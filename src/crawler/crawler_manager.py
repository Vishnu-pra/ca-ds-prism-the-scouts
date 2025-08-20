"""
Crawler Manager

This module contains the CrawlerManager class responsible for orchestrating
the crawling process across multiple websites.
"""

import logging
from typing import Dict, List, Any, Optional
import time
import random
from retrying import retry

from src.parsers import get_parser_for_website
from src.utils.helpers import generate_rfp_id


class CrawlerManager:
    """
    Manages the crawling process across multiple websites.
    
    Responsible for:
    - Coordinating sequential crawling operations across configured websites
    - Handling errors and basic retries
    - Consolidating results and detecting new/updated RFPs
    """
    
    def __init__(self, websites, output_dir):
        """
        Initialize the CrawlerManager.
        
        Args:
            websites: List of websites to crawl
            output_dir: Directory to save output files
        """
        self.websites = websites
        self.output_dir = output_dir
        self.previous_data = self._load_previous_data()
        
    def _load_previous_data(self) -> Dict[str, Any]:
        """
        Load previously crawled data.
        
        In a real implementation, this would load from a database.
        For now, we'll return an empty dictionary as a placeholder.
        
        Returns:
            Dictionary of previously crawled RFP data
        """
        # Placeholder for database integration
        return {}
        
    def run_all(self) -> List[Dict[str, Any]]:
        """
        Run the crawler on all configured websites sequentially.
        
        Returns:
            List of dictionaries containing RFP data
        """
        all_results = []
        
        self.logger.info(f"Starting crawler for {len(self.websites)} websites")
        
        # Process each website sequentially
        for website in self.websites:
            try:
                self.logger.info(f"Starting crawl for {website['name']}")
                results = self.crawl_website(website)
                self.logger.info(f"Completed crawling {website['name']}: found {len(results)} RFPs")
                all_results.extend(results)
            except Exception as e:
                self.logger.error(f"Error crawling {website['name']}: {str(e)}")
        
        # Process results to identify new and updated RFPs
        processed_results = self._process_results(all_results)
        
        return processed_results
    
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
            rfps = parser.parse()
            
            # Enrich with website metadata
            for rfp in rfps:
                rfp['website_name'] = website['name']
                rfp['website_url'] = website['url']
                rfp['rfp_id'] = generate_rfp_id(rfp)
                
            return rfps
        except Exception as e:
            print(f"Error parsing {website['name']}: {str(e)}")
            return []
    
    def _process_results(self, rfps: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Process crawling results to identify new and updated RFPs.
        
        Args:
            rfps: List of dictionaries containing raw RFP data
            
        Returns:
            List of dictionaries containing processed RFP data
        """
        processed_rfps = []
        
        for rfp in rfps:
            rfp_id = rfp.get('rfp_id')
            
            # Check if this is a new RFP or an update to an existing one
            if rfp_id not in self.previous_data:
                rfp['is_new'] = True
                rfp['is_updated'] = False
                self.logger.info(f"Found new RFP: {rfp.get('title', 'Untitled')} from {rfp.get('website_name')}")
            else:
                rfp['is_new'] = False
                previous_rfp = self.previous_data[rfp_id]
                
                # Compare with previous data to determine if updated
                if self._is_rfp_updated(previous_rfp, rfp):
                    rfp['is_updated'] = True
                    self.logger.info(f"RFP updated: {rfp.get('title', 'Untitled')} from {rfp.get('website_name')}")
                else:
                    rfp['is_updated'] = False
            
            processed_rfps.append(rfp)
            
        return processed_rfps
    
    def _is_rfp_updated(self, old_rfp: Dict[str, Any], new_rfp: Dict[str, Any]) -> bool:
        """
        Determine if an RFP has been updated by comparing key fields.
        
        Args:
            old_rfp: Dictionary containing previous RFP data
            new_rfp: Dictionary containing new RFP data
            
        Returns:
            True if the RFP has been updated, False otherwise
        """
        # Only check the most important fields for updates
        fields_to_compare = ['title', 'description', 'deadline', 'status']
        
        for field in fields_to_compare:
            if old_rfp.get(field) != new_rfp.get(field):
                return True
                
        return False
