import time
import random
import requests
from bs4 import BeautifulSoup
from urllib.parse import quote_plus, urljoin

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


def search_repository(query: str, repo: str, max_pages: int = 2):
    """
    Search across multiple pages for a boolean query on a given repository.
    """
    repo = repo.lower()
    if repo == 'google_scholar':
        return _search_google_scholar_scholarly(query, max_pages * 10)

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

def _search_google_scholar_scholarly(query: str, max_results: int):
    """Uses scholarly library for Google Scholar."""
    print(f"🚀 Searching Google Scholar for '{query}'...")
    results = []
    try:
        search_gen = scholarly.search_pubs(query)
        for i, paper in enumerate(search_gen):
            if i >= max_results:
                break
            bib = paper.get('bib', {})
            results.append({
                'title': bib.get('title', 'N/A'),
                'authors': ", ".join(bib.get('author', [])),
                'url': paper.get('pub_url', 'N/A')
            })
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


if __name__ == '__main__':
    # --- Example Usage ---
    google_scholar_results = search_repository("Humanitarian AND AI", "google_scholar")
    print("\n--- GOOGLE SCHOLAR RESULTS ---")
    if google_scholar_results:
        for paper in google_scholar_results:
            print(f"Title: {paper['title']}\nAuthors: {paper['authors']}\nURL: {paper['url']}\n")
        
    
    '''
    # 1. Search JAMA
    jama_results = search_repository("cardiovascular health", "jama", max_pages=1)
    print("\n--- JAMA Results ---")
    if jama_results:
        for paper in jama_results:
            print(f"Title: {paper['title']}\nAuthors: {paper['authors']}\nURL: {paper['url']}\n")
    else:
        print("No results found for JAMA.")

    print("\n" + "="*50 + "\n")

    # 2. Search UN
    un_results = search_repository("epidemic AND modeling", "un", max_pages=1)
    print("\n--- UN Results ---")
    if un_results:
        for paper in un_results:
            print(f"Title: {paper['title']}\nURL: {paper['url']}\n")
    else:
        print("No results found for UN.")

    print("\n" + "="*50 + "\n")

    # 3. Search WHO
    who_results = search_repository("zika virus AND prevention", "who", max_pages=1)
    print("\n--- WHO Results ---")
    if who_results:
        for paper in who_results:
            print(f"Title: {paper['title']}\nAuthors: {paper['authors']}\nURL: {paper['url']}\n")
    else:
        print("No results found for WHO.")

    '''
    
