"""
Tests for the sync engine module.
"""

import unittest
from unittest.mock import Mock, patch
from sync_engine import SyncEngine, SyncResult


class TestSyncResult(unittest.TestCase):
    
    def test_sync_result_str_success(self):
        """Test SyncResult string representation for success."""
        result = SyncResult('photo.jpg', 'success', 'Uploaded successfully')
        expected = "photo.jpg: success - Uploaded successfully"
        self.assertEqual(str(result), expected)
        
    def test_sync_result_str_error(self):
        """Test SyncResult string representation for error."""
        result = SyncResult('photo.jpg', 'error', error='Upload failed')
        expected = "photo.jpg: error - Upload failed"
        self.assertEqual(str(result), expected)
        
    def test_sync_result_str_status_only(self):
        """Test SyncResult string representation with status only."""
        result = SyncResult('photo.jpg', 'skipped')
        expected = "photo.jpg: skipped"
        self.assertEqual(str(result), expected)


class TestSyncEngine(unittest.TestCase):
    
    def setUp(self):
        self.engine = SyncEngine()
        
    def test_init_default_parameters(self):
        """Test SyncEngine initialization with default parameters."""
        engine = SyncEngine()
        
        self.assertFalse(engine.skip_errors)
        self.assertIsNone(engine.file_types)
        self.assertIsNone(engine.regex_filter)
        self.assertIsNone(engine.min_size_kb)
        self.assertIsNone(engine.max_size_mb)
        self.assertTrue(engine.launch_browser)
        self.assertFalse(engine.reset_auth)
        
    def test_init_custom_parameters(self):
        """Test SyncEngine initialization with custom parameters."""
        engine = SyncEngine(
            skip_errors=True,
            file_types=['jpg', 'png'],
            regex_filter=r'.*\.jpg$',
            min_size_kb=100,
            max_size_mb=50,
            launch_browser=False,
            reset_auth=True
        )
        
        self.assertTrue(engine.skip_errors)
        self.assertEqual(engine.file_types, ['jpg', 'png'])
        self.assertEqual(engine.regex_filter, r'.*\.jpg$')
        self.assertEqual(engine.min_size_kb, 100)
        self.assertEqual(engine.max_size_mb, 50)
        self.assertFalse(engine.launch_browser)
        self.assertTrue(engine.reset_auth)

    @patch('sync_engine.GoogleAuth')
    @patch('sync_engine.DriveClient')
    @patch('sync_engine.PhotosClient')
    def test_sync_with_album_name(self, mock_photos_client, mock_drive_client, mock_auth):
        """Test sync with album name."""
        # Setup mocks
        mock_auth_instance = Mock()
        mock_auth.return_value = mock_auth_instance
        mock_auth_instance.authenticate.return_value = Mock()
        
        mock_drive = Mock()
        mock_drive_client.return_value = mock_drive
        mock_photos = Mock()
        mock_photos_client.return_value = mock_photos
        
        # Mock file operations
        mock_files = [
            {'id': 'file1', 'name': 'photo1.jpg', 'size': '1024000', 'md5Checksum': 'hash1'}
        ]
        mock_drive.list_files_recursive.return_value = mock_files
        mock_drive.is_media_file.return_value = True
        mock_photos.get_or_create_album.return_value = 'album123'
        
        # Mock download and upload
        mock_drive.download_file.return_value = b'file_content'
        mock_photos.upload_media.return_value = 'upload_token_123'
        mock_photos.batch_create_media_items.return_value = ['media_item_123']
        mock_photos.batch_add_media_to_album.return_value = None
        mock_photos.check_media_exists_in_album.return_value = False
        mock_photos.get_album_url.return_value = 'https://photos.google.com/album123'
        
        with patch('webbrowser.open'):
            engine = SyncEngine()
            engine.sync('folder123', album_name='My Album')
            
        # Verify album creation with name
        mock_photos.get_or_create_album.assert_called_once_with('My Album')
        
    @patch('sync_engine.GoogleAuth')
    @patch('sync_engine.DriveClient')
    @patch('sync_engine.PhotosClient')
    def test_sync_with_album_id(self, mock_photos_client, mock_drive_client, mock_auth):
        """Test sync with album ID."""
        # Setup mocks
        mock_auth_instance = Mock()
        mock_auth.return_value = mock_auth_instance
        mock_auth_instance.authenticate.return_value = Mock()
        
        mock_drive = Mock()
        mock_drive_client.return_value = mock_drive
        mock_photos = Mock()
        mock_photos_client.return_value = mock_photos
        
        # Mock file operations
        mock_files = [
            {'id': 'file1', 'name': 'photo1.jpg', 'size': '1024000', 'md5Checksum': 'hash1'}
        ]
        mock_drive.list_files_recursive.return_value = mock_files
        mock_drive.is_media_file.return_value = True
        
        # Mock download and upload
        mock_drive.download_file.return_value = b'file_content'
        mock_photos.upload_media.return_value = 'upload_token_123'
        mock_photos.batch_create_media_items.return_value = ['media_item_123']
        mock_photos.batch_add_media_to_album.return_value = None
        mock_photos.check_media_exists_in_album.return_value = False
        mock_photos.get_album_url.return_value = 'https://photos.google.com/album123'
        
        with patch('webbrowser.open'):
            engine = SyncEngine()
            engine.sync('folder123', album_id='album123')
            
        # Verify album ID is used directly (no get_or_create_album call)
        mock_photos.get_or_create_album.assert_not_called()

    @patch('sync_engine.GoogleAuth')
    @patch('sync_engine.DriveClient')
    @patch('sync_engine.PhotosClient')
    def test_filter_files(self, mock_photos_client, mock_drive_client, mock_auth):
        """Test file filtering functionality."""
        engine = SyncEngine(
            file_types=['jpg'],
            regex_filter=r'.*photo.*',
            min_size_kb=100,
            max_size_mb=10
        )
        
        mock_drive = Mock()
        engine.drive_client = mock_drive
        
        all_files = [
            {'name': 'photo1.jpg', 'size': '1024000'},
            {'name': 'video1.mp4', 'size': '2048000'},
            {'name': 'document.pdf', 'size': '512000'}
        ]
        
        # Mock filtering methods
        mock_drive.is_media_file.side_effect = lambda f: f['name'].endswith(('.jpg', '.mp4'))
        mock_drive.filter_files_by_type.return_value = [all_files[0]]  # Only jpg
        mock_drive.filter_files_by_regex.return_value = [all_files[0]]  # Only with 'photo'
        mock_drive.filter_files_by_size.return_value = [all_files[0]]  # Size filtered
        
        result = engine._filter_files(all_files)
        
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]['name'], 'photo1.jpg')

    @patch('sync_engine.GoogleAuth')
    @patch('sync_engine.DriveClient')
    @patch('sync_engine.PhotosClient')
    def test_upload_files(self, mock_photos_client, mock_drive_client, mock_auth):
        """Test file upload functionality."""
        engine = SyncEngine()
        
        mock_drive = Mock()
        mock_photos = Mock()
        engine.drive_client = mock_drive
        engine.photos_client = mock_photos
        
        files = [
            {'id': 'file1', 'name': 'photo1.jpg', 'md5Checksum': 'hash1'},
            {'id': 'file2', 'name': 'photo2.jpg', 'md5Checksum': 'hash2'}
        ]
        
        mock_drive.download_file.return_value = b'file_content'
        mock_photos.upload_media.return_value = 'upload_token'
        
        tokens, mapping, results = engine._upload_files(files, set())
        
        self.assertEqual(len(tokens), 2)
        self.assertEqual(len(mapping), 2)
        self.assertEqual(len(results), 0)  # No errors or skips

    @patch('sync_engine.GoogleAuth')
    @patch('sync_engine.DriveClient')
    @patch('sync_engine.PhotosClient')
    def test_upload_files_with_duplicate_hash(self, mock_photos_client, mock_drive_client, mock_auth):
        """Test file upload with duplicate hash detection."""
        engine = SyncEngine()
        
        mock_drive = Mock()
        mock_photos = Mock()
        engine.drive_client = mock_drive
        engine.photos_client = mock_photos
        
        files = [
            {'id': 'file1', 'name': 'photo1.jpg', 'md5Checksum': 'hash1'},
            {'id': 'file2', 'name': 'photo2.jpg', 'md5Checksum': 'hash1'}  # Same hash
        ]
        
        processed_hashes = {'hash1'}
        
        tokens, mapping, results = engine._upload_files(files, processed_hashes)
        
        self.assertEqual(len(tokens), 0)  # Both files skipped
        self.assertEqual(len(mapping), 0)
        self.assertEqual(len(results), 2)  # Both files have results
        self.assertEqual(results[0].status, 'skipped')
        self.assertEqual(results[1].status, 'skipped')

    @patch('sync_engine.GoogleAuth')
    @patch('sync_engine.DriveClient')
    @patch('sync_engine.PhotosClient')
    def test_create_and_add_media_items(self, mock_photos_client, mock_drive_client, mock_auth):
        """Test media item creation and album addition."""
        engine = SyncEngine()
        
        mock_photos = Mock()
        engine.photos_client = mock_photos
        
        upload_tokens = [('token1', 'photo1.jpg'), ('token2', 'photo2.jpg')]
        file_mapping = [
            {'name': 'photo1.jpg', 'size': '1024000'},
            {'name': 'photo2.jpg', 'size': '2048000'}
        ]
        
        mock_photos.batch_create_media_items.return_value = ['media1', 'media2']
        mock_photos.batch_add_media_to_album.return_value = None
        
        results = engine._create_and_add_media_items(
            upload_tokens, file_mapping, 'album123', set()
        )
        
        self.assertEqual(len(results), 2)
        self.assertEqual(results[0].status, 'success')
        self.assertEqual(results[1].status, 'success')
        
        mock_photos.batch_create_media_items.assert_called_once_with(upload_tokens)
        mock_photos.batch_add_media_to_album.assert_called_once_with('album123', ['media1', 'media2'])

    @patch('sync_engine.GoogleAuth')
    @patch('sync_engine.DriveClient')  
    @patch('sync_engine.PhotosClient')
    def test_sync_no_files_after_filtering(self, mock_photos_client, mock_drive_client, mock_auth):
        """Test sync when no files remain after filtering."""
        # Setup mocks
        mock_auth_instance = Mock()
        mock_auth.return_value = mock_auth_instance
        mock_auth_instance.authenticate.return_value = Mock()
        
        mock_drive = Mock()
        mock_drive_client.return_value = mock_drive
        mock_photos = Mock()
        mock_photos_client.return_value = mock_photos
        
        # Mock empty file list after filtering
        mock_drive.list_files_recursive.return_value = []
        mock_photos.get_or_create_album.return_value = 'album123'
        
        engine = SyncEngine()
        engine.sync('folder123', album_name='My Album')
        
        # Should not attempt any upload operations
        mock_drive.download_file.assert_not_called()
        mock_photos.upload_media.assert_not_called()

    def test_sync_missing_album_parameters(self):
        """Test sync with missing album parameters."""
        engine = SyncEngine()
        
        with self.assertRaises(ValueError):
            engine.sync('folder123')  # Neither album_name nor album_id provided


if __name__ == '__main__':
    unittest.main()