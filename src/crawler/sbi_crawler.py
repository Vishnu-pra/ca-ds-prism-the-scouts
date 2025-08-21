#!/usr/bin/env python3
"""
SBI Portal Crawler
Crawls the SBI e-tender portal for tender information with focus on extracting document details
"""

import os
import re
import json
import time
import logging
from datetime import datetime
from urllib.parse import urljoin, urlparse
import requests
from bs4 import BeautifulSoup
from dateutil import parser as date_parser

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
try:
    from webdriver_manager.chrome import ChromeDriverManager
except ImportError:
    print("ChromeDriverManager not available, will use local Chrome driver")
    ChromeDriverManager = None

# Constants
BASE_URL = "https://etender.sbi/SBI/"
SEARCH_URL = "https://etender.sbi/SBI/"
DEFAULT_TIMEOUT = 20  # seconds
REQUEST_TIMEOUT = 30  # seconds for HTTP requests
MAX_RETRIES = 3      # Maximum retries for HTTP requests

# Define output directory with absolute path
ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_DIR = os.path.join(ROOT_DIR, "data")
os.makedirs(OUTPUT_DIR, exist_ok=True)
OUTPUT_DIR = os.path.join(OUTPUT_DIR, "SBI_Requests_New")
os.makedirs(OUTPUT_DIR, exist_ok=True)
print(f"Output directory set to: {OUTPUT_DIR}")

# Configure logging
log_file = os.path.join(OUTPUT_DIR, "sbi_crawler.log")
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file),
        logging.StreamHandler()
    ]
)

