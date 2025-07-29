"""
Tests for the utility functions module.
"""

import unittest
import logging
from unittest.mock import patch
from utils import (
    extract_folder_id_from_url, 
    extract_album_id_from_url,
    generate_unique_filename,
    calculate_file_hash,
    format_file_size
)


class TestUtils(unittest.TestCase):
        
    def test_extract_folder_id_from_url_folder_pattern(self):
        """Test extracting folder ID from /folders/ URL pattern."""
        url = "https://drive.google.com/drive/folders/1BcDefGhIjKlMnOpQrStUvWxYz"
        result = extract_folder_id_from_url(url)
        self.assertEqual(result, "1BcDefGhIjKlMnOpQrStUvWxYz")
        
    def test_extract_folder_id_from_url_id_pattern(self):
        """Test extracting folder ID from id= URL pattern."""
        url = "https://drive.google.com/open?id=1BcDefGhIjKlMnOpQrStUvWxYz"
        result = extract_folder_id_from_url(url)
        self.assertEqual(result, "1BcDefGhIjKlMnOpQrStUvWxYz")
        
    def test_extract_folder_id_from_url_plain_id(self):
        """Test handling plain folder ID (no URL)."""
        folder_id = "1BcDefGhIjKlMnOpQrStUvWxYz"
        result = extract_folder_id_from_url(folder_id)
        self.assertEqual(result, folder_id)
        
    def test_extract_folder_id_from_url_invalid(self):
        """Test handling invalid URL/ID."""
        invalid_url = "https://example.com/invalid"
        result = extract_folder_id_from_url(invalid_url)
        self.assertIsNone(result)
        
        short_string = "abc"
        result = extract_folder_id_from_url(short_string)
        self.assertIsNone(result)
        
    def test_extract_album_id_from_url_valid(self):
        """Test extracting album ID from Google Photos URL."""
        url = "https://photos.google.com/lr/album/ABcdEFghIJklMNop"
        result = extract_album_id_from_url(url)
        self.assertEqual(result, "ABcdEFghIJklMNop")
        
    def test_extract_album_id_from_url_invalid(self):
        """Test handling invalid album URL (returns None for names)."""
        album_name = "My Vacation Photos"
        result = extract_album_id_from_url(album_name)
        self.assertIsNone(result)
        
        invalid_url = "https://example.com/invalid"
        result = extract_album_id_from_url(invalid_url)
        self.assertIsNone(result)
        
    def test_generate_unique_filename_no_collision(self):
        """Test generate_unique_filename when no collision exists."""
        existing_names = {"other.jpg", "another.png"}
        result = generate_unique_filename("photo.jpg", existing_names)
        self.assertEqual(result, "photo.jpg")
        
    def test_generate_unique_filename_with_collision(self):
        """Test generate_unique_filename when collision exists."""
        existing_names = {"photo.jpg", "photo_1.jpg", "other.png"}
        result = generate_unique_filename("photo.jpg", existing_names)
        self.assertEqual(result, "photo_2.jpg")
        
    def test_generate_unique_filename_no_extension(self):
        """Test generate_unique_filename with file that has no extension."""
        existing_names = {"document", "document_1"}
        result = generate_unique_filename("document", existing_names)
        self.assertEqual(result, "document_2")
        
    def test_generate_unique_filename_multiple_collisions(self):
        """Test generate_unique_filename with multiple existing collisions."""
        existing_names = {
            "photo.jpg", 
            "photo_1.jpg", 
            "photo_2.jpg", 
            "photo_3.jpg"
        }
        result = generate_unique_filename("photo.jpg", existing_names)
        self.assertEqual(result, "photo_4.jpg")
        
    def test_calculate_file_hash(self):
        """Test MD5 hash calculation."""
        test_content = b"Hello, World!"
        result = calculate_file_hash(test_content)
        # MD5 of "Hello, World!" is known
        expected_hash = "65a8e27d8879283831b664bd8b7f0ad4"
        self.assertEqual(result, expected_hash)
        
    def test_calculate_file_hash_empty(self):
        """Test MD5 hash calculation for empty content."""
        test_content = b""
        result = calculate_file_hash(test_content)
        # MD5 of empty string is known
        expected_hash = "d41d8cd98f00b204e9800998ecf8427e"
        self.assertEqual(result, expected_hash)
        
    def test_format_file_size_bytes(self):
        """Test file size formatting for bytes."""
        self.assertEqual(format_file_size(512), "512.0 B")
        self.assertEqual(format_file_size(1023), "1023.0 B")
        
    def test_format_file_size_kilobytes(self):
        """Test file size formatting for kilobytes."""
        self.assertEqual(format_file_size(1024), "1.0 KB")
        self.assertEqual(format_file_size(1536), "1.5 KB")
        self.assertEqual(format_file_size(1024 * 1023), "1023.0 KB")
        
    def test_format_file_size_megabytes(self):
        """Test file size formatting for megabytes."""
        self.assertEqual(format_file_size(1024 * 1024), "1.0 MB")
        self.assertEqual(format_file_size(1024 * 1024 * 2.5), "2.5 MB")
        self.assertEqual(format_file_size(1024 * 1024 * 1023), "1023.0 MB")
        
    def test_format_file_size_gigabytes(self):
        """Test file size formatting for gigabytes."""
        self.assertEqual(format_file_size(1024 * 1024 * 1024), "1.0 GB")
        self.assertEqual(format_file_size(1024 * 1024 * 1024 * 3.2), "3.2 GB")
        
    def test_format_file_size_terabytes(self):
        """Test file size formatting for terabytes."""
        size_tb = 1024 * 1024 * 1024 * 1024 * 1.5
        result = format_file_size(size_tb)
        self.assertEqual(result, "1.5 TB")
        
    def test_format_file_size_zero(self):
        """Test file size formatting for zero size."""
        self.assertEqual(format_file_size(0), "0.0 B")


if __name__ == '__main__':
    unittest.main()