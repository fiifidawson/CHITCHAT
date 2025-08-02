import time
import random
import requests
from bs4 import BeautifulSoup
from urllib.parse import quote_plus, urljoin, urlparse
import json
import requests
import fitz  # PyMuPDF
import tempfile
import os
from PyPDF2 import PdfReader
import re

# --- Selenium Imports ---
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException

# Scholarly integration for Google Scholar
try:
    from scholarly import scholarly
except ImportError:
    raise ImportError("Please install the scholarly package: pip install scholarly")

# --- WebDriver Setup for Safari ---
def get_selenium_driver():
    """
    Initializes and returns a Selenium WebDriver for Safari.
    
    IMPORTANT: Before running, you must enable remote automation in Safari.
    1. Open Safari.
    2. Go to Safari > Settings > Advanced.
    3. Check the box for "Show features for web developers".
    4. A new "Develop" menu will appear in the menu bar.
    5. Click "Develop" and ensure "Allow Remote Automation" is checked.
    """
    driver = webdriver.Safari()
    return driver

# --- Helper function to handle cookie banners ---
def _handle_cookie_banner(driver):
    """
    Tries to find and click common cookie consent buttons, including modal close buttons.
    """
    selectors = [
        "//button[@aria-label='Close']",
        "//a[@aria-label='Close']",
        "//button[contains(@class, 'close')]",
        "//button[contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'accept')]",
        "//button[contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'agree')]",
        "//button[contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'i understand')]",
        "//button[@id='CybotCookiebotDialogBodyLevelButtonLevelOptinAllowAll']"
    ]
    
    for selector in selectors:
        try:
            wait = WebDriverWait(driver, 5)
            button = wait.until(EC.element_to_be_clickable((By.XPATH, selector)))
            button.click()
            print(f"   - Handled banner with selector: {selector}")
            # The more robust wait will happen in the specific scraper function
            return True # Indicate that a banner was handled
        except (TimeoutException, NoSuchElementException):
            continue
    print("   - No cookie banner found or handled.")
    return False


def search_repository(query: str, repo: str, max_pages: int = 1, pub_year: int = 2020, num_citations: int = 1):
    """
    Search across multiple pages for a boolean query on a given repository.
    """
    repo = repo.lower()
    if repo == 'google_scholar':
        return _search_google_scholar_scholarly(query, max_pages * 10, pub_year, num_citations)

    search_map = {
        'iscram': _search_iscram,
        'icrc': _search_icrc,
        'jama': _search_jama,
        'un': _search_un,
        'who': _search_who
    }
    if repo not in search_map:
        raise ValueError(f"Unsupported repository: {repo}")
    
    print(f"🚀 Searching {repo.upper()} for '{query}'...")
    return _paginate_with_selenium(search_map[repo], query, max_pages)


import os
import requests
from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup

def download_research_paper(url, save_dir="research_paper_downloads"):
    """
    Downloads a research paper from the given URL.
    Works generically for many publishers by checking for PDF links in HTML.
    
    Args:
        url (str): URL to the research paper page or PDF.
        save_dir (str): Directory to save the paper.
        
    Returns:
        str: Path to the downloaded file or error message.
    """
    try:
        os.makedirs(save_dir, exist_ok=True)
        headers = {"User-Agent": "Mozilla/5.0"}
        
        # 1. Try direct download first
        resp = requests.get(url, headers=headers, stream=True)
        resp.raise_for_status()
        content_type = resp.headers.get('Content-Type', '').lower()
        
        if 'pdf' in content_type or url.lower().endswith(".pdf"):
            print(f'found the pdf link in the content type and initiating download process ... {url}')
            # Direct PDF
            filename = os.path.basename(urlparse(url).path)
            if not filename.endswith(".pdf"):
                filename += ".pdf"
            file_path = os.path.join(save_dir, filename)
            with open(file_path, "wb") as f:
                for chunk in resp.iter_content(chunk_size=8192):
                    f.write(chunk)
            return f"Downloaded PDF to: {file_path}"
        
        # 2. Not a direct PDF → parse HTML to find a PDF link
        html = resp.text
        soup = BeautifulSoup(html, "html.parser")
        pdf_link = None
        for a in soup.find_all("a", href=True):
            href = a["href"]
            if href.lower().endswith(".pdf") or "/pdf" in href.lower() or "/epdf" in href.lower():
                print(f'found pdf link using beautifulsoup and now proceeding to download the paper...{url}')
                pdf_link = urljoin(url, href)
                break
        
        if not pdf_link:
            print(f'No PDF link found on this page...{url}')
            return "No PDF link found on this page."
        
        # 3. Download the found PDF link
        pdf_resp = requests.get(pdf_link, headers=headers, stream=True)
        pdf_resp.raise_for_status()
        
        filename = os.path.basename(urlparse(pdf_link).path)
        if not filename.endswith(".pdf"):
            filename += ".pdf"
        file_path = os.path.join(save_dir, filename)
        
        with open(file_path, "wb") as f:
            for chunk in pdf_resp.iter_content(chunk_size=8192):
                f.write(chunk)
        
        return file_path
    
    except requests.exceptions.RequestException as e:
        return f"Error: {e}"
    

