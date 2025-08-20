"""
Settings for the RFP Crawler

Simple configuration settings for the RFP web crawler.
"""

import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Search keywords - RFPs that match these keywords will be crawled
SEARCH_KEYWORDS = [
    "machine learning",
    "artificial intelligence",
    "data science",
    "data analytics",
    "big data",
    "predictive analytics"
]

# Websites to crawl - each website needs a type that maps to a parser
WEBSITES = [
    {
        "name": "SBI Portal",
        "url": "https://sbiportal.com",
        "type": "government",
        "search_path": "/search/opportunities",
        "rfp_path_pattern": "/opportunity/",
        "requires_login": False,
        "login_credentials": {
            "login_path": "/login",
            "username": os.getenv('SBI_PORTAL_USERNAME', ''),
            "password": os.getenv('SBI_PORTAL_PASSWORD', '')
        },
        "requires_captcha": False,
        "search_key_words": SEARCH_KEYWORDS
    },
    {
        "name": "PNB portal",
        "url": "https://www.pnb.com",
        "type": "contractor",
        "search_path": "/search/projects",
        "rfp_path_pattern": "/project/",
        "requires_login": False,
        "login_credentials": {
            "login_path": "/login",
            "username": os.getenv('PNB_PORTAL_USERNAME', ''),
            "password": os.getenv('PNB_PORTAL_PASSWORD', '')
        },
        "requires_captcha": False,
        "search_key_words": SEARCH_KEYWORDS
    }
]

# Output directory for temporary storage (until database integration)
OUTPUT_DIR = os.getenv('OUTPUT_DIR', 'output')

# Request timeout in seconds
REQUEST_TIMEOUT = 30

# User agent for web requests
USER_AGENT = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'

# Delay between requests (seconds) to avoid rate limiting
REQUEST_DELAY = 1.0


# LLM Settings
LLM_PROXY_API_KEY = os.getenv('LLM_PROXY_API_KEY', '')
LLM_PROXY_URL = os.getenv('LLM_PROXY_URL', '')
MAX_RETRIES = 3

# CSV tracker configuration (stored on GCS)
# Example: gs://your-bucket/path/to/rfp_tracker.csv
GCS_RFP_TRACKER_CSV_URI = os.getenv('GCS_RFP_TRACKER_CSV_URI', '')

# CSV column names (assumed; can be overridden via env)
CSV_COL_INTERNAL_ID = os.getenv('CSV_COL_INTERNAL_ID', 'rfp_internal_id')
CSV_COL_EXTERNAL_ID = os.getenv('CSV_COL_EXTERNAL_ID', 'rfp_external_id')
CSV_COL_ORIGINAL_FILE_PATH = os.getenv('CSV_COL_ORIGINAL_FILE_PATH', 'original_file_path')
CSV_COL_RELEVANT_RMS = os.getenv('CSV_COL_RELEVANT_RMS', 'relevant_rms')

# Local download directory for fetched files
DOWNLOAD_DIR = os.getenv('DOWNLOAD_DIR', 'output/downloads')
