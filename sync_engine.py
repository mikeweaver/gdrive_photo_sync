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
from utils import format_file_size


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
        
    def sync(self, drive_folder_id: str, album_name: Optional[str] = None, album_id: Optional[str] = None) -> None:
        """
        Perform the synchronization.
        
        Args:
            drive_folder_id: Google Drive folder ID
            album_name: Google Photos album name (if creating/finding by name)
            album_id: Google Photos album ID (if using existing album)
        """
        logger.info("Starting synchronization...")
        logger.info(f"Source: Google Drive folder {drive_folder_id}")
        
        if album_id:
            logger.info(f"Target: Google Photos album ID '{album_id}'")
        elif album_name:
            logger.info(f"Target: Google Photos album name '{album_name}'")
        else:
            raise ValueError("Either album_name or album_id must be provided")
        
        try:
            # Authenticate and initialize clients
            credentials = self.auth.authenticate()
            self.drive_client = DriveClient(credentials)
            self.photos_client = PhotosClient(credentials)
            
            # Determine target album ID
            if album_id:
                target_album_id = album_id
                logger.info(f"Using album ID: {target_album_id}")
            else:
                # Get or create album by name
                target_album_id = self.photos_client.get_or_create_album(album_name)
                
            # Get list of files from Drive
            logger.info("Scanning Google Drive folder...")
            all_files = list(self.drive_client.list_files_recursive(drive_folder_id))
            logger.info(f"Found {len(all_files)} total files")
            
            # Filter files
            media_files = self._filter_files(all_files)
            
            if not media_files:
                logger.info("No files to sync after applying filters")
                return
                
            # Sync files using batch operations
            success_count, skip_count, error_count = self._process_files_in_batches(media_files, target_album_id)
                    
            # Summary
            logger.info("Synchronization completed!")
            logger.info(f"Results: {success_count} uploaded, {skip_count} skipped, {error_count} errors")
            
            # Launch browser if requested
            if self.launch_browser and success_count > 0:
                album_url = self.photos_client.get_album_url(target_album_id)
                logger.info(f"Opening album in browser: {album_url}")
                webbrowser.open(album_url)
                
        except Exception as e:
            logger.error(f"Synchronization failed: {e}")
            raise
    
    def _filter_files(self, all_files: List[dict]) -> List[dict]:
        """
        Filter files based on configured criteria.
        
        Args:
            all_files: List of all file metadata from Drive API
            
        Returns:
            List of filtered media files
        """
        # Filter to media files only
        media_files = [f for f in all_files if self.drive_client.is_media_file(f)]
        logger.info(f"After media type filter: {len(media_files)} files")
        
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
            
        return media_files
    
    def _process_files_in_batches(self, media_files: List[dict], target_album_id: str, batch_size:int = 50) -> tuple:
        """
        Process all files in batches.
        
        Args:
            media_files: List of filtered media files
            target_album_id: Target album ID
            
        Returns:
            Tuple of (success_count, skip_count, error_count)
        """
        logger.info(f"Starting sync of {len(media_files)} files...")
        processed_hashes: Set[str] = set()
        
        success_count = 0
        skip_count = 0
        error_count = 0
        
        # Process files in batches for efficiency
        for batch_start in range(0, len(media_files), batch_size):
            batch_end = min(batch_start + batch_size, len(media_files))
            batch_files = media_files[batch_start:batch_end]
            
            logger.info(f"Processing batch {batch_start//batch_size + 1}/{(len(media_files) + batch_size - 1)//batch_size} ({len(batch_files)} files)")
            
            results = self._process_files(batch_files, target_album_id, processed_hashes)
            
            for result in results:
                print(f"{result}")
                
                if result.status == 'success':
                    success_count += 1
                elif result.status == 'skipped':
                    skip_count += 1
                else:  # error
                    error_count += 1
        
        return success_count, skip_count, error_count
            
    def _process_files(self, batch_files: List[dict], album_id: str, processed_hashes: Set[str]) -> List[SyncResult]:
        """
        Completely process a batch of files: upload, create media items, add to album.
        
        Args:
            batch_files: List of file metadata from Drive API
            album_id: Target album ID
            processed_hashes: Set of already processed file hashes
            
        Returns:
            List of SyncResult indicating the outcome for each file
        """
        results = []
        upload_tokens_and_filenames = []
        file_mapping = []
        
        # Phase 1: Upload files individually and collect tokens
        upload_tokens_and_filenames, file_mapping, upload_results = self._upload_files(
            batch_files, processed_hashes
        )
        results.extend(upload_results)
        
        # Phase 2: Batch create media items and add to album (complete processing)
        if upload_tokens_and_filenames:
            batch_results = self._create_and_add_media_items(
                upload_tokens_and_filenames, file_mapping, album_id, processed_hashes
            )
            results.extend(batch_results)
        
        return results
    
    def _upload_files(self, files: List[dict], processed_hashes: Set[str]) -> tuple:
        """
        Upload files in a batch and collect upload tokens.
        
        Args:
            files: List of file metadata from Drive API
            processed_hashes: Set of already processed file hashes
            
        Returns:
            Tuple of (upload_tokens_and_filenames, file_mapping, results)
        """
        upload_tokens_and_filenames = []
        file_mapping = []
        results = []
        
        for file_info in files:
            filename = file_info['name']
            file_id = file_info['id']
            file_hash = file_info.get('md5Checksum')
            
            try:
                # Check for duplicate content by hash
                if file_hash and file_hash in processed_hashes:
                    results.append(SyncResult(
                        filename, 'skipped',
                        message='duplicate content (same hash already processed)'
                    ))
                    continue
                
                # Download file from Drive
                logger.debug(f"Downloading {filename} from Google Drive...")
                file_content = self.drive_client.download_file(file_id)
                
                # Upload to Google Photos to get token
                logger.debug(f"Uploading {filename} to Google Photos...")
                upload_token = self.photos_client.upload_media(file_content, filename)
                
                upload_tokens_and_filenames.append((upload_token, filename))
                file_mapping.append(file_info)
                
            except Exception as e:
                error_msg = str(e)
                logger.error(f"Error uploading {filename}: {error_msg}")
                
                if self.skip_errors:
                    results.append(SyncResult(filename, 'error', error=error_msg))
                else:
                    # Re-raise to halt sync
                    raise
        
        return upload_tokens_and_filenames, file_mapping, results
    
    def _create_and_add_media_items(self, upload_tokens_and_filenames: List[tuple], 
                                   file_mapping: List[dict], album_id: str, 
                                   processed_hashes: Set[str]) -> List[SyncResult]:
        """
        Create media items and add them to album.
        
        Args:
            upload_tokens_and_filenames: List of (upload_token, filename) tuples
            file_mapping: List of file metadata
            album_id: Target album ID
            processed_hashes: Set of already processed file hashes
            
        Returns:
            List of SyncResult indicating the outcome for each file
        """
        results = []
        
        try:
            # Create media items in batch
            logger.debug(f"Creating {len(upload_tokens_and_filenames)} media items...")
            media_item_ids = self.photos_client.batch_create_media_items(upload_tokens_and_filenames)
            
            # Add media items to album in batch
            logger.debug(f"Adding {len(media_item_ids)} items to album...")
            self.photos_client.batch_add_media_to_album(album_id, media_item_ids)
            
            # Create success results and mark hashes as processed
            for file_info in file_mapping:
                filename = file_info['name']
                file_hash = file_info.get('md5Checksum')
                
                # Add hash to processed set
                if file_hash:
                    processed_hashes.add(file_hash)
                
                # Format success message
                size_str = format_file_size(int(file_info.get('size', 0)))
                message = f"uploaded successfully ({size_str})"
                
                results.append(SyncResult(filename, 'success', message=message))
                
        except Exception as e:
            error_msg = str(e)
            logger.error(f"Error in batch operations: {error_msg}")
            
            # Mark all files in batch as failed
            for file_info in file_mapping:
                filename = file_info['name']
                if self.skip_errors:
                    results.append(SyncResult(filename, 'error', error=error_msg))
                else:
                    raise
        
        return results