#!/usr/bin/env python3
"""
Setup script for Google Drive to Google Photos Sync Tool.
"""

from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

with open("requirements.txt", "r", encoding="utf-8") as fh:
    requirements = [line.strip() for line in fh if line.strip() and not line.startswith("#")]

setup(
    name="gdrive-photo-sync",
    version="1.0.0",
    author="Google Drive Photo Sync Tool",
    description="Synchronize photos from Google Drive folders to Google Photos albums",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/mikeweaver/gdrive_photo_sync",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: End Users/Desktop",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Topic :: Multimedia :: Graphics",
        "Topic :: Internet :: WWW/HTTP :: Dynamic Content",
    ],
    python_requires=">=3.8",
    install_requires=requirements,
    entry_points={
        "console_scripts": [
            "gdrive-photo-sync=__main__:main",
        ],
    },
    include_package_data=True,
)