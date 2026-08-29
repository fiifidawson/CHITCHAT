import time
import random
import requests
from bs4 import BeautifulSoup
from urllib.parse import quote_plus, urljoin, urlparse, urlencode
from scholarly import scholarly
import json
import requests
import fitz  # PyMuPDF
import tempfile
import os
import io
from PyPDF2 import PdfReader
from PyPDF2.errors import PdfReadError
import re
import requests
import time




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
            print(f"successfully downloaded research paper from the following {url}")
            return file_path
        
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
            return None
        
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
    
    except Exception as e:
        return None
    

def _rebuild_abstract(inv_index: dict[str, list[int]]) -> str:
    # 1. Find total number of tokens
    max_pos = max(pos for positions in inv_index.values() for pos in positions)
    tokens = [''] * (max_pos + 1)

    # 2. Fill in each token at its recorded positions
    for token, positions in inv_index.items():
        for pos in positions:
            tokens[pos] = token

    # 3. Join back into a string (this gives a space-separated approximation)
    return ' '.join(tokens)

def search_openalex(
    query: str,
    per_page: int = 200,
    max_pages: int | None = None,
    sleep_between: float = 1.0
) -> list[dict]:
    """
    Perform a Boolean-style search on OpenAlex and return all matching works.

    Parameters:
        query (str): A free-text Boolean query (e.g. "heart AND attack NOT stroke").
        per_page (int): Number of results per request (max 200).
        max_pages (int|None): Stop after this many pages; None = no limit.
        sleep_between (float): Seconds to pause between requests.

    Returns:
        List[dict]: Each dict is one work record from OpenAlex's /works endpoint.
    """
    base_url = "https://api.openalex.org/works"
    cursor = "*"
    all_works = []
    page_count = 0

    while True:
        params = {
            "search": query,
            "per_page": per_page,
            "cursor": cursor,
        }
        resp = requests.get(base_url, params=params)
        resp.raise_for_status()
        payload = resp.json()

        works = payload.get("results", [])
        all_works.extend(works)

        page_count += 1
        # Stop if we've hit the user-defined page limit
        if max_pages is not None and page_count >= max_pages:
            break

        # Grab next cursor for pagination
        next_cursor = payload.get("meta", {}).get("next_cursor")
        if not next_cursor:
            break

        cursor = next_cursor
        time.sleep(sleep_between)
    

    #extract all of the needed information from the obtained works
    processed_works = []
    for work_item in all_works:
        #get the paper title
        paper_title = work_item['title']

        #get the authors in a comma separated fashion
        author_info = work_item['authorships']
        authorship_list = []
        for author_item in author_info:
            authorship_list.append(author_item['author']['display_name'])
        authors = ','.join(authorship_list)

        #get the best open access location url
        url = work_item['primary_location']['landing_page_url']
        pdf_url = work_item['primary_location']['pdf_url']

        #get the publication year
        year = work_item['publication_year']

        if pdf_url is not None:
            #extract the text from the pdf of the paper
            downloaded_paper_path = download_research_paper(pdf_url)
            if downloaded_paper_path is not None:
                try:
                    paper_text = extract_paper_text(downloaded_paper_path)
                except Exception as e:
                    print(f"Could not extract the text from {pdf_url} even though it was downloaded. It is probably behind a paywall.")
                    paper_text = None
            else:
                paper_text = None
        else:
            paper_text = None
        
        #check to see if abstract_inverted_index is not None
        if work_item['abstract_inverted_index'] is not None:
            abstract = _rebuild_abstract(work_item['abstract_inverted_index'])
        else:
            abstract = None
        
        #append all of the extracted items to processed_works
        processed_works.append({
                                    'title':paper_title,
                                    'authors': authors,
                                    'url': url,
                                    'abstract': abstract,
                                    'year': year,
                                    'extracted_text': paper_text
                                })
    return processed_works



