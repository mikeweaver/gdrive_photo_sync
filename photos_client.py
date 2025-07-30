"""
Google Photos client for uploading and managing media items and albums.
"""

import logging
import time
from typing import Generator, List, Optional

import requests
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from google.oauth2.credentials import Credentials


logger = logging.getLogger(__name__)


class PhotosClient:
    """Client for interacting with Google Photos API."""
    
    def __init__(self, credentials: Credentials):
        """
        Initialize Photos client.
        
        Args:
            credentials: Google API credentials
        """
        self.credentials = credentials
        self.service = build('photoslibrary', 'v1', credentials=credentials, static_discovery=False)
        self.upload_url = 'https://photoslibrary.googleapis.com/v1/uploads'
        
    def find_album_by_name(self, album_name: str) -> Optional[str]:
        """
        Find album ID by name.
        
        Args:
            album_name: Name of the album to find
            
        Returns:
            Album ID if found, None otherwise
        """
        try:
            page_token = None
            
            while True:
                request_params = {}
                if page_token:
                    request_params['pageToken'] = page_token
                    
                results = self.service.albums().list(**request_params).execute()
                albums = results.get('albums', [])
                
                for album in albums:
                    if album.get('title') == album_name:
                        return album['id']
                        
                page_token = results.get('nextPageToken')
                if not page_token:
                    break
                    
            return None
            
        except HttpError as e:
            logger.error(f"Error searching for album '{album_name}': {e}")
            raise
            
    def create_album(self, album_name: str) -> str:
        """
        Create a new album.
        
        Args:
            album_name: Name of the album to create
            
        Returns:
            Album ID of the created album
            
        Raises:
            Exception: If album creation fails
        """
        try:
            album_body = {
                'album': {
                    'title': album_name
                }
            }
            
            result = self.service.albums().create(body=album_body).execute()
            album_id = result['id']
            
            logger.info(f"Created album '{album_name}' with ID: {album_id}")
            return album_id
            
        except HttpError as e:
            logger.error(f"Error creating album '{album_name}': {e}")
            raise
            
    def get_or_create_album(self, album_name: str) -> str:
        """
        Get existing album ID or create new album.
        
        Args:
            album_name: Name of the album
            
        Returns:
            Album ID
        """
        album_id = self.find_album_by_name(album_name)
        
        if album_id:
            logger.info(f"Found existing album '{album_name}': {album_id}")
            return album_id
        else:
            logger.info(f"Album '{album_name}' not found, creating new album")
            return self.create_album(album_name)
            
    def list_album_media_items(self, album_id: str) -> Generator[dict, None, None]:
        """
        List all media items in an album.
        
        Args:
            album_id: ID of the album
            
        Yields:
            Media item metadata dictionaries
        """
        try:
            page_token = None
            
            while True:
                search_body = {
                    'albumId': album_id
                }
                if page_token:
                    search_body['pageToken'] = page_token
                    
                results = self.service.mediaItems().search(body=search_body).execute()
                media_items = results.get('mediaItems', [])
                
                for item in media_items:
                    yield item
                    
                page_token = results.get('nextPageToken')
                if not page_token:
                    break
                    
        except HttpError as e:
            logger.error(f"Error listing media items in album {album_id}: {e}")
            raise
            
    def upload_media(self, file_content: bytes, filename: str, max_retries: int = 2) -> str:
        """
        Upload media file to Google Photos and return upload token.
        
        Args:
            file_content: File content as bytes
            filename: Original filename
            max_retries: Maximum number of retry attempts
            
        Returns:
            Upload token for use in batch operations
            
        Raises:
            Exception: If upload fails after retries
        """
        for attempt in range(max_retries + 1):
            try:
                headers = {
                    'Authorization': f'Bearer {self.credentials.token}',
                    'Content-type': 'application/octet-stream',
                    'X-Goog-Upload-File-Name': filename,
                    'X-Goog-Upload-Protocol': 'raw'
                }
                
                upload_response = requests.post(
                    self.upload_url,
                    data=file_content,
                    headers=headers
                )
                upload_response.raise_for_status()
                upload_token = upload_response.text
                
                logger.debug(f"Successfully uploaded {filename}, got token")
                return upload_token
                    
            except Exception as e:
                if attempt < max_retries:
                    wait_time = 2 ** attempt  # Exponential backoff
                    logger.warning(f"Upload attempt {attempt + 1} failed, retrying in {wait_time}s: {e}")
                    time.sleep(wait_time)
                else:
                    logger.error(f"Upload failed after {max_retries + 1} attempts: {e}")
                    raise
    def batch_create_media_items(self, upload_tokens_and_filenames: List[tuple], max_retries: int = 2) -> List[str]:
        """
        Create media items from upload tokens in batches (up to 50 at once).
        
        Args:
            upload_tokens_and_filenames: List of (upload_token, filename) tuples
            max_retries: Maximum number of retry attempts
            
        Returns:
            List of media item IDs
            
        Raises:
            Exception: If batch creation fails after retries
        """
        media_item_ids = []
        
        # Process in batches of 50
        for i in range(0, len(upload_tokens_and_filenames), 50):
            batch = upload_tokens_and_filenames[i:i+50]
            
            for attempt in range(max_retries + 1):
                try:
                    new_media_items = []
                    for upload_token, filename in batch:
                        new_media_items.append({
                            'description': f'Uploaded from Google Drive: {filename}',
                            'simpleMediaItem': {
                                'fileName': filename,
                                'uploadToken': upload_token
                            }
                        })
                    
                    create_body = {
                        'newMediaItems': new_media_items
                    }
                    
                    create_result = self.service.mediaItems().batchCreate(body=create_body).execute()
                    
                    # Process results
                    new_media_results = create_result.get('newMediaItemResults', [])
                    if not new_media_results:
                        raise Exception("No media item results returned")
                    
                    batch_ids = []
                    for j, result in enumerate(new_media_results):
                        if 'mediaItem' in result:
                            media_item_id = result['mediaItem']['id']
                            batch_ids.append(media_item_id)
                            logger.debug(f"Successfully created media item for {batch[j][1]}")
                        else:
                            error_msg = result.get('status', {}).get('message', 'Unknown error')
                            logger.error(f"Media item creation failed for {batch[j][1]}: {error_msg}")
                            raise Exception(f"Batch creation failed: {error_msg}")
                    
                    media_item_ids.extend(batch_ids)
                    logger.info(f"Successfully created batch of {len(batch_ids)} media items")
                    break
                    
                except Exception as e:
                    if attempt < max_retries:
                        wait_time = 2 ** attempt
                        logger.warning(f"Batch create attempt {attempt + 1} failed, retrying in {wait_time}s: {e}")
                        time.sleep(wait_time)
                    else:
                        logger.error(f"Batch create failed after {max_retries + 1} attempts: {e}")
                        raise
        
        return media_item_ids
                    
    def batch_add_media_to_album(self, album_id: str, media_item_ids: List[str], max_retries: int = 2) -> None:
        """
        Add media items to an album in batches (up to 50 at once).
        
        Args:
            album_id: ID of the album
            media_item_ids: List of media item IDs to add
            max_retries: Maximum number of retry attempts
            
        Raises:
            Exception: If adding to album fails after retries
        """
        # Process in batches of 50
        for i in range(0, len(media_item_ids), 50):
            batch = media_item_ids[i:i+50]
            
            for attempt in range(max_retries + 1):
                try:
                    add_body = {
                        'mediaItemIds': batch
                    }
                    
                    self.service.albums().batchAddMediaItems(
                        albumId=album_id,
                        body=add_body
                    ).execute()
                    
                    logger.info(f"Added batch of {len(batch)} items to album {album_id}")
                    break
                    
                except HttpError as e:
                    if attempt < max_retries:
                        wait_time = 2 ** attempt
                        logger.warning(f"Batch add attempt {attempt + 1} failed, retrying in {wait_time}s: {e}")
                        time.sleep(wait_time)
                    else:
                        logger.error(f"Batch add failed after {max_retries + 1} attempts: {e}")
                        raise
            
    def check_media_exists_in_album(self, album_id: str, media_item_id: str) -> bool:
        """
        Check if a media item already exists in an album.
        
        Args:
            album_id: ID of the album
            media_item_id: ID of the media item to check
            
        Returns:
            True if media item exists in album, False otherwise
        """
        try:
            for item in self.list_album_media_items(album_id):
                if item['id'] == media_item_id:
                    return True
            return False
            
        except Exception as e:
            logger.error(f"Error checking if media exists in album: {e}")
            return False
            
            
    def get_album_url(self, album_id: str) -> str:
        """
        Get the web URL for an album.
        
        Args:
            album_id: ID of the album
            
        Returns:
            Web URL for the album
        """
        return f'https://photos.google.com/lr/album/{album_id}'