class SBICrawler:
    """SBI Portal crawler to extract tender information with document details"""
    
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
        
        # Initialize the driver
        try:
            logging.info("Initializing Chrome driver...")
            # Try direct initialization first (most reliable)
            self.driver = webdriver.Chrome(options=chrome_options)
            logging.info("Successfully initialized Chrome driver directly")
        except Exception as e:
            logging.error(f"Error with direct Chrome initialization: {str(e)}")
            try:
                # Try with ChromeDriverManager if available
                if ChromeDriverManager is not None:
                    logging.info("Trying with ChromeDriverManager...")
                    service = Service(ChromeDriverManager().install())
                    self.driver = webdriver.Chrome(service=service, options=chrome_options)
                    logging.info("Successfully initialized Chrome driver with ChromeDriverManager")
                else:
                    raise Exception("ChromeDriverManager not available")
            except Exception as e2:
                logging.error(f"Error with ChromeDriverManager: {str(e2)}")
                raise Exception("Failed to initialize Chrome driver. Please ensure Chrome is installed.")

        self.driver.set_page_load_timeout(DEFAULT_TIMEOUT)
        logging.info("WebDriver initialized successfully")
        
    def close_driver(self):
        """Close the WebDriver"""
        if self.driver:
            try:
                self.driver.quit()
                logging.info("WebDriver closed successfully")
            except Exception as e:
                logging.error(f"Error closing WebDriver: {str(e)}")

    def access_homepage(self):
        """Access the SBI Portal homepage"""
        logging.info(f"Accessing SBI Portal homepage: {BASE_URL}")
        try:
            self.driver.get(BASE_URL)
            # Wait for the page to load completely
            time.sleep(5)
            screenshot_path = os.path.join(OUTPUT_DIR, f"sbi_homepage.png")
            self.driver.save_screenshot(screenshot_path)
            logging.info("Homepage loaded successfully")
            return True
        except Exception as e:
            logging.error(f"Error accessing homepage: {str(e)}")
            return False

    def search_keyword(self, keyword):
        """
        Search for a keyword on the SBI portal
        Returns the HTML content after search
        """
        logging.info(f"Searching for keyword: '{keyword}'")
        try:
            # Find and fill the search input
            time.sleep(3)
            search_input = self.driver.find_element(By.ID, "txtKeywordSearch")
            search_input.clear()
            search_input.send_keys(keyword)
            logging.info(f"Entered keyword: '{keyword}' in search field")
            
            # Find the search button and click it
            search_button = self.driver.find_element(By.XPATH, "//button[contains(text(), 'Search') or contains(@id, 'search')]")
            search_button.click()
            logging.info("Search button clicked successfully")
            
            # Wait for search results to load
            logging.info("Waiting for search results to load...")
            time.sleep(3)  # Basic wait for the results to load
            
            # Take a screenshot of the results
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            screenshot_path = os.path.join(OUTPUT_DIR, f"search_results_{keyword}_{timestamp}.png")
            try:
                self.driver.save_screenshot(screenshot_path)
                logging.info(f"Saved search results screenshot to {screenshot_path}")
            except Exception as e:
                logging.error(f"Error saving screenshot: {str(e)}")
                
            return self.driver.page_source
        except Exception as e:
            logging.error(f"Error during search process: {str(e)}")
            # Save a screenshot of the error state
            try:
                error_screenshot_path = os.path.join(OUTPUT_DIR, f"search_error_{keyword}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png")
                self.driver.save_screenshot(error_screenshot_path)
                logging.info(f"Saved error state screenshot to {error_screenshot_path}")
            except:
                pass
            return None

    def extract_tenders(self, html_content):
        """
        Extract tender data from the HTML content
        """
        if not html_content:
            logging.warning("No HTML content to extract from")
            return []
        
        # Parse HTML with BeautifulSoup
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # Find table rows that contain tender data
        rows = soup.find_all('tr')
        
        # If no table rows found, try some alternative selectors
        if not rows or len(rows) < 5:
            logging.warning("Few table rows found, trying alternative selectors")
            # Look for divs that might contain tender data
            alt_containers = soup.select('div.searchResult, div.resultItem, div.result-item, div.item')
            if alt_containers:
                logging.info(f"Found {len(alt_containers)} alternative containers")
                return self._extract_from_containers(alt_containers, container_type="alternative")
        
        return self._extract_from_containers(rows, container_type="table_row")
    
    def _extract_from_containers(self, containers, container_type="table_row"):
        """Extract tender data from containers"""
        results = []
        logging.info(f"Found {len(containers)} potential {container_type} containers")
        
        for container in containers:
            container_text = container.get_text(strip=True)
            
            # Skip if too short
            if len(container_text) < 20:
                continue
                
            tender_item = {
                'container_type': container_type,
                'raw_text_sample': container_text[:100] + '...' if len(container_text) > 100 else container_text
            }
            
            # Extract title - first try SBI pattern, then general
            title_match = re.search(r'SBI\s*:\s*([^|:]+)', container_text)
            if not title_match:
                title_match = re.search(r'^(.+?)\s*(?:Due date|\|)', container_text)
                
            if title_match:
                tender_item['title'] = title_match.group(1).strip()
            elif 'SBI' in container_text[:50]:
                tender_item['title'] = container_text[:50].strip() + '...'
            
            # Extract due date
            due_date_match = re.search(r'Due date[^:]*:\s*([\d/]+\s*[\d:]+)', container_text)
            if due_date_match:
                tender_item['due_date'] = due_date_match.group(1).strip()
            
            # Extract Event ID
            event_id_match = re.search(r'Event ID:\s*(\d+)', container_text)
            if event_id_match:
                tender_item['event_id'] = event_id_match.group(1)
            
            # Extract Status
            status_match = re.search(r'Status:\s*([^\|\n]+)', container_text)
            if status_match:
                tender_item['status'] = status_match.group(1).strip()

            # Extract Corrigendum status
            corrigendum_match = re.search(r'Corrigendum:\s*([^\|\n]+)', container_text)
            if corrigendum_match:
                tender_item['corrigendum'] = corrigendum_match.group(1).strip()
                if isinstance(tender_item['corrigendum'], str):
                    # Extract corrigendum number if available
                    tender_item['corrigendum'] = int(re.search(r'\d+', tender_item['corrigendum']).group()) if re.search(r'\d+', tender_item['corrigendum']) else None

            # Extract document URL and download URL
            download_link = container.find('a', string=lambda t: t and ('Download' in t or 'download' in t))
            if download_link and 'href' in download_link.attrs:
                document_url = urljoin(BASE_URL, download_link['href'])
                tender_item['document_url'] = document_url
                tender_item['download_text'] = download_link.get_text(strip=True)
            else:
                # If no direct download link found, check for any link
                any_link = container.find('a')
                if any_link and 'href' in any_link.attrs:
                    document_url = urljoin(BASE_URL, any_link['href'])
                    tender_item['document_url'] = document_url
                    tender_item['link_text'] = any_link.get_text(strip=True)
            
            # Only add if we have useful data
            if tender_item.get('title') and tender_item.get('document_url'):
                results.append(tender_item)
        
        logging.info(f"Extracted {len(results)} tenders from {container_type} containers")
        return results

    def extract_document_details(self, document_url):
        """
        Uses Selenium to click on the document URL and navigate to the next page
        """
        if not document_url:
            logging.warning("No document URL provided")
            return None
            
        # Normalize URL
        parsed_url = urlparse(document_url)
        if not parsed_url.scheme:
            document_url = urljoin(BASE_URL, document_url)
            
        # Try multiple times in case of network issues
        for attempt in range(MAX_RETRIES):
            try:
                logging.info(f"Accessing document URL: {document_url} (attempt {attempt+1}/{MAX_RETRIES})")
                
                # Use Selenium to navigate to the document URL
                self.driver.get(document_url)
                logging.info(f"Navigated to document URL: {document_url}")
                
                # Wait for the page to load
                time.sleep(3)
                
                # Take a screenshot of the document page
                doc_screenshot_path = os.path.join(OUTPUT_DIR, f"document_page_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png")
                self.driver.save_screenshot(doc_screenshot_path)
                logging.info(f"Saved document page screenshot to {doc_screenshot_path}")
                

                # Look for links to the next page or download links
                download_links = []
                
                # Method 1: Look for direct download links
                links = self.driver.find_elements(By.XPATH, "//a[contains(@href, '.pdf') or contains(@href, 'download') or contains(text(), 'Download') or contains(text(), 'download')]")
                for link in links:
                    try:
                        href = link.get_attribute('href')
                        text = link.text
                        if href:
                            download_links.append((href, text))
                            logging.info(f"Found potential download link: {href} with text: {text}")
                    except Exception as e:
                        logging.warning(f"Error getting link attributes: {str(e)}")
                
                # Method 2: Look for buttons that might lead to download page
                buttons = self.driver.find_elements(By.XPATH, "//button[contains(text(), 'Download') or contains(text(), 'download') or contains(text(), 'View')]")
                
                # If we found download links directly, use the last one
                if download_links:
                    pdf_url = download_links[-1][0]  # Use the last link instead of the first
                    logging.info(f"Using direct download link (last one): {pdf_url}")
                    return pdf_url
                
                # If we found buttons, try clicking the first one to navigate to download page
                elif buttons:
                    logging.info(f"Found {len(buttons)} potential download buttons, clicking the first one")
                    try:
                        buttons[0].click()
                        logging.info("Clicked on download button")
                        
                        # Wait for the next page to load
                        time.sleep(3)
                        
                        # Take a screenshot of the download page
                        download_screenshot_path = os.path.join(OUTPUT_DIR, f"download_page_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png")
                        self.driver.save_screenshot(download_screenshot_path)
                        logging.info(f"Saved download page screenshot to {download_screenshot_path}")
                        
                        # Look for download links on this page
                        download_page_links = self.driver.find_elements(By.XPATH, "//a[contains(@href, '.pdf') or contains(@href, 'download')]")
                        if download_page_links:
                            pdf_url = download_page_links[0].get_attribute('href')
                            logging.info(f"Found download URL on next page: {pdf_url}")
                            return pdf_url
                    except Exception as e:
                        logging.error(f"Error clicking download button: {str(e)}")
                
                # Method 3: Look for iframe or object tags that might contain PDFs
                try:
                    iframes = self.driver.find_elements(By.TAG_NAME, "iframe")
                    for iframe in iframes:
                        src = iframe.get_attribute('src')
                        if src and ('.pdf' in src.lower() or 'download' in src.lower()):
                            logging.info(f"Found PDF in iframe: {src}")
                            return src
                except Exception as e:
                    logging.warning(f"Error checking iframes: {str(e)}")
                
                # If we still don't have a download URL, try to find any link that might be relevant
                all_links = self.driver.find_elements(By.TAG_NAME, "a")
                for link in all_links:
                    try:
                        href = link.get_attribute('href')
                        text = link.text
                        if href and ('download' in href.lower() or 'tender' in href.lower() or 'document' in href.lower()):
                            logging.info(f"Found potential relevant link: {href} with text: {text}")
                            # Try clicking this link
                            link.click()
                            time.sleep(3)
                            
                            # Check if we're now on a page with download links
                            current_url = self.driver.current_url
                            logging.info(f"Navigated to: {current_url}")
                            
                            # Take a screenshot
                            nav_screenshot_path = os.path.join(OUTPUT_DIR, f"navigation_page_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png")
                            self.driver.save_screenshot(nav_screenshot_path)
                            
                            # Look for download links on this page
                            nav_download_links = self.driver.find_elements(By.XPATH, "//a[contains(@href, '.pdf') or contains(@href, 'download')]")
                            if nav_download_links:
                                pdf_url = nav_download_links[0].get_attribute('href')
                                logging.info(f"Found download URL after navigation: {pdf_url}")
                                return pdf_url
                            
                            # Go back to try another link
                            self.driver.back()
                            time.sleep(2)
                    except Exception as e:
                        logging.warning(f"Error with link navigation: {str(e)}")
                        # Try to go back to the original page
                        try:
                            self.driver.get(document_url)
                            time.sleep(2)
                        except:
                            pass
                
                logging.warning(f"Could not find download URL after trying multiple methods")
                return None
                
            except Exception as e:
                logging.error(f"Error extracting details from document URL: {document_url}, error: {str(e)}")
                if attempt < MAX_RETRIES - 1:
                    time.sleep(2)  # Wait before retrying
                    continue
                return None
                
        return None
            
    def _extract_pdf_url(self, soup, document_url):
        """
        Extract PDF download URL from a document page using multiple methods
        """
        pdf_url = None
        
        # Method 1: Look for direct PDF links
        pdf_links = soup.find_all('a', href=lambda href: href and href.lower().endswith('.pdf'))
        if pdf_links:
            pdf_url = urljoin(document_url, pdf_links[0]['href'])
            return pdf_url
        
        # Method 2: Look for download buttons/links with PDF text
        download_links = soup.find_all('a', string=lambda t: t and ('download' in t.lower() or 'pdf' in t.lower()))
        if download_links:
            for link in download_links:
                if 'href' in link.attrs:
                    pdf_url = urljoin(document_url, link['href'])
                    return pdf_url
        
        # Method 3: Look for links with download or pdf in the href
        href_links = soup.find_all('a', href=lambda href: href and ('download' in href.lower() or 'pdf' in href.lower()))
        if href_links:
            for link in href_links:
                pdf_url = urljoin(document_url, link['href'])
                return pdf_url
        
        # Method 4: Look for iframe sources that might be PDFs
        iframes = soup.find_all('iframe', src=lambda src: src and '.pdf' in src.lower())
        if iframes:
            pdf_url = urljoin(document_url, iframes[0]['src'])
            return pdf_url
        
        # Method 5: Look for object tags with PDF data
        objects = soup.find_all('object', data=lambda data: data and data.lower().endswith('.pdf'))
        if objects:
            pdf_url = urljoin(document_url, objects[0]['data'])
            return pdf_url
        
        # Method 6: Look for any link with common document extensions
        doc_extensions = ['.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx', '.pdf', '.zip', '.rar']
        for ext in doc_extensions:
            links = soup.find_all('a', href=lambda href: href and href.lower().endswith(ext))
            if links:
                pdf_url = urljoin(document_url, links[0]['href'])
                return pdf_url
        
        return pdf_url

    def save_tender_data(self, tender_data, filename='sbi_tender_data.json'):
        """Save tender data to JSON file"""
        # Use absolute path for output file
        output_path = os.path.abspath(os.path.join(OUTPUT_DIR, filename))
        logging.info(f"Saving tender data to: {output_path}")
        
        try:
            # Save the data
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(tender_data, f, indent=2)
            logging.info(f"Successfully saved tender data to: {output_path}")
            return output_path
        except Exception as e:
            logging.error(f"ERROR saving tender data: {str(e)}")
            return None

    def crawl(self, keyword="ai ml"):
        """
        Crawl the SBI portal for the specified keyword
        Returns results with document details
        """
        try:
            # Create a unique run ID for this crawl session
            run_id = datetime.now().strftime("%Y%m%d_%H%M%S")
            logging.info(f"Starting crawl session with ID: {run_id}")
            
            # Access homepage
            if not self.access_homepage():
                logging.error("Failed to access homepage. Aborting.")
                return []
            
            # Search for the keyword
            search_html = self.search_keyword(keyword)
            if not search_html:
                logging.error(f"Failed to search for keyword: {keyword}")
                return []
            
            # Extract tenders
            tenders = self.extract_tenders(search_html)
            logging.info(f"Found {len(tenders)} tenders for keyword '{keyword}'")
            
            if not tenders:
                logging.warning("No tenders found. Check if the site structure has changed.")
                return []
            
            # Process each tender to extract document details
            logging.info("\nExtracting document details from each tender...")
            for i, tender in enumerate(tenders):
                logging.info(f"Processing tender {i+1}/{len(tenders)}: {tender.get('title', 'Untitled')}")
                if tender.get('document_url'):
                    pdf_url = self.extract_document_details(tender['document_url'])
                    if pdf_url:
                        tender['pdf_download_url'] = pdf_url
                        logging.info(f"Added pdf_download_url: {pdf_url}")
                else:
                    logging.warning(f"No document_url found for tender: {tender.get('title', 'Untitled')}")
                
                # Add search keyword to the tender
                tender['search_keyword'] = keyword
            
            # Add timestamp metadata
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            result = {
                "metadata": {
                    "run_id": run_id,
                    "keyword": keyword,
                    "timestamp": timestamp,
                    "total_tenders_found": len(tenders)
                },
                "tenders": tenders
            }
            
            # Save results
            output_filename = f"sbi_tenders_{run_id}.json"
            output_path = self.save_tender_data(result, output_filename)
            
            logging.info("\n=== Crawl Summary ===")
            logging.info(f"Keyword searched: {keyword}")
            logging.info(f"Total tenders found: {len(tenders)}")
            logging.info(f"Tenders with PDF download URL: {sum(1 for t in tenders if 'pdf_download_url' in t)}")
            logging.info(f"Final results saved to: {output_path}")
            
            return tenders
            
        except Exception as e:
            logging.error(f"\nERROR in crawl: {str(e)}")
            import traceback
            traceback.print_exc()
            
            # Try to take a screenshot of the error state
            try:
                error_screenshot_path = os.path.join(OUTPUT_DIR, f"error_state_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png")
                self.driver.save_screenshot(error_screenshot_path)
                logging.info(f"Saved error state screenshot to {error_screenshot_path}")
            except:
                pass
            
            return []
        finally:
            # Always close the driver
            self.close_driver()

    def crawl_keywords(self, keywords=None):
        """
        Crawl the SBI portal for a list of keywords
        Returns consolidated results with document details
        """
        if keywords is None:
            keywords = ["ai ml"]
        
        try:
            # Create a unique run ID for this crawl session
            run_id = datetime.now().strftime("%Y%m%d_%H%M%S")
            logging.info(f"Starting multi-keyword crawl session with ID: {run_id}")
            
            # Access homepage once
            if not self.access_homepage():
                logging.error("Failed to access homepage. Aborting.")
                return []
            
            all_tenders = []
            keyword_results = {}
            
            # Process each keyword
            for i, keyword in enumerate(keywords):
                logging.info(f"\n=== Processing keyword {i+1}/{len(keywords)}: '{keyword}' ===\n")
                
                # Try the keyword search up to 3 times if it fails
                max_attempts = 3
                search_html = None
                
                for attempt in range(1, max_attempts + 1):
                    if attempt > 1:
                        logging.info(f"Retrying keyword '{keyword}' (attempt {attempt}/{max_attempts})")
                        # Make sure we're on the homepage for a fresh attempt
                        self.access_homepage()
                    
                    # Search for the keyword
                    search_html = self.search_keyword(keyword)
                    if search_html:
                        break
                
                # Extract tenders
                if search_html:
                    keyword_tenders = self.extract_tenders(search_html)
                    logging.info(f"Found {len(keyword_tenders)} tenders for keyword '{keyword}'")
                    
                    # Process each tender to extract document details
                    if keyword_tenders:
                        logging.info("\nExtracting document details from each tender...")
                        for j, tender in enumerate(keyword_tenders):
                            logging.info(f"Processing tender {j+1}/{len(keyword_tenders)}: {tender.get('title', 'Untitled')}")
                            if tender.get('document_url'):
                                pdf_url = self.extract_document_details(tender['document_url'])
                                if pdf_url:
                                    tender['pdf_download_url'] = pdf_url
                                    logging.info(f"Added pdf_download_url: {pdf_url}")
                            else:
                                logging.warning(f"No document_url found for tender: {tender.get('title', 'Untitled')}")
                            
                            # Add search keyword to the tender
                            tender['search_keyword'] = keyword
                    
                    all_tenders.extend(keyword_tenders)
                    keyword_results[keyword] = len(keyword_tenders)
                else:
                    logging.warning(f"No search results HTML for keyword '{keyword}'")
                    keyword_results[keyword] = 0
                
                # Go back to homepage for next keyword
                if i < len(keywords) - 1:  # If not the last keyword
                    logging.info(f"Returning to homepage for next keyword")
                    self.access_homepage()
            
            if not all_tenders:
                logging.warning("No tenders found for any of the keywords. Check if the site structure has changed.")
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
            output_filename = f"sbi_tenders_{run_id}.json"
            output_path = self.save_tender_data(result, output_filename)
            
            logging.info("\n=== Crawl Summary ===")
            logging.info(f"Keywords searched: {', '.join(keywords)}")
            logging.info(f"Total tenders found: {len(all_tenders)}")
            logging.info(f"Results by keyword:")
            for kw, count in keyword_results.items():
                logging.info(f"  - '{kw}': {count} tenders")
            logging.info(f"Tenders with PDF download URL: {sum(1 for t in all_tenders if 'pdf_download_url' in t)}")
            logging.info(f"Final results saved to: {output_path}")
            
            return all_tenders
            
        except Exception as e:
            logging.error(f"\nERROR in crawl_keywords: {str(e)}")
            import traceback
            traceback.print_exc()
            
            # Try to take a screenshot of the error state
            try:
                error_screenshot_path = os.path.join(OUTPUT_DIR, f"error_state_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png")
                self.driver.save_screenshot(error_screenshot_path)
                logging.info(f"Saved error state screenshot to {error_screenshot_path}")
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
    # keywords = ["ai ml", "artificial intelligence", "machine learning"]
    # keywords = ["DLP","Digital Lending Platform","Digital Lending","Colending","Co-Lending","CLM-1","CLM-2","Convertable loan agreement","AI","Artificial Intelligence","AI ML","AI and ML","AI and Machine Learning","Generative AI","GenAI","Voice Bots","Personalised Videos","Document Parsing","OCR"]
    logging.info(f"Starting SBI Portal crawler with keywords: {keywords}")
    crawler = SBICrawler(headless=True)
    tenders = crawler.crawl_keywords(keywords)
    logging.info(f"Crawler completed. Found {len(tenders)} tenders")
    
    # Filter tenders based on keywords and extract only required fields
    filtered_tenders = []
    for tender in tenders:

        # Create a simplified tender object with only the required fields
        simplified_tender = {
            'title': tender.get('title', ''),
            'document_url': tender.get('pdf_download_url', ''),
            'corrigendum': tender.get('corrigendum', 0),
            'rpf_id' : tender.get('event_id','')
        }
        filtered_tenders.append(simplified_tender)
    
    # Save the filtered results
    output_filename = f"sbi_filtered_tenders.json"
    output_path = os.path.join(OUTPUT_DIR, output_filename)
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(filtered_tenders, f, indent=2)
    
    logging.info(f"Filtered {len(filtered_tenders)} tenders out of {len(tenders)} total tenders")
    logging.info(f"Filtered results saved to: {output_path}")
    
    return filtered_tenders

if __name__ == "__main__":
    input_keywords = ["ai ml"]
    main(input_keywords)