def search_europepmc(
    query: str,
    result_type: str = 'core',
    page_size: int = 1000,
    max_pages: int | None = None,
    pause: float = 1.0
) -> list[dict]:
    """
    Perform a Boolean-style search on Europe PMC and return all matching records.

    Parameters:
        query (str): Boolean query string (e.g. "stroke AND (trevo OR solitaire)").
        result_type (str): Level of detail ('lite' or 'core'); 'core' returns abstracts.  
        page_size (int): Number of records per page (max 1000).  
        max_pages (Optional[int]): Maximum number of pages to fetch; None = no limit.  
        pause (float): Seconds to wait between requests to avoid rate limits.  

    Returns:
        List[Dict]: List of JSON objects, each representing one Europe PMC record.
    """
    base_url = 'https://www.ebi.ac.uk/europepmc/webservices/rest/search'
    cursor = '*'
    all_records: list[dict] = []
    page_count = 0

    while True:
        params = {
            'query': query,
            'resultType': result_type,
            'cursorMark': cursor,
            'pageSize': page_size,
            'format': 'json'
        }
        resp = requests.get(base_url, params=params)
        resp.raise_for_status()
        payload = resp.json()

        # Extract result list
        results = payload.get('resultList', {}).get('result', [])
        all_records.extend(results)

        page_count += 1
        # Respect max_pages
        if max_pages is not None and page_count >= max_pages:
            break

        # Get next cursor; break if absent or unchanged
        next_cursor = payload.get('nextCursorMark')
        if not next_cursor or next_cursor == cursor:
            break
        cursor = next_cursor

        time.sleep(pause)
    

    #extract the information from the obtained records and then pre-process it to re-arrange the structure
    #title, authors, url, abstract, year and extracted text
    processed_records = []
    for record in all_records:
        #extract the title of the current record
        title = record.get('title', 'N/A')

        #extract the authors of the current record - with error handling
        author_list = record.get('authorString', 'N/A')

        #extract the url for the paper - with error handling
        try:
            url = record['fullTextUrlList']['fullTextUrl'][0]['url']
        except (KeyError, IndexError, TypeError):
            print(f"No URL available for paper: {title}")
            url = None

        #extract the abstract
        try:
            abstract = record['abstractText']
        except KeyError:
            print(f"Abstract information does not exist for the following paper {title}")
            abstract = None
    
        try:
            #extract the publication year
            record_keys = record.keys()
            if 'journalInfo' in record_keys:
                year = record['journalInfo']['yearOfPublication']
            else:
                year = record['bookOrReportDetails']['yearOfPublication']
        except KeyError:
            print(f"Year information not available for paper: {title}")
            year = None

        #extract the text of the paper
        if url is not None:
            downloaded_paper_path = download_research_paper(url)
            if downloaded_paper_path is not None:
                try:
                    extracted_text = extract_paper_text(downloaded_paper_path)
                except Exception as e:
                    print(f"Could not extract the text from {url} even though it was downloaded. It is probably behind a paywall.")
                    extracted_text = None
            else:
                extracted_text = None
        else:
            extracted_text = None
        
        processed_records.append({
            'title': title,
            'authors': author_list,
            'url': url,
            'abstract': abstract,
            'year': year,
            'extracted_text': extracted_text
        })
                
    return processed_records


def extract_paper_text(research_paper_path: str) -> str:
    """
    Extracts and returns all of the text in the provided research paper.

    Params:
        research_paper_path (str): Path to the downloaded research paper.

    Returns:
        extracted_text (str): Extracted text from the research paper.
    """
    if not os.path.exists(research_paper_path):
        raise FileNotFoundError(f"File not found: {research_paper_path}")

    # Read raw bytes
    with open(research_paper_path, "rb") as f:
        data = f.read()

    # Quick sanity check: must start with "%PDF-"
    if not data.startswith(b"%PDF-"):
        raise ValueError(f"Not a valid PDF (missing %PDF- header): {research_paper_path}")

    # Pad EOF marker if missing
    if b"%%EOF" not in data[-20:]:
        data += b"\n%%EOF\n"

    # Wrap in BytesIO so we can pass strict=False
    buf = io.BytesIO(data)

    try:
        reader = PdfReader(buf, strict=False)
    except PdfReadError as e:
        raise RuntimeError(f"Failed to parse PDF: {e}") from e

    # Extract text
    pages = []
    for page in reader.pages:
        text = page.extract_text()
        if text:
            pages.append(text)

    return "\n".join(pages)



def search_google_scholar_scholarly(query: str, max_results: int | None = None , pub_year: int = 2020, num_citations: int = 0):
    """Uses scholarly library for Google Scholar."""
    print(f"🚀 Searching Google Scholar for '{query}'...")
    try:
        search_gen = scholarly.search_pubs(query)
        results = []
        for i, paper in enumerate(search_gen):
            if max_results is not None and i >= max_results:
                break

            bib = paper.get('bib', {})
            #check that the pub year of paper >= pub_year and num_citations >= 1
            paper_pub_year = int(bib.get('pub_year', 0))
            paper_citations = int(paper.get('num_citations', 0))
            downloaded_paper_file_path = download_research_paper(paper.get('pub_url', 'N/A'))


            if downloaded_paper_file_path is not None:
                paper_text = extract_paper_text(downloaded_paper_file_path)
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

