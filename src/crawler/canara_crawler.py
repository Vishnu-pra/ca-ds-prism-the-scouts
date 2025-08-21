#!/usr/bin/env python3
"""
Canara Bank Portal Crawler
Crawls the Canara Bank tender portal for tender information
"""

import os
import re
import json
import time
import ssl
import certifi
import urllib3
from datetime import datetime
from urllib.parse import urljoin
import logging
from dateutil.parser import parse

# Disable SSL warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
# Import ChromeDriverManager conditionally to handle potential import errors
try:
    from webdriver_manager.chrome import ChromeDriverManager
except ImportError:
    print("ChromeDriverManager not available, will use local Chrome driver")
    ChromeDriverManager = None
from bs4 import BeautifulSoup

# Constants
BASE_URL = "https://canarabank.com/tenders"
DEFAULT_TIMEOUT = 30  # seconds

# Define output directory with absolute path
ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_DIR = os.path.join(ROOT_DIR, "data")
os.makedirs(OUTPUT_DIR, exist_ok=True)
OUTPUT_DIR = os.path.join(OUTPUT_DIR, "Canara_Requests")
os.makedirs(OUTPUT_DIR, exist_ok=True)
print(f"Output directory set to: {OUTPUT_DIR}")

class CanaraBankCrawler:
    """Canara Bank Portal crawler to extract tender information"""
    
    def __init__(self, headless=True):
        """Initialize the crawler with Chrome WebDriver"""
        # Ensure output directory exists
        os.makedirs(OUTPUT_DIR, exist_ok=True)
        
        # Set up Chrome options
        chrome_options = Options()
        if headless:
            chrome_options.add_argument("--headless")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--window-size=1920,1080")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        
        # Bypass SSL certificate verification
        chrome_options.add_argument("--ignore-certificate-errors")
        chrome_options.add_argument("--allow-insecure-localhost")
        chrome_options.add_argument("--ignore-ssl-errors")
        
        # Initialize the driver
        try:
            print("Initializing Chrome driver...")
            # Try direct initialization first (most reliable)
            self.driver = webdriver.Chrome(options=chrome_options)
            print("Successfully initialized Chrome driver directly")
        except Exception as e:
            print(f"Error with direct Chrome initialization: {str(e)}")
            try:
                # Try with ChromeDriverManager if available
                if ChromeDriverManager is not None:
                    print("Trying with ChromeDriverManager...")
                    service = Service(ChromeDriverManager().install())
                    self.driver = webdriver.Chrome(service=service, options=chrome_options)
                    print("Successfully initialized Chrome driver with ChromeDriverManager")
                else:
                    raise Exception("ChromeDriverManager not available")
            except Exception as e2:
                print(f"Error with ChromeDriverManager: {str(e2)}")
                raise Exception("Failed to initialize Chrome driver. Please ensure Chrome is installed.")

        self.driver.set_page_load_timeout(DEFAULT_TIMEOUT)
        
        print("WebDriver initialized successfully")
        
    def close_driver(self):
        """Close the WebDriver"""
        if self.driver:
            try:
                self.driver.quit()
                print("WebDriver closed successfully")
            except Exception as e:
                print(f"Error closing WebDriver: {str(e)}")

    def access_tenders_page(self):
        """Access the Canara Bank tenders page"""
        print(f"Accessing Canara Bank tenders page: {BASE_URL}")
        try:
            self.driver.get(BASE_URL)
            # Wait for the page to load completely
            time.sleep(5)
            screenshot_path = os.path.join(OUTPUT_DIR, f"canara_bank_tenders_page.png")
            self.driver.save_screenshot(screenshot_path)
            print("Tenders page loaded successfully")
            return True
        except Exception as e:
            print(f"Error accessing tenders page: {str(e)}")
            return False

    def search_keyword(self, keyword):
        """Search for a keyword in the tenders page"""
        print(f"Searching for keyword: '{keyword}'")
        try:
            # Access the tenders page directly
            self.driver.get(BASE_URL)
            time.sleep(5)  # Wait longer for the page to fully load
            
            # Take a screenshot before searching
            self.driver.save_screenshot(os.path.join(OUTPUT_DIR, f"before_search_{keyword}.png"))
            print("Saved screenshot before searching")
            
            # Look specifically for the search input with label "Search:"
            print("Looking for label with text 'Search:'")
            label_element = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.XPATH, "//label[contains(text(), 'Search:')]")),
            )
            print("Found label with text 'Search:'")
            
            # Find the input element inside the label
            search_input = label_element.find_element(By.TAG_NAME, "input")
            print("Found search input inside the label")
            
            # Clear and fill the search input
            search_input.clear()
            search_input.send_keys(keyword)
            
            # Press Enter to submit the search (Canara Bank might use Enter key for search)
            search_input.send_keys('\ue007')  # Enter key
            print("Pressed Enter key to submit search")
            
            # Wait for search results to load
            print("Waiting for search results to load...")
            time.sleep(5)
            
            # Save screenshot and HTML for debugging
            screenshot_path = os.path.join(OUTPUT_DIR, f"search_results_{keyword}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png")
            self.driver.save_screenshot(screenshot_path)
            print(f"Saved search results screenshot to {screenshot_path}")
            
            html_path = os.path.join(OUTPUT_DIR, f"search_results_html_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html")
            with open(html_path, "w", encoding="utf-8") as f:
                f.write(self.driver.page_source)
            print(f"Saved HTML content to {html_path} for debugging")
            
            return self.driver.page_source
        except Exception as e:
            print(f"Error during search process: {str(e)}")
            # Try alternative search approach if the first one fails
            try:
                print("Trying alternative search approach...")
                # Try to find any search input with type="search"
                search_input = WebDriverWait(self.driver, 10).until(
                    EC.presence_of_element_located((By.XPATH, "//input[@type='search']"))
                )
                search_input.clear()
                search_input.send_keys(keyword)
                search_input.send_keys('\ue007')  # Enter key
                print("Alternative search approach: Pressed Enter key to submit search")
                
                # Wait for search results to load
                time.sleep(5)
                
                # Save screenshot for debugging
                screenshot_path = os.path.join(OUTPUT_DIR, f"alt_search_results_{keyword}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png")
                self.driver.save_screenshot(screenshot_path)
                
                return self.driver.page_source
            except Exception as e2:
                print(f"Alternative search approach also failed: {str(e2)}")
                return None

    def extract_tenders(self, html_content):
        """Extract tender data from the HTML content"""
        if not html_content:
            print("No HTML content to extract from")
            return []
        
        # Save the HTML content for debugging
        debug_html_path = os.path.join(OUTPUT_DIR, f"search_results_html_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html")
        with open(debug_html_path, 'w', encoding='utf-8') as f:
            f.write(html_content)
        print(f"Saved HTML content to {debug_html_path} for debugging")
        
        # Parse HTML with BeautifulSoup
        soup = BeautifulSoup(html_content, 'html.parser')

        # Find tender data in tables
        tenders = []
        
        # Look for tables containing tender information
        print("Looking for tender tables...")
        tables = soup.find_all('table')
        print(f"Found {len(tables)} tables in the HTML")
        
        for i, table in enumerate(tables):
            print(f"Examining table {i+1}/{len(tables)}")
            table_tenders = self._extract_from_table(table)
            if table_tenders:
                print(f"Found {len(table_tenders)} tenders in table {i+1}")
                tenders.extend(table_tenders)
        
        print(f"Total tenders extracted: {len(tenders)}")
        
        # Return all extracted tenders
        return tenders
    
    def _extract_from_table(self, table):
        """Extract tender data from a table"""
        tenders = []
        
        # Extract rows from the table
        rows = table.find_all('tr')
        if not rows or len(rows) < 2:  # Check if there are at least 2 rows (header + data)
            return []
        
        # Try to determine if this is a tender table by checking header row
        header_row = rows[0]
        header_cells = header_row.find_all(['th', 'td'])
        header_texts = [cell.get_text(strip=True).lower() for cell in header_cells]
        
        print(f"Found table headers: {header_texts}")
        
        # Look specifically for the expected column headers
        title_index = None
        tender_date_index = None
        last_date_index = None
        doc_index = None
        
        # Try to identify column indices based on header text
        for i, text in enumerate(header_texts):
            if 'description' in text.lower() or 'tender/rfp' in text.lower():
                title_index = i
                print(f"Found title column at index {i}: '{text}'")
            elif 'tender date' in text.lower() or 'date of issue' in text.lower():
                tender_date_index = i
                print(f"Found tender date column at index {i}: '{text}'")
            elif 'last date' in text.lower() or 'closing date' in text.lower() or 'due date' in text.lower():
                last_date_index = i
                print(f"Found last date column at index {i}: '{text}'")
            elif 'document' in text.lower() or 'download' in text.lower() or 'attachment' in text.lower():
                doc_index = i
                print(f"Found document column at index {i}: '{text}'")
        
        # Skip the header row
        data_rows = rows[1:]
        
        for row in data_rows:
            cells = row.find_all(['td', 'th'])
            if len(cells) < 2:  # Need at least some data
                continue
            
            tender = {}
            
            # If we couldn't determine columns from header, try to identify based on content
            if title_index is None and len(cells) > 0:
                # Assume the first column with substantial text is the title
                for i, cell in enumerate(cells):
                    text = cell.get_text(strip=True)
                    if len(text) > 10 and not re.match(r'^\d{2}[/.-]\d{2}[/.-]\d{2,4}$', text):
                        title_index = i
                        break
            
            # If we still don't have date indices, look for date patterns
            date_indices = []
            if (tender_date_index is None or last_date_index is None) and len(cells) > 1:
                for i, cell in enumerate(cells):
                    text = cell.get_text(strip=True)
                    if re.search(r'\d{2}[/.-]\d{2}[/.-]\d{2,4}', text):
                        date_indices.append(i)
                
                # If we found date columns, assign them
                if len(date_indices) >= 2 and tender_date_index is None and last_date_index is None:
                    tender_date_index = date_indices[0]
                    last_date_index = date_indices[1]
                elif len(date_indices) == 1:
                    if tender_date_index is None:
                        tender_date_index = date_indices[0]
                    elif last_date_index is None:
                        last_date_index = date_indices[0]
            
            # Extract tender title (Description Of Tender/RFP)
            if title_index is not None and title_index < len(cells):
                title_cell = cells[title_index]
                title_link = title_cell.find('a')
                if title_link:
                    tender['title'] = title_link.get_text(strip=True)
                    tender['document_url'] = urljoin(BASE_URL, title_link.get('href', ''))
                else:
                    tender['title'] = title_cell.get_text(strip=True)
                print(f"Extracted title: {tender['title']}")
            
            # Extract tender date
            if tender_date_index is not None and tender_date_index < len(cells):
                tender['tender_date'] = cells[tender_date_index].get_text(strip=True)
                print(f"Extracted tender date: {tender['tender_date']}")
            
            # Extract last date
            if last_date_index is not None and last_date_index < len(cells):
                tender['last_date'] = cells[last_date_index].get_text(strip=True)
                print(f"Extracted last date: {tender['last_date']}")
            
            # # For backward compatibility, also set 'date' field
            # if tender.get('tender_date'):
            #     tender['date'] = tender['tender_date']
            # elif tender.get('last_date'):
            #     tender['date'] = tender['last_date']
            
            # Extract document URL if not already found
            if not tender.get('document_url') and doc_index is not None and doc_index < len(cells):
                doc_cell = cells[doc_index]
                doc_link = doc_cell.find('a')
                if doc_link and 'href' in doc_link.attrs:
                    tender['document_url'] = urljoin(BASE_URL, doc_link['href'])
                    print(f"Extracted document URL from document column: {tender['document_url']}")
            
            # If still no document URL, look for any link in the row
            if not tender.get('document_url'):
                any_link = row.find('a', href=True)
                if any_link:
                    tender['document_url'] = urljoin(BASE_URL, any_link['href'])
                    print(f"Extracted document URL from any link in row: {tender['document_url']}")
            
            # Only add if we have useful data
            if tender:
                tenders.append(tender)
                print(f"Added tender record: {tender}")
        
        return tenders
        
    def save_tender_data(self, tender_data, filename='canara_bank_tender_data.json'):
        """Save tender data to JSON file"""
        # Use absolute path for output file
        output_path = os.path.join(OUTPUT_DIR, filename)
        print(f"Saving tender data to: {output_path}")
        
        try:
            # Save the data
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(tender_data, f, indent=2)
            print(f"Successfully saved tender data to {output_path}")
            return output_path
        except Exception as e:
            print(f"ERROR saving tender data: {str(e)}")
            return None

    def crawl_keywords(self, keywords=None):
        """Crawl the Canara Bank portal for a list of keywords"""
        if keywords is None:
            keywords = ["tender"]
        
        try:
            # Create a unique run ID for this crawl session
            run_id = datetime.now().strftime("%Y%m%d_%H%M%S")
            print(f"Starting crawl session with ID: {run_id}")
            
            # Access tenders page once
            if not self.access_tenders_page():
                print("Failed to access tenders page. Aborting.")
                return []
            
            all_tenders = []
            keyword_results = {}
            
            # Process each keyword
            for i, keyword in enumerate(keywords):
                print(f"\n=== Processing keyword {i+1}/{len(keywords)}: '{keyword}' ===\n")
                
                # Try the keyword search up to 2 times if it fails
                max_attempts = 3
                search_html = None
                
                for attempt in range(1, max_attempts + 1):
                    if attempt > 1:
                        print(f"Retrying keyword '{keyword}' (attempt {attempt}/{max_attempts})")
                        # Make sure we're on the tenders page for a fresh attempt
                        self.access_tenders_page()
                    
                    # Search for the keyword
                    search_html = self.search_keyword(keyword)
                    if search_html:
                        break
                
                # Extract tenders
                if search_html:
                    keyword_tenders = self.extract_tenders(search_html)
                    print(f"Found {len(keyword_tenders)} tenders for keyword '{keyword}'")
                    
                    # Add keyword as metadata to each tender
                    for tender in keyword_tenders:
                        tender['search_keyword'] = keyword
                    
                    all_tenders.extend(keyword_tenders)
                    keyword_results[keyword] = len(keyword_tenders)
                else:
                    print(f"No search results HTML for keyword '{keyword}'")
                    keyword_results[keyword] = 0
                
                # Go back to tenders page for next keyword
                if i < len(keywords) - 1:  # If not the last keyword
                    print(f"Returning to tenders page for next keyword")
                    self.access_tenders_page()
            
            if not all_tenders:
                print("No tenders found for any of the keywords. Check if the site structure has changed.")
                return []

            # Add timestamp metadata
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            result = {
                "metadata": {
                    "run_id": run_id,
                    "keywords": keywords,
                    "timestamp": timestamp,
                    "keyword_results": keyword_results,
                    "total_tenders_found": len(all_tenders)
                },
                "tenders": all_tenders
            }
            
            # Save consolidated results
            output_filename = f"canara_bank_tenders_{run_id}.json"
            output_path = self.save_tender_data(result, output_filename)
            
            print("\n=== Crawl Summary ===\n")
            print(f"Keywords searched: {', '.join(keywords)}")
            print(f"Total tenders found: {len(all_tenders)}")
            print(f"Results by keyword:")
            for kw, count in keyword_results.items():
                print(f"  - '{kw}': {count} tenders")
            print(f"Final results saved to: {output_path}")
            
            return all_tenders
            
        except Exception as e:
            print(f"\nERROR in crawl_keywords: {str(e)}")
            import traceback
            traceback.print_exc()
            
            # Try to take a screenshot of the error state
            try:
                error_screenshot_path = os.path.join(OUTPUT_DIR, f"error_state_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png")
                self.driver.save_screenshot(error_screenshot_path)
                print(f"Saved error state screenshot to {error_screenshot_path}")
            except:
                pass
            
            return []
        finally:
            # Always close the driver
            self.close_driver()

