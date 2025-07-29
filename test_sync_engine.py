"""
Tests for the sync engine module.
"""

import unittest
from unittest.mock import Mock, patch, MagicMock
from sync_engine import SyncEngine, SyncResult


class TestSyncEngine(unittest.TestCase):
    
    def setUp(self):
        self.engine = SyncEngine()
        
    @patch('sync_engine.GoogleAuth')
    def test_init_default_parameters(self, mock_auth_class):
        """Test SyncEngine initialization with default parameters."""
        engine = SyncEngine()
        
        self.assertFalse(engine.skip_errors)
        self.assertIsNone(engine.file_types)
        self.assertIsNone(engine.regex_filter)
        self.assertIsNone(engine.min_size_kb)
        self.assertIsNone(engine.max_size_mb)
        self.assertTrue(engine.launch_browser)
        self.assertFalse(engine.reset_auth)
        
    @patch('sync_engine.GoogleAuth')
    def test_init_custom_parameters(self, mock_auth_class):
        """Test SyncEngine initialization with custom parameters."""
        engine = SyncEngine(
            skip_errors=True,
            file_types=['jpg', 'mp4'],
            regex_filter=r'.*vacation.*',
            min_size_kb=100,
            max_size_mb=50,
            launch_browser=False,
            reset_auth=True
        )
        
        self.assertTrue(engine.skip_errors)
        self.assertEqual(engine.file_types, ['jpg', 'mp4'])
        self.assertEqual(engine.regex_filter, r'.*vacation.*')
        self.assertEqual(engine.min_size_kb, 100)
        self.assertEqual(engine.max_size_mb, 50)
        self.assertFalse(engine.launch_browser)
        self.assertTrue(engine.reset_auth)
        
    @patch('sync_engine.GoogleAuth')
    @patch('sync_engine.DriveClient')
    @patch('sync_engine.PhotosClient')
    def test_sync_with_album_name(self, mock_photos_client, mock_drive_client, mock_auth):
        """Test sync with album name (not URL)."""
        # Setup mocks
        mock_auth_instance = Mock()
        mock_auth.return_value = mock_auth_instance
        mock_creds = Mock()
        mock_auth_instance.authenticate.return_value = mock_creds
        
        mock_drive = Mock()
        mock_drive_client.return_value = mock_drive
        
        mock_photos = Mock()
        mock_photos_client.return_value = mock_photos
        mock_photos.get_or_create_album.return_value = 'album123'
        mock_photos.get_album_url.return_value = 'https://photos.google.com/lr/album/album123'
        
        # Mock file listing
        mock_files = [
            {
                'id': 'file1',
                'name': 'photo1.jpg',
                'mimeType': 'image/jpeg',
                'size': '1024000',
                'md5Checksum': 'abc123'
            }
        ]
        mock_drive.list_files_recursive.return_value = iter(mock_files)
        mock_drive.is_media_file.return_value = True
        mock_drive.filter_files_by_type.return_value = mock_files
        mock_drive.filter_files_by_regex.return_value = mock_files
        mock_drive.filter_files_by_size.return_value = mock_files
        
        # Mock download and upload
        mock_drive.download_file.return_value = b'file_content'
        mock_photos.upload_media.return_value = 'media123'
        mock_photos.check_media_exists_in_album.return_value = False
        mock_photos.check_filename_exists_in_album.return_value = False
        
        with patch('webbrowser.open'):
            engine = SyncEngine()
            engine.sync('folder123', 'My Album', is_album_id=False)
            
        # Verify album creation with name
        mock_photos.get_or_create_album.assert_called_once_with('My Album')
        
    @patch('sync_engine.GoogleAuth')
    @patch('sync_engine.DriveClient')
    @patch('sync_engine.PhotosClient')
    def test_sync_with_album_id(self, mock_photos_client, mock_drive_client, mock_auth):
        """Test sync with album ID (not name)."""
        # Setup mocks
        mock_auth_instance = Mock()
        mock_auth.return_value = mock_auth_instance
        mock_creds = Mock()
        mock_auth_instance.authenticate.return_value = mock_creds
        
        mock_drive = Mock()
        mock_drive_client.return_value = mock_drive
        
        mock_photos = Mock()
        mock_photos_client.return_value = mock_photos
        mock_photos.get_album_url.return_value = 'https://photos.google.com/lr/album/album123'
        
        # Mock file listing
        mock_files = [
            {
                'id': 'file1',
                'name': 'photo1.jpg',
                'mimeType': 'image/jpeg',
                'size': '1024000',
                'md5Checksum': 'abc123'
            }
        ]
        mock_drive.list_files_recursive.return_value = iter(mock_files)
        mock_drive.is_media_file.return_value = True
        mock_drive.filter_files_by_type.return_value = mock_files
        mock_drive.filter_files_by_regex.return_value = mock_files
        mock_drive.filter_files_by_size.return_value = mock_files
        
        # Mock download and upload
        mock_drive.download_file.return_value = b'file_content'
        mock_photos.upload_media.return_value = 'media123'
        mock_photos.check_media_exists_in_album.return_value = False
        mock_photos.check_filename_exists_in_album.return_value = False
        
        with patch('webbrowser.open'):
            engine = SyncEngine()
            engine.sync('folder123', 'album123', is_album_id=True)
            
        # Verify album ID is used directly (no get_or_create_album call)
        mock_photos.get_or_create_album.assert_not_called()
        
        
    @patch('sync_engine.GoogleAuth')
    @patch('sync_engine.DriveClient')
    @patch('sync_engine.PhotosClient')
    def test_sync_file_success(self, mock_photos_client, mock_drive_client, mock_auth):
        """Test successful sync of a single file."""
        engine = SyncEngine()
        
        # Setup clients
        mock_drive = Mock()
        mock_photos = Mock()
        engine.drive_client = mock_drive
        engine.photos_client = mock_photos
        
        file_info = {
            'id': 'file123',
            'name': 'photo.jpg',
            'mimeType': 'image/jpeg',
            'size': '1024000',
            'md5Checksum': 'abc123'
        }
        
        # Mock successful operations
        mock_photos.check_filename_exists_in_album.return_value = False
        mock_drive.download_file.return_value = b'file_content'
        mock_photos.upload_media.return_value = 'media123'
        mock_photos.check_media_exists_in_album.return_value = False
        
        result = engine._sync_file(file_info, 'album123', set())
        
        self.assertEqual(result.status, 'success')
        self.assertEqual(result.filename, 'photo.jpg')
        self.assertIsNone(result.error)
        
    @patch('sync_engine.GoogleAuth')
    @patch('sync_engine.DriveClient')
    @patch('sync_engine.PhotosClient')
    def test_sync_file_duplicate_filename(self, mock_photos_client, mock_drive_client, mock_auth):
        """Test sync with duplicate filename handling."""
        engine = SyncEngine()
        
        # Setup clients
        mock_drive = Mock()
        mock_photos = Mock()
        engine.drive_client = mock_drive
        engine.photos_client = mock_photos
        
        file_info = {
            'id': 'file123',
            'name': 'photo.jpg',
            'mimeType': 'image/jpeg',
            'size': '1024000',
            'md5Checksum': 'abc123'
        }
        
        # Mock duplicate filename
        mock_photos.check_filename_exists_in_album.return_value = True
        mock_photos.list_album_media_items.return_value = [
            {'filename': 'photo.jpg'},
            {'filename': 'other.jpg'}
        ]
        mock_drive.download_file.return_value = b'file_content'
        mock_photos.upload_media.return_value = 'media123'
        mock_photos.check_media_exists_in_album.return_value = False
        
        with patch('sync_engine.generate_unique_filename', return_value='photo_1.jpg'):
            result = engine._sync_file(file_info, 'album123', set())
            
        self.assertEqual(result.status, 'success')
        self.assertEqual(result.filename, 'photo.jpg')
        self.assertIn('renamed to photo_1.jpg', result.message)
        
    @patch('sync_engine.GoogleAuth')
    @patch('sync_engine.DriveClient')
    @patch('sync_engine.PhotosClient')  
    def test_sync_file_duplicate_content(self, mock_photos_client, mock_drive_client, mock_auth):
        """Test sync with duplicate content detection."""
        engine = SyncEngine()
        
        # Setup clients
        mock_drive = Mock()
        mock_photos = Mock()
        engine.drive_client = mock_drive
        engine.photos_client = mock_photos
        
        file_info = {
            'id': 'file123',
            'name': 'photo.jpg',
            'mimeType': 'image/jpeg',
            'size': '1024000',
            'md5Checksum': 'abc123'
        }
        
        # Mock duplicate content (same media item returned)
        mock_photos.check_filename_exists_in_album.return_value = False
        mock_drive.download_file.return_value = b'file_content'
        mock_photos.upload_media.return_value = 'existing_media123'
        mock_photos.check_media_exists_in_album.return_value = True  # Already in album
        
        result = engine._sync_file(file_info, 'album123', {'abc123'})
        
        self.assertEqual(result.status, 'skipped')
        self.assertEqual(result.filename, 'photo.jpg')
        self.assertIn('duplicate content', result.message)
        
    @patch('sync_engine.GoogleAuth')
    @patch('sync_engine.DriveClient')
    @patch('sync_engine.PhotosClient')
    def test_sync_file_error_skip_mode(self, mock_photos_client, mock_drive_client, mock_auth):
        """Test sync file error handling in skip mode."""
        engine = SyncEngine(skip_errors=True)
        
        # Setup clients
        mock_drive = Mock()
        mock_photos = Mock()
        engine.drive_client = mock_drive
        engine.photos_client = mock_photos
        
        file_info = {
            'id': 'file123',
            'name': 'photo.jpg',
            'mimeType': 'image/jpeg',
            'size': '1024000',
            'md5Checksum': 'abc123'
        }
        
        # Mock error during download
        mock_photos.check_filename_exists_in_album.return_value = False
        mock_drive.download_file.side_effect = Exception("Download failed")
        
        result = engine._sync_file(file_info, 'album123', set())
        
        self.assertEqual(result.status, 'error')
        self.assertEqual(result.filename, 'photo.jpg')
        self.assertIn('Download failed', result.error)
        
    def test_sync_result_str(self):
        """Test SyncResult string representation."""
        result = SyncResult('photo.jpg', 'success', 'Uploaded successfully')
        expected = "photo.jpg: success - Uploaded successfully"
        self.assertEqual(str(result), expected)
        
        result_with_error = SyncResult('photo.jpg', 'error', error='Upload failed')
        expected_error = "photo.jpg: error - Upload failed"
        self.assertEqual(str(result_with_error), expected_error)


if __name__ == '__main__':
    unittest.main()