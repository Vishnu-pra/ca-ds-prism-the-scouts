#!/usr/bin/env python3
"""
UCO Bank Portal Crawler
Crawls the UCO Bank tender portal for tender information
"""

import os
import re
import json
import time
import ssl
import certifi
import urllib3
import logging
from datetime import datetime
from urllib.parse import urljoin
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
BASE_URL = "https://www.ucobank.com/en/web/guest/tenders"
SEARCH_URL = "https://www.ucobank.com/en/web/guest/tenders?p_p_id=com_uco_tenders_web_TendersWebPortlet_INSTANCE_blgg&p_p_lifecycle=1&p_p_state=normal&p_p_mode=view&_com_uco_tenders_web_TendersWebPortlet_INSTANCE_blgg_javax.portlet.action=getTenderDetailsByOfficeType&p_auth=e0dpOFjb"
DEFAULT_TIMEOUT = 20  # seconds

# Define output directory with absolute path
# ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_DIR = os.path.join(ROOT_DIR, "data")
os.makedirs(OUTPUT_DIR, exist_ok=True)
OUTPUT_DIR = os.path.join(OUTPUT_DIR, "UCO_Requests")
os.makedirs(OUTPUT_DIR, exist_ok=True)
print(f"Output directory set to: {OUTPUT_DIR}")

