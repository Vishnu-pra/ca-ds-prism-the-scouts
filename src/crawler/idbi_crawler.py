#!/usr/bin/env python3
"""
IDBI Bank Notices Crawler (Simple Version)
Crawls the IDBI Bank notices page and extracts date and document URLs using requests and BeautifulSoup
Supports proxy configuration for web requests
"""

import os
import json
import ssl
import requests
from datetime import datetime
from urllib.parse import urljoin
from bs4 import BeautifulSoup
from dateutil.parser import parse

# Disable SSL certificate verification
ssl._create_default_https_context = ssl._create_unverified_context

# Constants
BASE_URL = "https://apps.idbibank.in/idbiapp/notices.aspx"

# Proxy configuration (set to None to disable)
# Format: {'http': 'http://user:pass@host:port', 'https': 'https://user:pass@host:port'}
PROXY_CONFIG = None  # Example: {'http': 'http://127.0.0.1:8080', 'https': 'https://127.0.0.1:8080'}

# Define output directory with absolute path
ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_DIR = os.path.join(ROOT_DIR, "data")
os.makedirs(OUTPUT_DIR, exist_ok=True)
OUTPUT_DIR = os.path.join(OUTPUT_DIR, "IDBI_Requests")
os.makedirs(OUTPUT_DIR, exist_ok=True)
print(f"Output directory set to: {OUTPUT_DIR}")

class IDBICrawlerSimple:
    """IDBI Bank notices crawler using requests and BeautifulSoup with proxy support"""
    
    def __init__(self, proxies=None):
        """Initialize the crawler
        
        Args:
            proxies (dict, optional): Proxy configuration dictionary. 
                Format: {'http': 'http://user:pass@host:port', 'https': 'https://user:pass@host:port'}
        """
        self.session = requests.Session()
        # Disable SSL verification
        self.session.verify = False
        # Set headers to mimic a browser
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
        })
        
        # Configure proxies if provided
        if proxies:
            self.session.proxies.update(proxies)
            print(f"Crawler initialized with proxies: {proxies}")
        else:
            print("Crawler initialized without proxies")

    def access_notices_page(self):
        """Access the IDBI Bank notices page"""
        print(f"Accessing IDBI Bank notices page: {BASE_URL}")
        try:
            response = self.session.get(BASE_URL, timeout=30)
            response.raise_for_status()  # Raise an exception for 4XX/5XX responses
            print(f"Notices page loaded successfully with status code: {response.status_code}")
            return response.text
        except Exception as e:
            print(f"Error accessing notices page: {str(e)}")
            return None

    def extract_notices(self, html_content):
        """Extract notices from the HTML content"""
        if not html_content:
            print("No HTML content to extract notices from.")
            return []
            
        print("Extracting notices from the page...")
        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # Find the notices table - try different possible IDs and classes
            notices_table = soup.find('table', {'id': 'ContentPlaceHolder1_gvNotices'}) or \
                           soup.find('table', {'class': 'table'}) or \
                           soup.find('table')
            
            # Debug information
            print(f"Found {len(soup.find_all('table'))} tables on the page")
            for i, table in enumerate(soup.find_all('table')):
                print(f"Table {i+1} - ID: {table.get('id', 'No ID')} - Class: {table.get('class', 'No Class')}")
                print(f"First few characters: {str(table)[:100]}...")
                print("-" * 50)
            
            if not notices_table:
                print("Notices table not found. The page structure might have changed.")
                return []
            
            # Extract rows (skip header row)
            rows = notices_table.find_all('tr')[1:]  # Skip header row
            
            notices = []
            for row in rows:
                try:
                    cells = row.find_all('td')
                    # The table structure is different from what we expected
                    # Based on the HTML we saw, the structure is:
                    # <td><span class="bullet-point"></span></td>
                    # <td><a href="URL">Title</a></td>
                    # <td>Date</td>
                    
                    if len(cells) >= 3:  # Ensure we have enough cells
                        # Extract title and document URL from second column
                        title_cell = cells[1]
                        title_link = title_cell.find('a')
                        
                        if title_link:
                            title = title_link.get_text(strip=True)
                            document_url = urljoin(BASE_URL, title_link['href']) if title_link.has_attr('href') else None
                        else:
                            title = title_cell.get_text(strip=True)
                            document_url = None
                        
                        # Extract date from third column
                        date_text = cells[2].get_text(strip=True)
                        
                        notice = {
                            "date": date_text,
                            "title": title,
                            "document_url": document_url,
                            "raw_html": str(row)
                        }
                        notices.append(notice)
                except Exception as e:
                    print(f"Error extracting notice from row: {str(e)}")
                    continue
            
            print(f"Extracted {len(notices)} notices")
            return notices
        
        except Exception as e:
            print(f"Error extracting notices: {str(e)}")
            import traceback
            traceback.print_exc()
            return []

    def save_notices_data(self, notices_data, filename=None):
        """Save notices data to JSON file"""
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"idbi_notices_{timestamp}.json"
        
        output_path = os.path.join(OUTPUT_DIR, filename)
        
        try:
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(notices_data, f, indent=2, ensure_ascii=False)
            print(f"Notices data saved to {output_path}")
            return output_path
        except Exception as e:
            print(f"Error saving notices data: {str(e)}")
            return None

    def crawl_notices(self):
        """Crawl the IDBI Bank notices page and extract all notices"""
        try:
            # Access the notices page
            html_content = self.access_notices_page()
            if not html_content:
                print("Failed to access the notices page. Exiting.")
                return []
            
            # Extract notices
            notices = self.extract_notices(html_content)
            
            if not notices:
                print("No notices found. Check if the site structure has changed.")
                return []
            
            # Add timestamp metadata
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            result = {
                "metadata": {
                    "timestamp": timestamp,
                    "source_url": BASE_URL,
                    "total_notices": len(notices)
                },
                "notices": notices
            }
            
            # Save results
            output_filename = f"idbi_notices_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            output_path = self.save_notices_data(result, output_filename)
            
            print("\n=== Crawl Summary ===")
            print(f"Total notices found: {len(notices)}")
            print(f"Results saved to: {output_path}")
            
            return notices
            
        except Exception as e:
            print(f"\nERROR in crawl_notices: {str(e)}")
            import traceback
            traceback.print_exc()
            return []