def main(input_keywords, start_date, end_date):
    """Main function to run the crawler"""
    # Define keywords to search for
    keywords = input_keywords
    # keywords = ["DLP"]
    # keywords = ["DLP","Digital Lending Platform","Digital Lending","Colending","Co-Lending","CLM-1","CLM-2","Convertable loan agreement","AI","Artificial Intelligence","AI ML","AI and ML","AI and Machine Learning","Generative AI","GenAI","Voice Bots","Personalised Videos","Document Parsing","OCR"]
    # keywords = ["DLP","Digital Lending Platform","Digital Lending","Colending","Co-Lending"]
    print(f"Starting Canara Bank Portal crawler with keywords: {keywords}")
    crawler = CanaraBankCrawler(headless=True)  # Set to False to see the browser
    tenders = crawler.crawl_keywords(keywords)
    print(f"Crawler completed. Found {len(tenders)} tenders")

    filtered_tenders = []
    for tender in tenders:
        # Check if any of the keywords are in the title (case insensitive)
        title = tender.get('title', '').lower()
        
        # Filter by date if date parameters are provided
        date_match = True
        if start_date and end_date and tender.get('tender_date'):
            try:
                tender_date_str = str(tender.get('tender_date', '')).strip()
                check_date = parse(tender_date_str, fuzzy=True).date()
        
                start_date_parsed = parse(str(start_date), fuzzy=True).date()
                end_date_parsed = parse(str(end_date), fuzzy=True).date()
                
                # Compare dates to check if tender date is within range
                if not (start_date_parsed <= check_date <= end_date_parsed):
                    date_match = False
                    
            except Exception as e:
                print(f"Error parsing date '{tender_date_str}': {str(e)}")
                # If there's an error parsing the date, we'll include the tender by default
                date_match = True

        if date_match:
            # Create a simplified tender object with only the required fields
            simplified_tender = {
                'title': tender.get('title', ''),
                'document_url': tender.get('document_url', ''),
                'opening_date': tender.get('tender_date','')
            }
            filtered_tenders.append(simplified_tender)
    
    # Save the filtered results
    output_filename = f"canara_bank_filtered_tenders.json"
    output_path = os.path.join(OUTPUT_DIR, output_filename)
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(filtered_tenders, f, indent=2)
    
    return filtered_tenders

if __name__ == "__main__":
    input_keywords = ["DLP"]
    start_date = "11/06/2024"  
    end_date = "10/02/2025"

    main(input_keywords, start_date, end_date)
