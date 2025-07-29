"""
Authentication module for Google APIs using Device Flow.
"""

import json
import logging
import os
from typing import Optional

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow


logger = logging.getLogger(__name__)


class GoogleAuth:
    """Handles Google API authentication using Device Flow."""
    
    def __init__(self):
        self.scopes = [
            'https://www.googleapis.com/auth/drive.readonly',
            'https://www.googleapis.com/auth/photoslibrary.appendonly',
            'https://www.googleapis.com/auth/photoslibrary.edit.appcreateddata',
            'https://www.googleapis.com/auth/photoslibrary.readonly',
            'https://www.googleapis.com/auth/photoslibrary.readonly.appcreateddata'
        ]
        self.credentials: Optional[Credentials] = None
        
    def authenticate(self) -> Credentials:
        """
        Authenticate with Google APIs.
        
        Returns:
            Valid Google credentials
            
        Raises:
            Exception: If authentication fails
        """
        logger.info("Starting authentication process...")
        
        if self._has_valid_token():
            logger.info("Using existing valid token")
            return self.credentials
            
        logger.info("No valid token found, starting device flow")
        return self._perform_device_flow()
        
    def clear_tokens(self) -> None:
        """Clear stored authentication tokens."""
        if os.path.exists('token.json'):
            os.remove('token.json')
            logger.info("Cleared stored tokens")
        self.credentials = None
        
    def _has_valid_token(self) -> bool:
        """
        Check if a valid token exists.
        
        Returns:
            True if valid token exists, False otherwise
        """
        if not os.path.exists('token.json'):
            return False
            
        try:
            self.credentials = Credentials.from_authorized_user_file('token.json', self.scopes)
            
            if not self.credentials.valid:
                if self.credentials.expired and self.credentials.refresh_token:
                    logger.info("Token expired, attempting refresh")
                    self.credentials.refresh(Request())
                    self._save_token()
                    return True
                else:
                    logger.info("Token invalid and cannot be refreshed")
                    return False
                    
            return True
            
        except Exception as e:
            logger.error(f"Error checking token validity: {e}")
            return False
            
    def _perform_device_flow(self) -> Credentials:
        """
        Perform device flow authentication.
        
        Returns:
            Valid Google credentials
            
        Raises:
            Exception: If device flow fails
        """
        try:
            client_config = self._load_client_secrets()
            flow = InstalledAppFlow.from_client_config(client_config, self.scopes)
            
            logger.info("Starting OAuth flow authentication")
            print("Please complete the authentication in your web browser...")
            self.credentials = flow.run_local_server(port=0)
            
            self._save_token()
            logger.info("Authentication successful")
            
            return self.credentials
            
        except Exception as e:
            logger.error(f"Device flow authentication failed: {e}")
            raise
            
    def _load_client_secrets(self) -> dict:
        """
        Load client secrets from credentials.json.
        
        Returns:
            Client configuration dictionary
            
        Raises:
            FileNotFoundError: If credentials.json doesn't exist
        """
        if not os.path.exists('credentials.json'):
            raise FileNotFoundError(
                "credentials.json not found. Please download it from Google Cloud Console."
            )
            
        with open('credentials.json', 'r') as f:
            return json.load(f)
            
    def _save_token(self) -> None:
        """Save credentials to token.json."""
        with open('token.json', 'w') as f:
            f.write(self.credentials.to_json())