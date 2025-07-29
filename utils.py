"""
Utility functions for the Google Drive to Google Photos sync tool.
"""

import logging
import re
import hashlib
from typing import Optional

def extract_folder_id_from_url(url: str) -> Optional[str]:
    """
    Extract folder ID from Google Drive folder URL.
    
    Args:
        url: Google Drive folder URL or ID
        
    Returns:
        Folder ID if valid, None otherwise
    """
    # If it's already just an ID (no URL components)
    if '/' not in url and len(url) > 10:
        return url
    
    # Extract from various URL formats
    patterns = [
        r'/folders/([a-zA-Z0-9-_]+)',
        r'id=([a-zA-Z0-9-_]+)',
    ]
    
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    
    return None


def extract_album_id_from_url(url: str) -> Optional[str]:
    """
    Extract album ID from Google Photos album URL.
    
    Args:
        url: Google Photos album URL or name
        
    Returns:
        Album ID if URL, otherwise None (indicating it's a name)
    """
    # If it contains album URL pattern
    match = re.search(r'/album/([a-zA-Z0-9-_]+)', url)
    if match:
        return match.group(1)
    
    return None


def generate_unique_filename(original_name: str, existing_names: set) -> str:
    """
    Generate unique filename if name collision exists.
    
    Args:
        original_name: Original filename
        existing_names: Set of existing filenames
        
    Returns:
        Unique filename
    """
    if original_name not in existing_names:
        return original_name
    
    name_parts = original_name.rsplit('.', 1)
    base_name = name_parts[0]
    extension = f".{name_parts[1]}" if len(name_parts) > 1 else ""
    
    counter = 1
    while True:
        new_name = f"{base_name}_{counter}{extension}"
        if new_name not in existing_names:
            return new_name
        counter += 1


def calculate_file_hash(file_content: bytes) -> str:
    """
    Calculate MD5 hash of file content.
    
    Args:
        file_content: File content as bytes
        
    Returns:
        MD5 hash as hex string
    """
    return hashlib.md5(file_content).hexdigest()


def format_file_size(size_bytes: int) -> str:
    """
    Format file size in human readable format.
    
    Args:
        size_bytes: File size in bytes
        
    Returns:
        Formatted size string
    """
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size_bytes < 1024.0:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.1f} TB"