def main(keywords,start_date,end_date):
    """Main function to run the crawler"""
    print("Starting IDBI Bank notices crawler (Simple Version)")
    print(f"keywords: {keywords}")
    # Initialize crawler with proxy configuration if defined
    crawler = IDBICrawlerSimple(proxies=PROXY_CONFIG)
    notices = crawler.crawl_notices()
    print(f"Crawler completed. Found {len(notices)} notices")

    filtered_tenders = []
    for tender in notices:
        # Check if any of the keywords are in the title (case insensitive)
        title = tender.get('title', '').lower()
        print(f"Title: {title}")
        keyword_match = any(keyword.lower() in title for keyword in keywords)
        print(f"keyword_match: {keyword_match}")
        
        # Filter by date if date parameters are provided
        date_match = True
        if start_date and end_date and tender.get('date'):
            try:
                tender_date_str = str(tender.get('date', '')).strip()
                
                # Parse dates with explicit format DD/MM/YYYY
                if '/' in tender_date_str:
                    day, month, year = tender_date_str.split('/')
                    check_date = datetime(int(year), int(month), int(day)).date()
                else:
                    check_date = parse(tender_date_str, fuzzy=True).date()
                
                # Parse start and end dates with the same explicit format
                if isinstance(start_date, str) and '/' in start_date:
                    day, month, year = start_date.split('/')
                    start_date_parsed = datetime(int(year), int(month), int(day)).date()
                else:
                    start_date_parsed = parse(str(start_date), fuzzy=True).date()
                    
                if isinstance(end_date, str) and '/' in end_date:
                    day, month, year = end_date.split('/')
                    end_date_parsed = datetime(int(year), int(month), int(day)).date()
                else:
                    end_date_parsed = parse(str(end_date), fuzzy=True).date()
                     
                # Compare dates to check if tender date is within range
                if not (start_date_parsed <= check_date <= end_date_parsed):
                    date_match = False
                    
            except Exception as e:
                print(f"Error parsing date '{tender_date_str}': {str(e)}")
                # If there's an error parsing the date, we'll include the tender by default
                date_match = True

        if date_match and keyword_match:
            # Create a simplified tender object with only the required fields
            simplified_tender = {
                'title': tender.get('title', ''),
                'document_url': tender.get('document_url', ''),
                'opening_date': tender.get('date','')
            }
            filtered_tenders.append(simplified_tender)
    
    # Save the filtered results
    output_filename = f"idbi_bank_filtered_tenders.json"
    output_path = os.path.join(OUTPUT_DIR, output_filename)
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(filtered_tenders, f, indent=2)
    
    return filtered_tenders



if __name__ == "__main__":
    input_keywords = ["ATM"]
    start_date = "15/08/2025"  
    end_date = "18/08/2025"
    main(input_keywords,start_date,end_date)
