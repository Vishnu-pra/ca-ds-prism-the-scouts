"""
Helper Utilities

Simplified utility functions for the RFP crawler.
"""

import re
import json
import hashlib
from typing import Dict, Any, List
from bs4 import BeautifulSoup


def sanitize_html(html_content: str) -> str:
    """
    Clean HTML content by removing scripts, styles, and other unwanted elements.
    
    Args:
        html_content: Raw HTML content
        
    Returns:
        Sanitized HTML content
    """
    soup = BeautifulSoup(html_content, 'lxml')
    
    # Remove script and style elements
    for tag in soup(['script', 'style', 'meta', 'noscript', 'iframe']):
        tag.decompose()
        
    # Get the text
    return soup.get_text(separator=' ', strip=True)


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