def _extract_paper_text(research_paper_path):
    '''
    Extracts and returns all of the text in the provided research paper.

    Params:
        research_paper_path (str): Path to the downloaded research paper.

    Returns:
        extracted_text (str): Extracted text from the research paper.
    '''
    text = []
    #check to see if the provided path exists
    if not os.path.exists(research_paper_path):
        raise FileNotFoundError(f'the research paper in path {research_paper_path} does not exist.')
    
    #open the file and extract the text from the pdf
    with open(research_paper_path, 'rb') as f:
        reader = PdfReader(f)
        for page in reader.pages:
            page_text = page.extract_text()
            if page_text:
                text.append(page_text)
    
    extracted_text = "\n".join(text)
    return extracted_text
    


def _search_google_scholar_scholarly(query: str, max_results: int, pub_year: int, num_citations: int):
    """Uses scholarly library for Google Scholar."""
    print(f"🚀 Searching Google Scholar for '{query}'...")
    try:
        search_gen = scholarly.search_pubs(query)
        results = []
        for i, paper in enumerate(search_gen):
            if i >= max_results:
                break

            bib = paper.get('bib', {})
            #check that the pub year of paper >= pub_year and num_citations >= 1
            paper_pub_year = int(bib.get('pub_year', 0))
            paper_citations = int(paper.get('num_citations', 0))
            downloaded_paper_file_path = download_research_paper(paper.get('pub_url', 'N/A'))


            if 'Error' not in downloaded_paper_file_path:
                paper_text = _extract_paper_text(downloaded_paper_file_path)
                if paper_pub_year >= pub_year and paper_citations >= num_citations:
                    results.append({
                        'title': bib.get('title', 'N/A'),
                        'authors': ", ".join(bib.get('author', [])),
                        'url': paper.get('pub_url', 'N/A'),
                        'abstract': bib.get('abstract', 'N/A'),
                        'year': paper_pub_year,
                        'extracted_text': paper_text
                    })
            else:
                continue            
    except Exception as e:
        print(f"An error occurred with scholarly: {e}")
    return results

def _paginate_with_selenium(search_fn, query: str, max_pages: int):
    """
    Pagination handler that uses a single Selenium driver instance.
    """
    driver = get_selenium_driver()
    all_results = []
    try:
        for page in range(1, max_pages + 1):
            print(f"   - Scraping page {page}...")
            try:
                page_results = search_fn(driver, query, page)
                if not page_results:
                    print("   - No more results found on this page. Stopping.")
                    break
                all_results.extend(page_results)
                
                if page < max_pages:
                    time.sleep(random.uniform(5, 10)) 
                    
            except TimeoutException as e:
                # Provide a more detailed error message
                print(f"   - Loading timed out on page {page}. The specific element was not found in time. This could be due to a slow network, a change in the website's layout, or an intermittent issue.")
                print(f"   - Error details: {e}")
                break
            except Exception as e:
                print(f"   - An error occurred on page {page}: {e}. Stopping.")
                break
    finally:
        driver.quit()
    return all_results

# --- Scraper Functions ---

# --- UPDATED: _search_jama with smarter waiting ---
def _search_jama(driver, query: str, page: int = 1):
    """Uses Selenium with robust cookie handling and explicit waits."""
    base_url = 'https://jamanetwork.com/searchresults'
    params = {'q': query, 'page': page}
    url = f"{base_url}?{requests.compat.urlencode(params)}"
    driver.get(url)
    
    # Try to handle the banner
    banner_was_handled = _handle_cookie_banner(driver)
    
    # Explicitly wait for the banner modal to disappear if it was clicked
    if banner_was_handled:
        try:
            modal_selector = (By.CLASS_NAME, "modal-content")
            wait = WebDriverWait(driver, 10)
            wait.until(EC.invisibility_of_element_located(modal_selector))
            print("   - Confirmed cookie modal is gone.")
        except TimeoutException:
            print("   - Cookie modal did not disappear in time. Continuing anyway.")

    # --- FIX: Wait for the main search results CONTAINER to be visible ---
    # This is more reliable than waiting for a single item.
    wait = WebDriverWait(driver, 30)
    try:
        wait.until(EC.visibility_of_element_located((By.ID, "searchResults")))
        print("   - Search results container is visible.")
    except TimeoutException:
        # If the container itself doesn't appear, we can't proceed.
        print("   - The main search results container did not load. The page may have changed or returned no results.")
        return [] # Return empty list

    # A small, final pause to ensure all JS rendering within the container is complete.
    time.sleep(2)
    
    soup = BeautifulSoup(driver.page_source, 'html.parser')
    results = []
    # Now that we know the container is loaded, we can safely look for the items.
    for item in soup.select('div.search-results-item'):
        tag = item.select_one('h3.meta-title a')
        authors_tag = item.select_one('div.meta-author')
        if not tag: continue
        results.append({
            'title': tag.get_text(strip=True),
            'authors': authors_tag.get_text(strip=True) if authors_tag else 'N/A',
            'url': urljoin(base_url, tag['href'])
        })
    
    if not results:
        print("   - Container was found, but no 'search-results-item' elements were located within it.")
        
    return results

