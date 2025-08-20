"""
Crawler Manager

This module contains the CrawlerManager class responsible for orchestrating
the crawling process across multiple websites.
"""

import logging
from typing import Dict, List, Any, Optional
import time
from datetime import datetime, timedelta
from pathlib import Path

from src.parsers import get_parser_for_website
from src.utils.helpers import generate_rfp_id
from src.settings import *


class CrawlerManager:
    """
    Manages the crawling process across multiple websites.
    
    Responsible for:
    - Coordinating sequential crawling operations across configured websites
    - Handling errors and basic retries
    - Consolidating results and detecting new/updated RFPs
    """
    
    def __init__(
        self,
        websites,
        output_dir,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ):
        """
        Initialize the CrawlerManager.
        
        Args:
            websites: List of websites to crawl
            output_dir: Directory to save output files
            start_date: Crawl start date (default: yesterday)
            end_date: Crawl end date (default: yesterday)
        """
        self.websites = websites
        self.output_dir = output_dir

        # Dates default to yesterday
        yesterday = (datetime.utcnow() - timedelta(days=1)).date()
        self.start_date = (start_date.date() if isinstance(start_date, datetime) else start_date) or yesterday
        self.end_date = (end_date.date() if isinstance(end_date, datetime) else end_date) or yesterday

        self._ensure_download_dir()
        
    def _ensure_download_dir(self) -> None:
        Path(DOWNLOAD_DIR).mkdir(parents=True, exist_ok=True)

        
    def run_all(self) -> List[Dict[str, Any]]:
        """
        Run the crawler on all configured websites sequentially.
        
        Returns:
            List of dictionaries containing RFP data
        """
        all_results = []
        print(f"Starting crawler for {len(self.websites)} websites | window: {self.start_date} to {self.end_date}")
        
        # Process each website sequentially
        for website in self.websites:
            try:
                print(f"Starting crawl for {website['name']}")
                results = self.crawl_website(website)
                print(f"Completed crawling {website['name']}: found {len(results)} RFPs")
                all_results.extend(results)
            except Exception as e:
                print(f"Error crawling {website['name']}: {str(e)}")
        
        # Return normalized RFPs; downstream pipeline runs in main.py
        return all_results
    
    def crawl_website(self, website: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Crawl a specific website for RFPs.
        
        Args:
            website: Dictionary containing website configuration
            
        Returns:
            List of dictionaries containing RFP data from the website
        """
        print(f"Crawling website: {website['name']}")
        
        # Get appropriate parser for the website
        try:
            parser = get_parser_for_website(website)
        except ValueError as e:
            print(f"Error with parser: {str(e)}")
            return []
        
        # Parse RFPs
        try:
            rfps = parser.parse(start_date=self.start_date, end_date=self.end_date)
            
            # Enrich with website metadata
            for rfp in rfps:
                rfp['website_name'] = website['name']
                rfp['website_url'] = website['url']
                rfp['rfp_id'] = generate_rfp_id(rfp)

                # normalize dates: if missing start_date, default to yesterday
                if not rfp.get('start_date'):
                    rfp['start_date'] = str(self.start_date)
            # Parsers are responsible for date filtering; return as-is
            return rfps
        except Exception as e:
            print(f"Error parsing {website['name']}: {str(e)}")
            return []
