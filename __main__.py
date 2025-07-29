#!/usr/bin/env python3
"""
Google Drive to Google Photos Sync Tool

Command-line tool to synchronize photos from Google Drive folders to Google Photos albums.
"""

import logging
import argparse
import sys
from sync_engine import SyncEngine
from utils import extract_album_id_from_url, extract_folder_id_from_url

def setup_logging(verbose: bool = False) -> None:
    """Setup logging configuration."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

def main():
    parser = argparse.ArgumentParser(
        description="Sync photos and videos from Google Drive folder to Google Photos album"
    )
    parser.add_argument(
        "drive-folder-id",
        help="Google Drive folder ID or URL to import from."
    )
    parser.add_argument(
        "album-name",
        help="Google Photos album name or URL to import into. Album will be created if it does not exist."
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable verbose logging"
    )
    parser.add_argument(
        "--skip-errors",
        action="store_true",
        help="Skip errors rather than retry"
    )
    parser.add_argument(
        "--file-types",
        help="Only import files of specified types (comma-separated)"
    )
    parser.add_argument(
        "--regex-filter",
        help="Only import files matching this regex pattern"
    )
    parser.add_argument(
        "--min-size-kb",
        type=int,
        help="Skip files below this size in KB"
    )
    parser.add_argument(
        "--max-size-mb",
        type=int,
        help="Skip files above this size in MB"
    )
    parser.add_argument(
        "--no-browser",
        action="store_true",
        help="Skip launching browser at the end"
    )
    parser.add_argument(
        "--reset-auth",
        action="store_true",
        help="Reset authentication (clear refresh tokens)"
    )

    args = parser.parse_args()

    setup_logging(verbose=args.verbose)

    try:
        engine = SyncEngine(
            skip_errors=args.skip_errors,
            file_types=args.file_types.split(',') if args.file_types else None,
            regex_filter=args.regex_filter,
            min_size_kb=args.min_size_kb,
            max_size_mb=args.max_size_mb,
            launch_browser=not args.no_browser,
            reset_auth=args.reset_auth
        )
        
        # Extract Drive folder ID from URL if provided
        drive_folder_input = getattr(args, 'drive-folder-id')
        drive_folder_id = extract_folder_id_from_url(drive_folder_input)
        if not drive_folder_id:
            print(f"Error: Invalid Google Drive folder ID or URL: {drive_folder_input}")
            sys.exit(1)
            
        # Determine album target and extract ID if URL provided
        album_input = getattr(args, 'album-name')
        extracted_id = extract_album_id_from_url(album_input)
        if extracted_id:
            # It's a URL, use the extracted ID
            album_name = None
            album_id = extracted_id
        else:
            # It's a name
            album_name = album_input
            album_id = None
            
        engine.sync(drive_folder_id, album_name=album_name, album_id=album_id)
        
    except KeyboardInterrupt:
        print("\nSync cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()