"""
Base Parser

Minimal base parser that serves as a foundation for all website-specific parser implementations.
Provides only the most essential common utilities. All parsing logic is implemented in child classes.
"""

import requests
from abc import ABC, abstractmethod
from typing import Dict, List, Any
from urllib.parse import urlparse, urljoin


class BaseParser(ABC):
    """
    Abstract base class for website parsers.

    Provides minimal common functionality for all parsers:
    - Basic configuration setup
    - HTTP request handling
    - URL resolution

    Each website parser must implement its own parsing logic.
    """
    
    def __init__(self, website_config: Dict[str, Any]):
        """
        Initialize the BaseParser.

        Args:
            website_config: Dictionary containing website configuration
        """
        # Store the website configuration
        self.config = website_config
        self.name = website_config.get('name', 'Unknown')
        self.url = website_config.get('url', '')

        # Extract base URL (scheme + domain) for resolving relative URLs
        parsed = urlparse(self.url)
        self.base_url = f"{parsed.scheme}://{parsed.netloc}"

        # Create a session for HTTP requests
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })
        
    def request(self, url: str, method: str = 'GET', params=None, data=None, timeout: int = 30):
        """
        Make an HTTP request with simple error handling.

        Args:
            url: URL to request
            method: HTTP method (GET, POST, etc.)
            params: URL parameters
            data: Request body data
            timeout: Request timeout in seconds

        Returns:
            Response object or None if request fails
        """
        try:
            print(f"Requesting URL: {url}")
            response = self.session.request(
                method=method,
                url=url,
                params=params,
                data=data,
                timeout=timeout
            )
            response.raise_for_status()
            return response
        except requests.exceptions.RequestException as e:
            print(f"Request error for {url}: {str(e)}")
            return None
            
    def resolve_url(self, relative_url: str) -> str:
        """
        Resolve a relative URL against the base URL.

        Args:
            relative_url: Relative URL

        Returns:
            Absolute URL
        """
        return urljoin(self.base_url, relative_url)
        
    @abstractmethod
    def parse(self, start_date=None, end_date=None) -> List[Dict[str, Any]]:
        """
        Parse the website for RFPs.

        Each parser must implement this method to handle the specific logic needed
        for its website. This includes identifying RFPs, extracting their details,
        and filtering based on relevant criteria.

        Returns:
            List of dictionaries containing RFP data
        """
        pass
    
    @abstractmethod
    def solve_captcha(self, image_url: str) -> str:
        """
        Placeholder function for solving captchas that may appear on government sites.

        Args:
            image_url: URL to the captcha image

        Returns:
            Captcha solution as a string
        """
        print(f"Would solve captcha at {image_url}")
        # In a real implementation, this would use an external service or OCR
        return "sample_solution"

    @abstractmethod
    def login(self, username: str, password: str) -> bool:
        """
        Placeholder function for logging in to password-protected RFP sites.

        Args:
            username: Login username
            password: Login password

        Returns:
            True if login successful, False otherwise
        """
        print(f"Would login with username {username}")
        # In a real implementation, this would authenticate with the website
        return True
