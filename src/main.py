#!/usr/bin/env python3
"""
RFP Web Crawler - Main Entry Point

This module serves as the main entry point for the RFP Crawler

Simplified script to orchestrate the RFP crawling process.
"""

import os
import json
import sys
import logging
from datetime import datetime

# Add src to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import settings and crawler manager
from src.settings import WEBSITES, OUTPUT_DIR
from src.crawler_manager import CrawlerManager


def main():
    """\n    Main entry point for the RFP crawler.\n    """
    # Configure basic logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    print("Starting RFP Crawler")
    
    try:
        # Create crawler manager
        crawler_manager = CrawlerManager(
            websites=WEBSITES,
            output_dir=OUTPUT_DIR
        )
        
        # Run crawler
        stats = crawler_manager.crawl_all()
        
        # Save stats
        stats_file = os.path.join(OUTPUT_DIR, f"stats_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
        with open(stats_file, 'w', encoding='utf-8') as f:
            json.dump(stats, f, indent=2)
            
        print(f"Crawling completed. Found {stats['new_rfps']} new RFPs")
        print(f"Updated {stats['updated_rfps']} existing RFPs")
        print(f"Stats saved to {stats_file}")
        
    except Exception as e:
        print(f"Error in main process: {str(e)}")
    
    print("RFP Crawler finished")


if __name__ == "__main__":
    main()
