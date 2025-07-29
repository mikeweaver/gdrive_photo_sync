"""
Google Drive client for accessing and downloading files.
"""

import logging
import re
import time
from typing import Generator, List, Optional

from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from google.oauth2.credentials import Credentials


logger = logging.getLogger(__name__)


class DriveClient:
    """Client for interacting with Google Drive API."""
    
    def __init__(self, credentials: Credentials):
        """
        Initialize Drive client.
        
        Args:
            credentials: Google API credentials
        """
        self.credentials = credentials
        self.service = build('drive', 'v3', credentials=credentials)
        
    def list_files_in_folder(self, folder_id: str, page_token: str = None) -> Generator[dict, None, None]:
        """
        List files in a specific Google Drive folder.
        
        Args:
            folder_id: Google Drive folder ID
            page_token: Token for pagination
            
        Yields:
            File metadata dictionaries
        """
        query = f"'{folder_id}' in parents and trashed=false"
        fields = "nextPageToken, files(id, name, mimeType, size, md5Checksum, createdTime, modifiedTime)"
        
        while True:
            try:
                results = self.service.files().list(
                    q=query,
                    fields=fields,
                    pageSize=100,
                    pageToken=page_token
                ).execute()
                
                files = results.get('files', [])
                for file_info in files:
                    yield file_info
                    
                page_token = results.get('nextPageToken')
                if not page_token:
                    break
                    
            except HttpError as e:
                logger.error(f"Error listing files in folder {folder_id}: {e}")
                raise
                
    def list_files_recursive(self, folder_id: str) -> Generator[dict, None, None]:
        """
        Recursively list all files in a folder and its subfolders.
        
        Args:
            folder_id: Google Drive folder ID
            
        Yields:
            File metadata dictionaries (excludes folders)
        """
        folders_to_process = [folder_id]
        
        while folders_to_process:
            current_folder = folders_to_process.pop(0)
            
            for file_info in self.list_files_in_folder(current_folder):
                if file_info['mimeType'] == 'application/vnd.google-apps.folder':
                    # Add subfolder to processing queue
                    folders_to_process.append(file_info['id'])
                    logger.debug(f"Found subfolder: {file_info['name']}")
                else:
                    # Yield regular files
                    yield file_info
                    
    def download_file(self, file_id: str, max_retries: int = 2) -> bytes:
        """
        Download file content from Google Drive.
        
        Args:
            file_id: Google Drive file ID
            max_retries: Maximum number of retry attempts
            
        Returns:
            File content as bytes
            
        Raises:
            Exception: If download fails after retries
        """
        for attempt in range(max_retries + 1):
            try:
                request = self.service.files().get_media(fileId=file_id)
                file_content = request.execute()
                return file_content
                
            except Exception as e:
                if attempt < max_retries:
                    wait_time = 2 ** attempt  # Exponential backoff
                    logger.warning(f"Download attempt {attempt + 1} failed, retrying in {wait_time}s: {e}")
                    time.sleep(wait_time)
                else:
                    logger.error(f"Download failed after {max_retries + 1} attempts: {e}")
                    raise
                    
    def is_media_file(self, file_info: dict) -> bool:
        """
        Check if a file is a media file (image or video).
        
        Args:
            file_info: File metadata dictionary
            
        Returns:
            True if file is image or video, False otherwise
        """
        mime_type = file_info.get('mimeType', '')
        return mime_type.startswith(('image/', 'video/'))
        
    def filter_files_by_type(self, files: List[dict], allowed_types: List[str]) -> List[dict]:
        """
        Filter files by allowed file extensions.
        
        Args:
            files: List of file metadata dictionaries
            allowed_types: List of allowed file extensions (without dots)
            
        Returns:
            Filtered list of files
        """
        if not allowed_types:
            return files
            
        allowed_extensions = [f".{ext.lower()}" for ext in allowed_types]
        filtered_files = []
        
        for file_info in files:
            filename = file_info.get('name', '').lower()
            if any(filename.endswith(ext) for ext in allowed_extensions):
                filtered_files.append(file_info)
                
        return filtered_files
        
    def filter_files_by_regex(self, files: List[dict], pattern: str) -> List[dict]:
        """
        Filter files by regex pattern matching filename.
        
        Args:
            files: List of file metadata dictionaries
            pattern: Regex pattern to match against filenames
            
        Returns:
            Filtered list of files
        """
        if not pattern:
            return files
            
        try:
            regex = re.compile(pattern)
            filtered_files = []
            
            for file_info in files:
                filename = file_info.get('name', '')
                if regex.search(filename):
                    filtered_files.append(file_info)
                    
            return filtered_files
            
        except re.error as e:
            logger.error(f"Invalid regex pattern '{pattern}': {e}")
            return files
            
    def filter_files_by_size(self, files: List[dict], min_size_kb: Optional[int] = None, 
                           max_size_mb: Optional[int] = None) -> List[dict]:
        """
        Filter files by size constraints.
        
        Args:
            files: List of file metadata dictionaries
            min_size_kb: Minimum file size in KB
            max_size_mb: Maximum file size in MB
            
        Returns:
            Filtered list of files
        """
        filtered_files = []
        
        for file_info in files:
            size_str = file_info.get('size')
            if not size_str:
                continue  # Skip files without size info
                
            try:
                size_bytes = int(size_str)
                
                # Check minimum size
                if min_size_kb and size_bytes < min_size_kb * 1024:
                    continue
                    
                # Check maximum size
                if max_size_mb and size_bytes > max_size_mb * 1024 * 1024:
                    continue
                    
                filtered_files.append(file_info)
                
            except ValueError:
                logger.warning(f"Invalid size value for file {file_info.get('name')}: {size_str}")
                continue
                
        return filtered_files