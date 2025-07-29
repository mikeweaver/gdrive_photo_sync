"""
Tests for the Google Drive client module.
"""

import unittest
from unittest.mock import Mock, patch, MagicMock
from drive_client import DriveClient


class TestDriveClient(unittest.TestCase):
    
    def setUp(self):
        self.mock_credentials = Mock()
        with patch('drive_client.build') as mock_build:
            self.mock_service = Mock()
            mock_build.return_value = self.mock_service
            self.client = DriveClient(self.mock_credentials)
        
    @patch('drive_client.build')
    def test_init_creates_drive_service(self, mock_build):
        """Test that DriveClient initializes the Drive service."""
        mock_service = Mock()
        mock_build.return_value = mock_service
        
        client = DriveClient(self.mock_credentials)
        
        mock_build.assert_called_once_with('drive', 'v3', credentials=self.mock_credentials)
        self.assertEqual(client.service, mock_service)
        
    def test_list_files_in_folder_success(self):
        """Test successful listing of files in a folder."""
        # Mock the service response
        mock_response = {
            'files': [
                {
                    'id': 'file1',
                    'name': 'photo1.jpg',
                    'mimeType': 'image/jpeg',
                    'size': '1024000',
                    'md5Checksum': 'abc123'
                },
                {
                    'id': 'file2',
                    'name': 'video1.mp4',
                    'mimeType': 'video/mp4',
                    'size': '5120000',
                    'md5Checksum': 'def456'
                }
            ],
            'nextPageToken': None
        }
        
        self.mock_service.files.return_value.list.return_value.execute.return_value = mock_response
        
        result = list(self.client.list_files_in_folder('folder123'))
        
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0]['name'], 'photo1.jpg')
        self.assertEqual(result[1]['name'], 'video1.mp4')
        
        # Verify API call
        self.mock_service.files.return_value.list.assert_called_with(
            q="'folder123' in parents and trashed=false",
            fields="nextPageToken, files(id, name, mimeType, size, md5Checksum, createdTime, modifiedTime)",
            pageSize=100,
            pageToken=None
        )
        
    def test_list_files_in_folder_with_pagination(self):
        """Test listing files with pagination."""
        # Mock responses for pagination
        mock_response_1 = {
            'files': [{'id': 'file1', 'name': 'photo1.jpg'}],
            'nextPageToken': 'token123'
        }
        mock_response_2 = {
            'files': [{'id': 'file2', 'name': 'photo2.jpg'}],
            'nextPageToken': None
        }
        
        mock_execute = self.mock_service.files.return_value.list.return_value.execute
        mock_execute.side_effect = [mock_response_1, mock_response_2]
        
        result = list(self.client.list_files_in_folder('folder123'))
        
        self.assertEqual(len(result), 2)
        self.assertEqual(mock_execute.call_count, 2)
        
    def test_list_files_recursive_with_subfolders(self):
        """Test recursive file listing including subfolders."""
        # Mock folder listing response
        folder_response = {
            'files': [
                {
                    'id': 'subfolder1',
                    'name': 'Subfolder 1',
                    'mimeType': 'application/vnd.google-apps.folder'
                },
                {
                    'id': 'file1',
                    'name': 'photo1.jpg',
                    'mimeType': 'image/jpeg',
                    'size': '1024000',
                    'md5Checksum': 'abc123'
                }
            ],
            'nextPageToken': None
        }
        
        # Mock subfolder files response
        subfolder_response = {
            'files': [
                {
                    'id': 'file2',
                    'name': 'photo2.jpg',
                    'mimeType': 'image/jpeg',
                    'size': '2048000',
                    'md5Checksum': 'def456'
                }
            ],
            'nextPageToken': None
        }
        
        mock_execute = self.mock_service.files.return_value.list.return_value.execute
        mock_execute.side_effect = [folder_response, subfolder_response]
        
        result = list(self.client.list_files_recursive('folder123'))
        
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0]['name'], 'photo1.jpg')
        self.assertEqual(result[1]['name'], 'photo2.jpg')
        
    def test_download_file_success(self):
        """Test successful file download."""
        mock_request = Mock()
        mock_request.execute.return_value = b'file content'
        self.mock_service.files.return_value.get_media.return_value = mock_request
        
        result = self.client.download_file('file123')
        
        self.assertEqual(result, b'file content')
        self.mock_service.files.return_value.get_media.assert_called_once_with(fileId='file123')
        
    def test_download_file_with_retry(self):
        """Test file download with retry on failure."""
        mock_request = Mock()
        # First call fails, second succeeds
        mock_request.execute.side_effect = [Exception("Network error"), b'file content']
        self.mock_service.files.return_value.get_media.return_value = mock_request
        
        with patch('time.sleep'):  # Mock sleep to speed up test
            result = self.client.download_file('file123')
            
        self.assertEqual(result, b'file content')
        self.assertEqual(mock_request.execute.call_count, 2)
        
    def test_download_file_max_retries_exceeded(self):
        """Test file download when max retries are exceeded."""
        mock_request = Mock()
        mock_request.execute.side_effect = Exception("Persistent error")
        self.mock_service.files.return_value.get_media.return_value = mock_request
        
        with patch('time.sleep'):  # Mock sleep to speed up test
            with self.assertRaises(Exception):
                self.client.download_file('file123')
                
        self.assertEqual(mock_request.execute.call_count, 3)  # Initial + 2 retries
        
    def test_is_media_file_image(self):
        """Test media file detection for images."""
        file_info = {'mimeType': 'image/jpeg'}
        self.assertTrue(self.client.is_media_file(file_info))
        
        file_info = {'mimeType': 'image/png'}
        self.assertTrue(self.client.is_media_file(file_info))
        
    def test_is_media_file_video(self):
        """Test media file detection for videos."""
        file_info = {'mimeType': 'video/mp4'}
        self.assertTrue(self.client.is_media_file(file_info))
        
        file_info = {'mimeType': 'video/avi'}
        self.assertTrue(self.client.is_media_file(file_info))
        
    def test_is_media_file_non_media(self):
        """Test media file detection for non-media files."""
        file_info = {'mimeType': 'application/pdf'}
        self.assertFalse(self.client.is_media_file(file_info))
        
        file_info = {'mimeType': 'text/plain'}
        self.assertFalse(self.client.is_media_file(file_info))
        
    def test_filter_files_by_type(self):
        """Test filtering files by type."""
        files = [
            {'name': 'photo.jpg', 'mimeType': 'image/jpeg'},
            {'name': 'video.mp4', 'mimeType': 'video/mp4'},
            {'name': 'doc.pdf', 'mimeType': 'application/pdf'}
        ]
        
        result = self.client.filter_files_by_type(files, ['jpg', 'mp4'])
        
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0]['name'], 'photo.jpg')
        self.assertEqual(result[1]['name'], 'video.mp4')
        
    def test_filter_files_by_size(self):
        """Test filtering files by size."""
        files = [
            {'name': 'small.jpg', 'size': '500'},      # 0.5 KB
            {'name': 'medium.jpg', 'size': '1500000'}, # 1.5 MB
            {'name': 'large.jpg', 'size': '10000000'}  # 10 MB
        ]
        
        # Filter: min 1KB, max 5MB
        result = self.client.filter_files_by_size(files, min_size_kb=1, max_size_mb=5)
        
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]['name'], 'medium.jpg')


if __name__ == '__main__':
    unittest.main()