def get_arxiv_results(path_to_unique_boolean_combinations):
    """
    Get arXiv search results and return them in the same format as other repositories
    
    Args:
        path_to_unique_boolean_combinations (str): Path to unique boolean combinations JSON
    
    Returns:
        List[dict]: Papers found by arXiv search, ready to be added to total_results
    """
    try:
        # Import your existing arXiv search function
        from legacy.src.api.arxiv_paper_search import search_arxiv_papers
        import json
        import os
        
        print("Starting arXiv search...")
        
        # Call your existing arXiv search function
        # Use a temporary file to avoid conflicts
        temp_arxiv_file = 'temp_arxiv_results.json'
        success = search_arxiv_papers(
            unique_combinations_file=path_to_unique_boolean_combinations,
            output_file=temp_arxiv_file
        )
        
        if success and os.path.exists(temp_arxiv_file):
            # Read the results
            with open(temp_arxiv_file, 'r') as f:
                arxiv_papers = json.load(f)
            
            # Clean up temporary file
            os.remove(temp_arxiv_file)
            
            print(f"✓ ArXiv search completed - found {len(arxiv_papers)} papers")
            return arxiv_papers
        else:
            print("✗ ArXiv search failed or no results found")
            return []
            
    except ImportError as e:
        print(f"✗ Could not import arXiv search module: {e}")
        print("Make sure arxiv_paper_search.py is in the same directory")
        return []
    except Exception as e:
        print(f"✗ Error during arXiv search: {e}")
        return []




def search_repository(query: str, repo: str):
    """
    Search across multiple pages for a boolean query on a given repository.
    """
    repo = repo.lower()
    if repo == 'google_scholar':
        return search_google_scholar_scholarly(query)

    elif repo == 'openalex':
        return search_openalex(query)
    
    else:
        return search_europepmc(query)

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
    output_json_filename = '../../output/obtained_lit.json'

    #iterate through the unique combinations in each topic section and call a search
    #using these combinations
    with open(path_to_unique_boolean_combinations, 'r') as input_json:
        json_contents = json.load(input_json)
        for i, topic_section in enumerate(json_contents):
            
            if i <= 1: # Restart from a certain point
                continue
            
            unique_combinations = topic_section['boolean_combination']
            
            ###############place calls to specialized functions written for literature search here###############
            print("Starting to scrape google scholar...")
            google_scholar_results = search_repository(unique_combinations, "google_scholar")
            append_results_to_json(output_json_filename, google_scholar_results, "Google Scholar")
            
            print("Starting to scrape openalex...")
            # openalex_results = search_repository(unique_combinations, "openalex")
            # append_results_to_json(output_json_filename, openalex_results, "OpenAlex")
            
            print("Starting to scrape europepmc...")
            europepmc_results = search_repository(unique_combinations, "europepmc")
            append_results_to_json(output_json_filename, europepmc_results, "Europe PMC")

        # ArXiv Integration
        print("Starting to scrape arxiv...")
        arxiv_results = get_arxiv_results(path_to_unique_boolean_combinations)
        append_results_to_json(output_json_filename, arxiv_results, "ArXiv")
        
    return output_json_filename


def append_results_to_json(output_json_filename, new_results, source_name):
    """
    Append new results to the JSON file. Creates file if it doesn't exist.
    
    Args:
        output_json_filename (str): Path to the JSON file
        new_results (list): List of new papers to append
        source_name (str): Name of the source (for logging)
    """
    if not new_results:
        print(f"No results from {source_name} to append")
        return
    
    import os
    
    # Create output directory if it doesn't exist
    os.makedirs(os.path.dirname(output_json_filename), exist_ok=True)
    
    try:
        # Try to read existing data, create empty list if file doesn't exist
        if os.path.exists(output_json_filename):
            with open(output_json_filename, 'r') as f:
                existing_data = json.load(f)
        else:
            existing_data = []
            print(f"Created new file: {output_json_filename}")
        
        # Append new results
        existing_data.extend(new_results)
        
        # Write back to file
        with open(output_json_filename, 'w') as f:
            json.dump(existing_data, f, indent=4)
        
        print(f"✓ Appended {len(new_results)} results from {source_name}. Total papers: {len(existing_data)}")
        
    except Exception as e:
        print(f"✗ Error appending results from {source_name}: {e}")



if __name__ == "__main__":
    import sys
    json_path = sys.argv[1]
    output = get_llit_papers(json_path)
    print(f"Results written to {output}")
