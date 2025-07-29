#!/usr/bin/env python3
"""
Google Drive to Google Photos Sync Tool

Command-line tool to synchronize photos from Google Drive folders to Google Photos albums.
"""

import logging
import argparse
import sys
from sync_engine import SyncEngine

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
        help="Google Drive folder ID to import from. (Sharing URLs are not supported.)"
    )
    
    # Create mutually exclusive group for album specification
    album_group = parser.add_mutually_exclusive_group(required=True)
    album_group.add_argument(
        "--album-name",
        help="Google Photos album name to import into. Album will be created if it does not exist."
    )
    album_group.add_argument(
        "--album-id", 
        help="Google Photos album ID to import into. Album must already exist."
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
        
        # Determine album target
        if args.album_name:
            album_target = args.album_name
            is_album_id = False
        else:
            album_target = args.album_id
            is_album_id = True
            
        engine.sync(getattr(args, 'drive-folder-id'), album_target, is_album_id)
        
    except KeyboardInterrupt:
        print("\nSync cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()