class UCOBankCrawler:
    """UCO Bank Portal crawler to extract tender information"""
    
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
        """Access the UCO Bank tenders page"""
        print(f"Accessing UCO Bank tenders page: {BASE_URL}")
        try:
            self.driver.get(BASE_URL)
            # Wait for the page to load completely
            time.sleep(5)
            screenshot_path = os.path.join(OUTPUT_DIR, f"uco_bank_tenders_page.png")
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
            
            # Print the page source for debugging
            
            # Look specifically for the search input with label "Keyword Search" and type="search"
            print("Looking for label with text 'Keyword Search'")
            label_element = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.XPATH, "//label[contains(text(), 'Keyword Search')]")),
            )
            print("Found label with text 'Keyword Search'")
            
            # Find the input element inside the label
            search_input = label_element.find_element(By.TAG_NAME, "input")
            print("Found search input inside the label")
            
            # Clear and fill the search input
            search_input.clear()
            search_input.send_keys(keyword)
            
            # Find the search button with onclick containing 'search'
            print("Looking for search button")
            search_button = self.driver.find_element(By.XPATH, "//button[contains(@onclick, 'search')]")
            print("Found search button")
            
            # Click the search button
            search_button.click()
            print("Search button clicked successfully")
            
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

        # Try multiple approaches to find tender data
        tenders = []
        
        # Approach 1: Look for tables
        print("Approach 1: Looking for tables...")
        tables = soup.find_all('table')
        print(f"Found {len(tables)} tables in the HTML")
        
        for i, table in enumerate(tables):
            print(f"Examining table {i+1}/{len(tables)}")
            table_tenders = self._extract_from_table(table)
            if table_tenders:
                print(f"Found {len(table_tenders)} tenders in table {i+1}")
                tenders.extend(table_tenders)
        
        # Approach 2: Look for divs that might contain tender information
        if not tenders:
            print("Approach 2: Looking for tender divs...")
            tenders = self._extract_from_divs(soup)
        
        # Approach 3: Look for any links that might be tender documents
        if not tenders:
            print("Approach 3: Looking for document links...")
            tenders = self._extract_from_links(soup)
        
        # Approach 4: Generic extraction of any text that looks like tender information
        if not tenders:
            print("Approach 4: Generic text extraction...")
            tenders = self._extract_generic(soup)
        
        # Filter out form elements and non-tender records
        filtered_tenders = []
        for tender in tenders:
            title = tender.get('title', '')
            
            # Skip form elements like year/month selectors
            if any(form_element in title for form_element in ['Select Year', 'Select Month', 'From', 'To']):
                continue
                
            # Skip entries with very short titles or no document URL
            if len(title) < 10 or not tender.get('document_url'):
                continue
                
            # Skip entries that don't look like actual tenders
            if not any(keyword in title.lower() for keyword in ['tender', 'bid', 'notice', 'procurement', 'proposal', 'rfp', 'extension']):
                continue
                
            filtered_tenders.append(tender)
        
        print(f"Total tenders extracted: {len(tenders)}")
        print(f"After filtering: {len(filtered_tenders)} valid tenders")
        return filtered_tenders
    
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
        
        # Check if this looks like a tender table
        tender_keywords = ['tender', 'title', 'description', 'date', 'document', 'download']
        matches = sum(1 for keyword in tender_keywords if any(keyword in text for text in header_texts))
        if matches < 1 and len(header_cells) > 1:  # If no clear tender headers, might not be a tender table
            print(f"Table headers don't look like tender data: {header_texts}")
            return []
        
        # Skip the header row
        data_rows = rows[1:]
        
        for row in data_rows:
            cells = row.find_all(['td', 'th'])
            if len(cells) < 2:  # Need at least title and date
                continue
            
            tender = {}
            
            # Try to identify which columns contain what information
            title_index = None
            date_index = None
            doc_index = None
            
            # Try to determine column meanings from header
            for i, text in enumerate(header_texts):
                if any(keyword in text for keyword in ['tender', 'title', 'subject', 'description']):
                    title_index = i
                elif any(keyword in text for keyword in ['date', 'published', 'issued']):
                    date_index = i
                elif any(keyword in text for keyword in ['document', 'download', 'file', 'link']):
                    doc_index = i
            
            # If we couldn't determine columns from header, make educated guesses
            if title_index is None:
                title_index = 0  # Usually first column is title
            if date_index is None and len(cells) > 1:
                # Look for date-like text in cells
                for i, cell in enumerate(cells):
                    text = cell.get_text(strip=True)
                    if re.search(r'\d{2}[/.-]\d{2}[/.-]\d{2,4}', text):  # Date pattern
                        date_index = i
                        break
                if date_index is None:
                    date_index = 1  # Default to second column for date
            
            # Extract tender title
            if title_index is not None and title_index < len(cells):
                title_cell = cells[title_index]
                title_link = title_cell.find('a')
                if title_link:
                    tender['title'] = title_link.get_text(strip=True)
                    tender['document_url'] = urljoin(BASE_URL, title_link.get('href', '')).replace(" ", "")

                else:
                    tender['title'] = title_cell.get_text(strip=True)
            
            # Extract date
            if date_index is not None and date_index < len(cells):
                tender['date'] = cells[date_index].get_text(strip=True)
            
            # Extract document URL if not already found
            if not tender.get('document_url') and doc_index is not None and doc_index < len(cells):
                doc_cell = cells[doc_index]
                doc_link = doc_cell.find('a')
                if doc_link and 'href' in doc_link.attrs:
                    tender['document_url'] = urljoin(BASE_URL, doc_link['href'])
            
            # If still no document URL, look for any link in the row
            if not tender.get('document_url'):
                any_link = row.find('a', href=True)
                if any_link:
                    tender['document_url'] = urljoin(BASE_URL, any_link['href'])
            
            # Only add if we have useful data
            if tender.get('title') and (tender.get('date') or tender.get('document_url')):
                tenders.append(tender)
        
        return tenders
    
    def _extract_from_divs(self, soup):
        """Extract tender data from div elements"""
        tenders = []
        
        # Look for divs that might contain tender information
        tender_containers = soup.select('div.tender-item, div.tender-container, div.tender-row, div.item, div.result-item')
        if not tender_containers:
            # Try more generic selectors
            tender_containers = soup.select('div.item, div.row-item, div.list-item, div.result')
        
        if not tender_containers:
            # Try even more generic approach - look for divs with certain classes or IDs
            for div in soup.find_all('div', class_=True):
                div_class = div.get('class', [])
                div_class_str = ' '.join(div_class).lower()
                div_id = div.get('id', '').lower()
                
                if any(keyword in div_class_str or keyword in div_id for keyword in 
                       ['tender', 'result', 'item', 'listing', 'search']):
                    tender_containers.append(div)
        
        for container in tender_containers:
            tender = {}
            
            # Try to find title
            title_elem = container.find(['h1', 'h2', 'h3', 'h4', 'h5', 'strong', 'b']) or \
                         container.find('div', class_=lambda c: c and any(x in str(c).lower() for x in ['title', 'heading', 'subject']))
            
            if title_elem:
                tender['title'] = title_elem.get_text(strip=True)
            else:
                # If no clear title element, use the first significant text
                text = container.get_text(strip=True)
                if text and len(text) > 10:  # Arbitrary minimum length
                    tender['title'] = text[:100]  # Limit length
            
            # Try to find date
            date_elem = container.find(string=re.compile(r'\d{2}[/.-]\d{2}[/.-]\d{2,4}'))
            if date_elem:
                date_match = re.search(r'\d{2}[/.-]\d{2}[/.-]\d{2,4}', date_elem)
                if date_match:
                    tender['date'] = date_match.group(0)
            
            # Try to find document link
            doc_link = container.find('a', href=True)
            if doc_link:
                tender['document_url'] = urljoin(BASE_URL, doc_link['href'])
            
            # Only add if we have useful data
            if tender.get('title') and (tender.get('date') or tender.get('document_url')):
                tenders.append(tender)
        
        return tenders
    
    def _extract_from_links(self, soup):
        """Extract tender data from links"""
        tenders = []
        
        # Look for links that might be tender documents
        links = soup.find_all('a', href=True)
        
        for link in links:
            href = link.get('href', '')
            text = link.get_text(strip=True)
            
            # Skip if too short or navigation links
            if len(text) < 10 or any(nav in text.lower() for nav in ['home', 'login', 'register', 'contact']):
                continue
                
            # Check if this looks like a tender link
            if any(keyword in text.lower() or keyword in href.lower() for keyword in 
                   ['tender', 'rfp', 'proposal', 'bid', 'document', 'download']):
                
                tender = {
                    'title': text,
                    'document_url': urljoin(BASE_URL, href)
                }
                
                # Try to find a date near this link
                parent = link.parent
                if parent:
                    date_text = parent.get_text(strip=True)
                    date_match = re.search(r'\d{2}[/.-]\d{2}[/.-]\d{2,4}', date_text)
                    if date_match:
                        tender['date'] = date_match.group(0)
                
                tenders.append(tender)
        
        return tenders
    
    def _extract_generic(self, soup):
        """Generic extraction of any text that looks like tender information"""
        tenders = []
        
        # Look for any text that contains tender-related keywords
        tender_keywords = ['tender', 'rfp', 'proposal', 'bid', 'procurement']
        
        # Find all text nodes
        for text_elem in soup.find_all(text=True):
            text = text_elem.strip()
            if not text or len(text) < 20:  # Skip short texts
                continue
                
            # Check if this looks like tender information
            if any(keyword in text.lower() for keyword in tender_keywords):
                # Get the parent element
                parent = text_elem.parent
                if parent:
                    # Extract title (use this text as title)
                    title = text[:100]  # Limit length
                    
                    tender = {'title': title}
                    
                    # Try to find a date
                    date_match = re.search(r'\d{2}[/.-]\d{2}[/.-]\d{2,4}', text)
                    if date_match:
                        tender['date'] = date_match.group(0)
                    
                    # Try to find a link
                    link = parent.find('a', href=True)
                    if link:
                        tender['document_url'] = urljoin(BASE_URL, link['href'])
                    
                    # Only add if we have useful data
                    if tender.get('title') and (tender.get('date') or tender.get('document_url')):
                        tenders.append(tender)
        
        return tenders
    
    def _extract_alternative(self, soup):
        """Alternative method to extract tender data"""
        tenders = []
        
        # Look for divs or sections that might contain tender information
        tender_containers = soup.select('div.tender-item, div.tender-container, div.tender-row')
        if not tender_containers:
            # Try more generic selectors
            tender_containers = soup.select('div.item, div.row-item, div.list-item')
        
        for container in tender_containers:
            tender = {}
            
            # Try to find title
            title_elem = container.find('h3') or container.find('h4') or container.find('div', class_='title')
            if title_elem:
                tender['title'] = title_elem.get_text(strip=True)
            
            # Try to find date
            date_elem = container.find('div', class_='date') or container.find('span', class_='date')
            if date_elem:
                tender['date'] = date_elem.get_text(strip=True)
            
            # Try to find document link
            doc_link = container.find('a', href=True)
            if doc_link:
                tender['document_url'] = urljoin(BASE_URL, doc_link['href'])
            
            # Only add if we have useful data
            if tender.get('title'):
                tenders.append(tender)
        
        print(f"Extracted {len(tenders)} tenders using alternative method")
        return tenders

    def save_tender_data(self, tender_data, filename='uco_bank_tender_data.json'):
        """Save tender data to JSON file"""
        # Use absolute path for output file
        output_path = os.path.abspath(os.path.join(OUTPUT_DIR, filename))
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
        """Crawl the UCO Bank portal for a list of keywords"""
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
            output_filename = f"uco_bank_tenders_{run_id}.json"
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

