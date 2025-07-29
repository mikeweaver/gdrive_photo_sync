"""
Main sync engine that orchestrates the synchronization between Google Drive and Google Photos.
"""

import logging
import re
import webbrowser
from dataclasses import dataclass
from typing import Optional, List, Set

from auth import GoogleAuth
from drive_client import DriveClient
from photos_client import PhotosClient
from utils import extract_album_id_from_url, generate_unique_filename, format_file_size


logger = logging.getLogger(__name__)


@dataclass
class SyncResult:
    """Result of syncing a single file."""
    filename: str
    status: str  # 'success', 'skipped', 'error'
    message: Optional[str] = None
    error: Optional[str] = None
    
    def __str__(self) -> str:
        if self.error:
            return f"{self.filename}: {self.status} - {self.error}"
        elif self.message:
            return f"{self.filename}: {self.status} - {self.message}"
        else:
            return f"{self.filename}: {self.status}"


class SyncEngine:
    """Main engine for synchronizing Google Drive folders to Google Photos albums."""
    
    def __init__(self, skip_errors: bool = False, file_types: Optional[List[str]] = None,
                 regex_filter: Optional[str] = None, min_size_kb: Optional[int] = None,
                 max_size_mb: Optional[int] = None, launch_browser: bool = True,
                 reset_auth: bool = False):
        """
        Initialize sync engine.
        
        Args:
            skip_errors: Skip errors rather than retry
            file_types: List of allowed file extensions
            regex_filter: Regex pattern to match filenames
            min_size_kb: Minimum file size in KB
            max_size_mb: Maximum file size in MB
            launch_browser: Launch browser to album after sync
            reset_auth: Reset authentication tokens
        """
        self.skip_errors = skip_errors
        self.file_types = file_types
        self.regex_filter = regex_filter
        self.min_size_kb = min_size_kb
        self.max_size_mb = max_size_mb
        self.launch_browser = launch_browser
        self.reset_auth = reset_auth
        
        # Initialize authentication
        self.auth = GoogleAuth()
        if reset_auth:
            self.auth.clear_tokens()
            
        # Clients will be initialized during sync
        self.drive_client: Optional[DriveClient] = None
        self.photos_client: Optional[PhotosClient] = None
        
    def sync(self, drive_folder_id: str, photos_album: str, is_album_id: bool = False) -> None:
        """
        Perform the synchronization.
        
        Args:
            drive_folder_id: Google Drive folder ID
            photos_album: Google Photos album name or ID
            is_album_id: True if photos_album is an ID, False if it's a name
        """
        logger.info("Starting synchronization...")
        logger.info(f"Source: Google Drive folder {drive_folder_id}")
        
        if is_album_id:
            logger.info(f"Target: Google Photos album ID '{photos_album}'")
        else:
            logger.info(f"Target: Google Photos album name '{photos_album}'")
        
        try:
            # Authenticate and initialize clients
            credentials = self.auth.authenticate()
            self.drive_client = DriveClient(credentials)
            self.photos_client = PhotosClient(credentials)
            
            # Determine target album ID
            if is_album_id:
                album_id = photos_album
                logger.info(f"Using provided album ID: {album_id}")
            else:
                # Extract ID from URL if it's a URL, otherwise treat as name
                album_id = extract_album_id_from_url(photos_album)
                if album_id:
                    logger.info(f"Extracted album ID from URL: {album_id}")
                else:
                    # Treat as album name, get or create
                    album_id = self.photos_client.get_or_create_album(photos_album)
                
            # Get list of files from Drive
            logger.info("Scanning Google Drive folder...")
            all_files = list(self.drive_client.list_files_recursive(drive_folder_id))
            logger.info(f"Found {len(all_files)} total files")
            
            # Filter files
            media_files = [f for f in all_files if self.drive_client.is_media_file(f)]
            logger.info(f"Found {len(media_files)} media files")
            
            # Apply filters
            if self.file_types:
                media_files = self.drive_client.filter_files_by_type(media_files, self.file_types)
                logger.info(f"After file type filter: {len(media_files)} files")
                
            if self.regex_filter:
                media_files = self.drive_client.filter_files_by_regex(media_files, self.regex_filter)
                logger.info(f"After regex filter: {len(media_files)} files")
                
            if self.min_size_kb or self.max_size_mb:
                media_files = self.drive_client.filter_files_by_size(
                    media_files, self.min_size_kb, self.max_size_mb
                )
                logger.info(f"After size filter: {len(media_files)} files")
                
            if not media_files:
                logger.info("No files to sync after applying filters")
                return
                
            # Sync files
            logger.info(f"Starting sync of {len(media_files)} files...")
            processed_hashes: Set[str] = set()
            
            success_count = 0
            skip_count = 0
            error_count = 0
            
            for i, file_info in enumerate(media_files, 1):
                logger.info(f"Processing file {i}/{len(media_files)}: {file_info['name']}")
                
                result = self._sync_file(file_info, album_id, processed_hashes)
                print(f"{result}")
                
                if result.status == 'success':
                    success_count += 1
                    # Add hash to processed set
                    if 'md5Checksum' in file_info:
                        processed_hashes.add(file_info['md5Checksum'])
                elif result.status == 'skipped':
                    skip_count += 1
                else:  # error
                    error_count += 1
                    
            # Summary
            logger.info("Synchronization completed!")
            logger.info(f"Results: {success_count} uploaded, {skip_count} skipped, {error_count} errors")
            
            # Launch browser if requested
            if self.launch_browser and success_count > 0:
                album_url = self.photos_client.get_album_url(album_id)
                logger.info(f"Opening album in browser: {album_url}")
                webbrowser.open(album_url)
                
        except Exception as e:
            logger.error(f"Synchronization failed: {e}")
            raise
            
        
    def _sync_file(self, file_info: dict, album_id: str, processed_hashes: Set[str]) -> SyncResult:
        """
        Sync a single file from Drive to Photos.
        
        Args:
            file_info: File metadata from Drive API
            album_id: Target album ID
            processed_hashes: Set of already processed file hashes
            
        Returns:
            SyncResult indicating the outcome
        """
        filename = file_info['name']
        file_id = file_info['id']
        file_hash = file_info.get('md5Checksum')
        
        try:
            # Check for duplicate content by hash
            if file_hash and file_hash in processed_hashes:
                return SyncResult(
                    filename, 'skipped',
                    message='duplicate content (same hash already processed)'
                )
                
            # Check for filename collision and generate unique name if needed
            upload_filename = filename
            if self.photos_client.check_filename_exists_in_album(album_id, filename):
                # Get existing filenames to avoid collisions
                existing_names = set()
                for item in self.photos_client.list_album_media_items(album_id):
                    if 'filename' in item:
                        existing_names.add(item['filename'])
                        
                upload_filename = generate_unique_filename(filename, existing_names)
                logger.info(f"Filename collision detected, renamed {filename} -> {upload_filename}")
                
            # Download file from Drive
            logger.debug(f"Downloading {filename} from Google Drive...")
            file_content = self.drive_client.download_file(file_id)
            
            # Upload to Google Photos
            logger.debug(f"Uploading {upload_filename} to Google Photos...")
            media_item_id = self.photos_client.upload_media(file_content, upload_filename)
            
            # Check if this is a duplicate (Google Photos returns same ID for duplicate content)
            if self.photos_client.check_media_exists_in_album(album_id, media_item_id):
                return SyncResult(
                    filename, 'skipped',
                    message='duplicate content (Google Photos detected duplicate)'
                )
                
            # Add to album
            self.photos_client.add_media_to_album(album_id, [media_item_id])
            
            # Format success message
            size_str = format_file_size(int(file_info.get('size', 0)))
            message = f"uploaded successfully ({size_str})"
            if upload_filename != filename:
                message += f", renamed to {upload_filename}"
                
            return SyncResult(filename, 'success', message=message)
            
        except Exception as e:
            error_msg = str(e)
            logger.error(f"Error syncing {filename}: {error_msg}")
            
            if self.skip_errors:
                return SyncResult(filename, 'error', error=error_msg)
            else:
                # Re-raise to halt sync
                raise