def _search_un(driver, query: str, page: int = 1):
    """Uses Selenium with cookie handling."""
    base_url = 'https://digitallibrary.un.org/search'
    params = {'ln': 'en', 'q': query, 'page': page}
    url = f"{base_url}?{requests.compat.urlencode(params)}"
    driver.get(url)

    _handle_cookie_banner(driver)

    wait = WebDriverWait(driver, 30)
    wait.until(EC.visibility_of_element_located((By.CLASS_NAME, "result-body")))

    soup = BeautifulSoup(driver.page_source, 'html.parser')
    results = []
    for item in soup.select('div.result-body'):
        title_tag = item.select_one('a.title-link')
        if not title_tag: continue
        author_tag = item.select_one('div.authors')
        results.append({
            'title': title_tag.get_text(strip=True),
            'authors': author_tag.get_text(strip=True).strip() if author_tag else 'N/A',
            'url': urljoin(base_url, title_tag['href'])
        })
    return results

def _search_who(driver, query: str, page: int = 1):
    """Uses Selenium with cookie handling."""
    base_url = 'https://iris.who.int/search'
    params = {'query': query, 'page': page - 1}
    url = f"{base_url}?{requests.compat.urlencode(params)}"
    driver.get(url)
    
    _handle_cookie_banner(driver)
    
    wait = WebDriverWait(driver, 30)
    wait.until(EC.visibility_of_element_located((By.TAG_NAME, "ds-artifact-browser-list-item")))

    soup = BeautifulSoup(driver.page_source, 'html.parser')
    results = []
    for item in soup.select('ds-artifact-browser-list-item'):
        tag = item.select_one('h4 a')
        authors_tag = item.select_one('p.authors')
        if not tag: continue
        results.append({
            'title': tag.get_text(strip=True), 
            'authors': authors_tag.get_text(strip=True) if authors_tag else 'N/A',
            'url': urljoin(base_url, tag['href'])
        })
    return results

def _search_iscram(driver, query: str, page: int = 1):
    """Uses Selenium with cookie handling."""
    base_url = "https://www.iscram.org/"
    url = f"https://www.iscram.org/search/node/{quote_plus(query)}"
    params = {'page': page - 1}
    full_url = f"{url}?{requests.compat.urlencode(params)}"
    driver.get(full_url)

    _handle_cookie_banner(driver)

    wait = WebDriverWait(driver, 30)
    wait.until(EC.visibility_of_element_located((By.CLASS_NAME, "search-result")))

    soup = BeautifulSoup(driver.page_source, 'html.parser')
    results = []
    for item in soup.select('li.search-result'):
        tag = item.select_one('h3.title a')
        if not tag: continue
        results.append({
            'title': tag.get_text(strip=True),
            'authors': 'N/A on search page',
            'url': urljoin(base_url, tag['href'])
        })
    return results

def _search_icrc(driver, query: str, page: int = 1):
    """Uses Selenium with cookie handling."""
    base_url = 'https://www.icrc.org/en/search/site'
    params = {'keys': query, 'page': page - 1}
    url = f"{base_url}?{requests.compat.urlencode(params)}"
    driver.get(url)

    _handle_cookie_banner(driver)

    wait = WebDriverWait(driver, 30)
    wait.until(EC.visibility_of_element_located((By.CLASS_NAME, "search-result-item")))
    
    soup = BeautifulSoup(driver.page_source, 'html.parser')
    results = []
    for item in soup.select('div.search-result-item'):
        tag = item.select_one('h3 a')
        if not tag: continue
        results.append({
            'title': tag.get_text(strip=True), 
            'authors': 'N/A on search page', 
            'url': urljoin(base_url, tag['href'])
        })
    return results

def get_llit_papers(path_to_unique_boolean_combinations):
    '''
    Searches research paper repositories for the relevant papers using the provided
    boolean search term combinations.

    Params:
        path_to_unique_boolean_combinations (str): Path to file containing the unique boolean
                                                    combinations.
    Output:
        path_to_obtained_lit_json (str): Path to the json file containing the found literature.
    '''
    total_results = []
    output_json_filename = 'obtained_lit.json'

    #iterate through the unique combinations in each topic section and call a search
    #using these combinations
    with open(path_to_unique_boolean_combinations, 'r') as input_json:
        json_contents = json.load(input_json)
        for topic_section in json_contents:
            unique_combinations = topic_section['unique_combinations']
            for unique_combination in unique_combinations:
                ###############place calls to specialized functions written for literature search here###############
                google_scholar_results = search_repository(unique_combinations, "google_scholar")
                
                #append the results from the google scholar search to the total results list
                total_results += google_scholar_results

                
                #FIIFI TO PLACE LITERATURE SEARCH FUNCTIONS HERE (make sure to append your results to total_results as I have done)
                #####################################################################################################
    
    #write the results to the output json file
    with open(output_json_filename, 'w') as output_json:
        json.dump(total_results, output_json, indent=4)
        
    return output_json_filename




    