def main(input_keywords,start_date,end_date):
    """Main function to run the crawler"""
    # Define keywords to search for
    keywords = input_keywords
    # keywords = ["DLP","Digital Lending Platform","Digital Lending","Colending","Co-Lending","CLM-1","CLM-2","Convertable Loan Agreement","AI","Artificial Intelligence","AI ML","AI and ML","AI and Machine Learning","Generative AI","GenAI","Voice Bots","Personalised Videos","Document Parsing","OCR"]
    
    print(f"Starting UCO Bank Portal crawler with keywords: {keywords}")
    crawler = UCOBankCrawler(headless=True)  # Set to False to see the browser
    tenders = crawler.crawl_keywords(keywords)
    print(f"Crawler completed. Found {len(tenders)} tenders")
    # Filter tenders based on keywords and extract only required fields
    filtered_tenders = []
    for tender in tenders:

        # Filter by date if date parameters are provided
        date_match = True
        if start_date and end_date and tender.get('date'):
            try:
                tender_date_str = str(tender.get('date', '')).strip()
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
                'opening_date': tender.get('date','')
            }
            filtered_tenders.append(simplified_tender)
    
    # Save the filtered results
    output_filename = f"uco_bank_filtered_tenders.json"
    output_path = os.path.join(OUTPUT_DIR, output_filename)
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(filtered_tenders, f, indent=2)
    
    logging.info(f"Filtered {len(filtered_tenders)} tenders out of {len(tenders)} total tenders")
    logging.info(f"Filtered results saved to: {output_path}")
    
    return filtered_tenders

if __name__ == "__main__":
    # Example usage
    input_keywords = ["artificial intellingence","dlp","colending"]
    start_date = "30/08/2024"  
    end_date = "10/02/2025"
    
    # The dateutil.parser will handle all these formats automatically
    main(input_keywords, start_date, end_date)
