# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a photo synchronization tool that synchronizes photos from Google Drive with Google Photos. The initial implementation is a command line tool to run to perform a one time import from Google Drive folder (and nested folders) to a Google Photos Album

## Repository Status

This is a brand new project. No code has been written yet.

## Reference Documentation

- Google Photos API documentation: https://developers.google.com/photos/library/reference/rest
- Google Drive API documentation: https://developers.google.com/workspace/drive/api/guides/about-files

## Design Guidance
### APIs to use
- Use the google-api-python-client API client

### Authentication
- Use the OAuth2 Local Server Flow for Google API authentication
- Save refresh tokens to avoid re-authentication
- Read and store the credentials in a credentials.json file in the root directory

### Sync Behavior
- Implement rate limits, with backoff and retry for API calls 
- Implement robust error handling and logging
- Preserve the original photo metadata
- Handle photos and videos
- Flatten nested folders on import. Do not create nested Albums in Google photos.
- Files with duplicate names, but different content, should be imported. Append a unique identifier to the imported name to prevent naming collisions. Use the Google photos API to check if a photo with the same name exists before importing.
- Files with duplicate content should not be imported. A warning message should be output when this occurs. The Google Photos API automatically handles duplicate content by returning the same mediaItems.id when identical bytes are uploaded.
- After attempting the import of each file, output the name of the file and the result
- After completing the import, launch a browser window with the Google Photos Album

### Command Line Options
- Google Drive folder ID to import from (positional argument). Sharing URLs are not supported.
- Either --album-name OR --album-id (mutually exclusive):
  - --album-name: Google Photos album name to import into. Album will be created if it does not exist.
  - --album-id: Google Photos album ID to import into. Album must already exist.
- Optional arguments to:
  - Enable verbose logging
  - Skip, rather than retry, errors. Error messages should still be emitted.
  - Only import files of particular types
  - Only import files that match a regex
  - Skip files that are below a specified size (KB)
  - Skip files that are above a specified size (MB)
  - Skip browser launch at the end
  - Reset authentication (clear refresh tokens)
 

## Coding guidance:
- Use Python
- Create a requirements.txt file
- Do not store authenticate keys/etc in source code
- Use test driven development
- For tests, mock API responses, do NOT call external APIs
- Plan for extensibility. Organize the code into these modules
  - __main__.py          # CLI entry point
  - auth.py              # Authentication handling
  - drive_client.py      # Google Drive operations
  - photos_client.py     # Google Photos operations
  - sync_engine.py       # Main sync logic
  - utils.py             # Common utilities
