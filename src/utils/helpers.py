"""
Helper Utilities

Simplified utility functions for the RFP crawler.
"""

import re
import json
import hashlib
from typing import Dict, Any, List
from bs4 import BeautifulSoup
import os
from urllib.parse import urlparse
import requests
import pandas as pd
import tempfile
from google.cloud import storage
from google.oauth2 import service_account
from src.settings import *


def generate_rfp_id(rfp: Dict[str, Any]) -> str:
    """
    Generate a simple unique ID for an RFP based on its URL and title.
    
    Args:
        rfp: Dictionary containing RFP data
        
    Returns:
        Unique ID for the RFP
    """
    # Generate ID from URL and title
    url = rfp.get('url', '')
    title = rfp.get('title', '')
    website = rfp.get('website_name', '')
    
    # Create a string to hash
    id_string = f"{url}|{title}|{website}"
    
    # Generate a hash
    return hashlib.md5(id_string.encode()).hexdigest()


def matches_keywords(text: str, keywords: List[str], match_all: bool = False) -> bool:
    """
    Check if text matches any or all of the given keywords.
    
    Args:
        text: Text to search in
        keywords: List of keywords to search for
        match_all: If True, all keywords must match; otherwise any match is sufficient
        
    Returns:
        True if the text matches the keywords based on the match_all parameter
    """
    text = text.lower()
    
    if match_all:
        return all(keyword.lower() in text for keyword in keywords)
    else:
        return any(keyword.lower() in text for keyword in keywords)


def has_rfp_changed(old_rfp: Dict[str, Any], new_rfp: Dict[str, Any]) -> bool:
    """
    Check if an RFP has significant changes between versions.
    
    Args:
        old_rfp: Dictionary containing previous RFP data
        new_rfp: Dictionary containing new RFP data
        
    Returns:
        True if there are significant changes, False otherwise
    """
    # Important fields to check for changes
    fields_to_compare = ['title', 'description', 'deadline', 'status']
    
    for field in fields_to_compare:
        if old_rfp.get(field) != new_rfp.get(field):
            return True
    
    return False


def download_file_from_url(url: str, title: str, download_dir: str, timeout: int = 60) -> str:
    """
    Download a file from a URL to the given download directory.

    Args:
        url: Source URL of the file.
        title: RFP title used to build a safe filename.
        index: Index of the file among attachments to ensure uniqueness.
        download_dir: Directory to save the file.
        timeout: Request timeout in seconds.

    Returns:
        The local file path if successful, else an empty string.
    """
    try:
        if not url:
            return ""
        os.makedirs(download_dir, exist_ok=True)
        safe_title = (title or 'rfp').replace('/', '_').replace(' ', '_')[:50]

        ext = os.path.splitext(urlparse(url).path)[1] or '.pdf'
        filename = f"{safe_title}{ext}"
        local_path = os.path.join(download_dir, filename)
        with requests.get(url, stream=True, timeout=timeout) as resp:
            resp.raise_for_status()
            with open(local_path, 'wb') as f:
                for chunk in resp.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
        return local_path
    except Exception as e:
        print(f"Error downloading {url}: {e}")
        return ""
        
def save_tracker_df(df: pd.DataFrame) -> None:
    """Save tracker DataFrame to local artifacts and upload to GCS (overwrites blob)."""
    if df is None:
        return
    try:
        os.makedirs(ARTIFACTS_DIR, exist_ok=True)
        local_path = os.path.join(ARTIFACTS_DIR, GCS_TRACKER_BLOB_NAME)
        # Save locally first
        df.to_csv(local_path, index=False)
        # Upload to GCS
        upload_file_to_gcs(
            local_file_path=local_path,
            bucket_name=GCS_BUCKET_NAME,
            destination_blob_name=GCS_TRACKER_BLOB_NAME,
            key_path=GCS_SERVICE_ACCOUNT_KEY_PATH,
        )
        print(f"Tracker CSV saved locally at {local_path} and to gs://{GCS_BUCKET_NAME}/{GCS_TRACKER_BLOB_NAME}")
    except Exception as e:
        print(f"Warning: could not save tracker CSV: {e}")


def get_gcs_client(key_path: str) -> storage.Client:
    """Initialize a Google Cloud Storage client using a service account JSON key file."""
    try:
        credentials = service_account.Credentials.from_service_account_file(
            key_path, scopes=["https://www.googleapis.com/auth/cloud-platform"]
        )
        return storage.Client(credentials=credentials)
    except Exception as e:
        print(f"Error initializing GCS client: {e}")
        raise


def upload_file_to_gcs(local_file_path: str, bucket_name: str, destination_blob_name: str, key_path: str) -> str:
    """Upload a local file to GCS and return the gs:// URI."""
    try:
        if not os.path.exists(local_file_path):
            raise FileNotFoundError(f"Local file not found: {local_file_path}")
        client = get_gcs_client(key_path)
        bucket = client.bucket(bucket_name)
        blob = bucket.blob(destination_blob_name)
        blob.upload_from_filename(local_file_path)
        return f"{bucket_name}/{destination_blob_name}"
    except Exception as e:
        print(f"Error uploading file to GCS: {e}")
        raise


def download_file_from_gcs(bucket_name: str, source_blob_name: str, destination_file_path: str, key_path: str) -> str:
    """Download a GCS blob to a local path and return the local path."""
    try:
        client = get_gcs_client(key_path)
        bucket = client.bucket(bucket_name)
        blob = bucket.blob(source_blob_name)
        os.makedirs(os.path.dirname(destination_file_path), exist_ok=True)
        blob.download_to_filename(destination_file_path)
        return destination_file_path
    except Exception as e:
        print(f"Error downloading file from GCS: {e}")
        raise


def load_tracker_df() -> pd.DataFrame:
    """Load tracker CSV by syncing from GCS to artifacts directory, then reading locally.

    Falls back to reading the local copy if GCS download fails.
    """
    local_path = os.path.join(ARTIFACTS_DIR, GCS_TRACKER_BLOB_NAME)
    try:
        os.makedirs(ARTIFACTS_DIR, exist_ok=True)
        # Try to refresh local copy from GCS
        download_file_from_gcs(
            bucket_name=GCS_BUCKET_NAME,
            source_blob_name=GCS_TRACKER_BLOB_NAME,
            destination_file_path=local_path,
            key_path=GCS_SERVICE_ACCOUNT_KEY_PATH,
        )
    except Exception as e:
        print(f"Warning: could not download tracker CSV from GCS, using local if present: {e}")
    # Read local copy if exists
    try:
        if os.path.exists(local_path):
            return pd.read_csv(local_path)
    except Exception as e:
        print(f"Warning: could not read local tracker CSV at {local_path}: {e}")
    return pd.DataFrame()
