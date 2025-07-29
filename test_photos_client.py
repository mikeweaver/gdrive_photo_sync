"""
Tests for the Google Photos client module.
"""

import unittest
from unittest.mock import Mock, patch, MagicMock
from photos_client import PhotosClient


class TestPhotosClient(unittest.TestCase):
    
    def setUp(self):
        self.mock_credentials = Mock()
        with patch('photos_client.build') as mock_build:
            self.mock_service = Mock()
            mock_build.return_value = self.mock_service
            self.client = PhotosClient(self.mock_credentials)
        
    @patch('photos_client.build')
    def test_init_creates_photos_service(self, mock_build):
        """Test that PhotosClient initializes the Photos service."""
        mock_service = Mock()
        mock_build.return_value = mock_service
        
        client = PhotosClient(self.mock_credentials)
        
        mock_build.assert_called_once_with('photoslibrary', 'v1', credentials=self.mock_credentials)
        self.assertEqual(client.service, mock_service)
        
    def test_find_album_by_name_found(self):
        """Test finding an album by name when it exists."""
        mock_response = {
            'albums': [
                {'id': 'album1', 'title': 'Other Album'},
                {'id': 'album2', 'title': 'My Vacation'},
                {'id': 'album3', 'title': 'Another Album'}
            ]
        }
        
        self.mock_service.albums.return_value.list.return_value.execute.return_value = mock_response
        
        result = self.client.find_album_by_name('My Vacation')
        
        self.assertEqual(result, 'album2')
        
    def test_find_album_by_name_not_found(self):
        """Test finding an album by name when it doesn't exist."""
        mock_response = {
            'albums': [
                {'id': 'album1', 'title': 'Other Album'},
                {'id': 'album3', 'title': 'Another Album'}
            ]
        }
        
        self.mock_service.albums.return_value.list.return_value.execute.return_value = mock_response
        
        result = self.client.find_album_by_name('Non-existent Album')
        
        self.assertIsNone(result)
        
    def test_create_album_success(self):
        """Test successful album creation."""
        mock_response = {
            'id': 'new_album_id',
            'title': 'New Album'
        }
        
        self.mock_service.albums.return_value.create.return_value.execute.return_value = mock_response
        
        result = self.client.create_album('New Album')
        
        self.assertEqual(result, 'new_album_id')
        self.mock_service.albums.return_value.create.assert_called_once_with(
            body={'album': {'title': 'New Album'}}
        )
        
    def test_get_or_create_album_existing(self):
        """Test getting existing album."""
        with patch.object(self.client, 'find_album_by_name', return_value='existing_id'):
            result = self.client.get_or_create_album('Existing Album')
            
        self.assertEqual(result, 'existing_id')
        
    def test_get_or_create_album_create_new(self):
        """Test creating new album when it doesn't exist."""
        with patch.object(self.client, 'find_album_by_name', return_value=None):
            with patch.object(self.client, 'create_album', return_value='new_id'):
                result = self.client.get_or_create_album('New Album')
                
        self.assertEqual(result, 'new_id')
        
    def test_list_album_media_items(self):
        """Test listing media items in an album."""
        mock_response = {
            'mediaItems': [
                {
                    'id': 'item1',
                    'filename': 'photo1.jpg',
                    'mimeType': 'image/jpeg'
                },
                {
                    'id': 'item2',
                    'filename': 'photo2.jpg',
                    'mimeType': 'image/jpeg'
                }
            ],
            'nextPageToken': None
        }
        
        self.mock_service.mediaItems.return_value.search.return_value.execute.return_value = mock_response
        
        result = list(self.client.list_album_media_items('album123'))
        
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0]['filename'], 'photo1.jpg')
        self.assertEqual(result[1]['filename'], 'photo2.jpg')
        
    def test_upload_media_success(self):
        """Test successful media upload."""
        # Mock the upload and media item creation
        with patch('requests.post') as mock_post:
            mock_post.return_value.text = 'upload_token_123'
            
            mock_create_response = {
                'newMediaItemResults': [
                    {
                        'mediaItem': {
                            'id': 'new_item_id',
                            'filename': 'test.jpg'
                        },
                        'status': {'message': 'Success'}
                    }
                ]
            }
            
            self.mock_service.mediaItems.return_value.batchCreate.return_value.execute.return_value = mock_create_response
            
            result = self.client.upload_media(b'image_content', 'test.jpg')
            
            self.assertEqual(result, 'new_item_id')
            
    def test_upload_media_failure(self):
        """Test media upload failure."""
        with patch('requests.post') as mock_post:
            mock_post.return_value.text = 'upload_token_123'
            
            mock_create_response = {
                'newMediaItemResults': [
                    {
                        'status': {
                            'message': 'Upload failed',
                            'code': 'FAILED_PRECONDITION'
                        }
                    }
                ]
            }
            
            self.mock_service.mediaItems.return_value.batchCreate.return_value.execute.return_value = mock_create_response
            
            with self.assertRaises(Exception):
                self.client.upload_media(b'image_content', 'test.jpg')
                
    def test_add_media_to_album_success(self):
        """Test successfully adding media items to album."""
        mock_response = {}  # Empty response indicates success
        
        self.mock_service.albums.return_value.batchAddMediaItems.return_value.execute.return_value = mock_response
        
        # Should not raise an exception
        self.client.add_media_to_album('album123', ['item1', 'item2'])
        
        self.mock_service.albums.return_value.batchAddMediaItems.assert_called_once_with(
            albumId='album123',
            body={'mediaItemIds': ['item1', 'item2']}
        )
        
    def test_check_media_exists_in_album_true(self):
        """Test checking if media exists in album - found."""
        mock_response = {
            'mediaItems': [
                {'id': 'item1', 'filename': 'photo1.jpg'},
                {'id': 'target_item', 'filename': 'target.jpg'},
                {'id': 'item3', 'filename': 'photo3.jpg'}
            ],
            'nextPageToken': None
        }
        
        self.mock_service.mediaItems.return_value.search.return_value.execute.return_value = mock_response
        
        result = self.client.check_media_exists_in_album('album123', 'target_item')
        
        self.assertTrue(result)
        
    def test_check_media_exists_in_album_false(self):
        """Test checking if media exists in album - not found."""
        mock_response = {
            'mediaItems': [
                {'id': 'item1', 'filename': 'photo1.jpg'},
                {'id': 'item2', 'filename': 'photo2.jpg'}
            ],
            'nextPageToken': None
        }
        
        self.mock_service.mediaItems.return_value.search.return_value.execute.return_value = mock_response
        
        result = self.client.check_media_exists_in_album('album123', 'missing_item')
        
        self.assertFalse(result)
        
    def test_get_album_url(self):
        """Test getting album URL from album ID."""
        expected_url = 'https://photos.google.com/lr/album/album123'
        
        result = self.client.get_album_url('album123')
        
        self.assertEqual(result, expected_url)
        
    def test_check_filename_exists_in_album_true(self):
        """Test checking if filename exists in album - found."""
        mock_response = {
            'mediaItems': [
                {'id': 'item1', 'filename': 'photo1.jpg'},
                {'id': 'item2', 'filename': 'target.jpg'},
                {'id': 'item3', 'filename': 'photo3.jpg'}
            ],
            'nextPageToken': None
        }
        
        self.mock_service.mediaItems.return_value.search.return_value.execute.return_value = mock_response
        
        result = self.client.check_filename_exists_in_album('album123', 'target.jpg')
        
        self.assertTrue(result)
        
    def test_check_filename_exists_in_album_false(self):
        """Test checking if filename exists in album - not found."""
        mock_response = {
            'mediaItems': [
                {'id': 'item1', 'filename': 'photo1.jpg'},
                {'id': 'item2', 'filename': 'photo2.jpg'}
            ],
            'nextPageToken': None
        }
        
        self.mock_service.mediaItems.return_value.search.return_value.execute.return_value = mock_response
        
        result = self.client.check_filename_exists_in_album('album123', 'missing.jpg')
        
        self.assertFalse(result)


if __name__ == '__main__':
    unittest.main()