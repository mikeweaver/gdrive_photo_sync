"""
Tests for the authentication module.
"""

import unittest
from unittest.mock import Mock, patch, mock_open
import json
import os
from auth import GoogleAuth


class TestGoogleAuth(unittest.TestCase):
    
    def setUp(self):
        self.auth = GoogleAuth()
        
    def test_init_sets_correct_scopes(self):
        """Test that GoogleAuth initializes with correct scopes."""
        expected_scopes = [
            'https://www.googleapis.com/auth/drive.readonly',
            'https://www.googleapis.com/auth/photoslibrary'
        ]
        self.assertEqual(self.auth.scopes, expected_scopes)
        
    @patch('auth.os.path.exists')
    def test_credentials_file_not_exists(self, mock_exists):
        """Test behavior when credentials.json doesn't exist."""
        mock_exists.return_value = False
        
        with self.assertRaises(FileNotFoundError):
            self.auth._load_client_secrets()
            
    @patch('auth.os.path.exists')
    @patch('builtins.open', new_callable=mock_open, read_data='{"test": "data"}')
    def test_load_client_secrets_success(self, mock_file, mock_exists):
        """Test successful loading of client secrets."""
        mock_exists.return_value = True
        
        result = self.auth._load_client_secrets()
        
        mock_file.assert_called_once_with('credentials.json', 'r')
        self.assertEqual(result, {"test": "data"})
        
    @patch('auth.os.path.exists')
    def test_has_valid_token_no_file(self, mock_exists):
        """Test has_valid_token when token file doesn't exist."""
        mock_exists.return_value = False
        
        self.assertFalse(self.auth._has_valid_token())
        
    @patch('auth.os.path.exists')
    @patch('builtins.open', new_callable=mock_open)
    @patch('auth.Credentials.from_authorized_user_file')
    @patch('auth.Request')
    def test_has_valid_token_expired(self, mock_request, mock_from_file, mock_file, mock_exists):
        """Test has_valid_token when token is expired but can be refreshed."""
        mock_exists.return_value = True
        mock_creds = Mock()
        mock_creds.valid = False
        mock_creds.expired = True
        mock_creds.refresh_token = 'refresh_token'
        mock_from_file.return_value = mock_creds
        
        # Mock successful refresh
        def refresh_side_effect(request):
            mock_creds.valid = True
            mock_creds.expired = False
            
        mock_creds.refresh.side_effect = refresh_side_effect
        
        result = self.auth._has_valid_token()
        
        self.assertTrue(result)  # Should be True after successful refresh
        mock_creds.refresh.assert_called_once()
        
    @patch('auth.os.path.exists')
    @patch('builtins.open', new_callable=mock_open)
    @patch('auth.Credentials.from_authorized_user_file')
    def test_has_valid_token_valid(self, mock_from_file, mock_file, mock_exists):
        """Test has_valid_token when token is valid."""
        mock_exists.return_value = True
        mock_creds = Mock()
        mock_creds.valid = True
        mock_from_file.return_value = mock_creds
        
        result = self.auth._has_valid_token()
        
        self.assertTrue(result)
        self.assertEqual(self.auth.credentials, mock_creds)
        
    @patch('auth.os.path.exists')
    def test_clear_tokens_no_file(self, mock_exists):
        """Test clear_tokens when no token file exists."""
        mock_exists.return_value = False
        
        # Should not raise an exception
        self.auth.clear_tokens()
        
    @patch('auth.os.path.exists')
    @patch('auth.os.remove')
    def test_clear_tokens_success(self, mock_remove, mock_exists):
        """Test successful token clearing."""
        mock_exists.return_value = True
        
        self.auth.clear_tokens()
        
        mock_remove.assert_called_once_with('token.json')
        self.assertIsNone(self.auth.credentials)
        
    @patch.object(GoogleAuth, '_has_valid_token')
    @patch.object(GoogleAuth, '_perform_device_flow')
    def test_authenticate_with_valid_token(self, mock_device_flow, mock_has_valid):
        """Test authenticate when valid token exists."""
        mock_has_valid.return_value = True
        mock_creds = Mock()
        self.auth.credentials = mock_creds
        
        result = self.auth.authenticate()
        
        self.assertEqual(result, mock_creds)
        mock_device_flow.assert_not_called()
        
    @patch.object(GoogleAuth, '_has_valid_token')
    @patch.object(GoogleAuth, '_perform_device_flow')
    def test_authenticate_needs_new_token(self, mock_device_flow, mock_has_valid):
        """Test authenticate when new token is needed."""
        mock_has_valid.return_value = False
        mock_creds = Mock()
        mock_device_flow.return_value = mock_creds
        
        result = self.auth.authenticate()
        
        self.assertEqual(result, mock_creds)
        mock_device_flow.assert_called_once()
        
    @patch.object(GoogleAuth, '_load_client_secrets')
    @patch('auth.InstalledAppFlow.from_client_config')
    @patch('builtins.open', new_callable=mock_open)
    def test_perform_device_flow_success(self, mock_file, mock_flow_class, mock_load_secrets):
        """Test successful device flow authentication."""
        mock_secrets = {"test": "config"}
        mock_load_secrets.return_value = mock_secrets
        
        mock_flow = Mock()
        mock_creds = Mock()
        mock_creds.to_json.return_value = '{"token": "data"}'
        mock_flow.run_console.return_value = mock_creds
        mock_flow_class.return_value = mock_flow
        
        result = self.auth._perform_device_flow()
        
        mock_flow_class.assert_called_once_with(mock_secrets, self.auth.scopes)
        mock_flow.run_console.assert_called_once()
        mock_file.assert_called_once_with('token.json', 'w')
        self.assertEqual(result, mock_creds)
        self.assertEqual(self.auth.credentials, mock_creds)


if __name__ == '__main__':
    unittest.main()