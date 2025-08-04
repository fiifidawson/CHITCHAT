import json
import requests
import xml.etree.ElementTree as ET
from typing import List, Dict, Optional
import re
import time
from urllib.parse import quote_plus
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ArxivPaperSearcher:
    """
    Specialized function for searching arXiv papers using boolean combinations
    """
    
    def __init__(self, unique_combinations_file='data/unique_boolean_combinations.json'):
        self.unique_combinations_file = unique_combinations_file
        self.base_url = "http://export.arxiv.org/api/query"
        self.unique_combinations = self._load_unique_combinations()
        
        # Rate limiting - arXiv recommends no more than 1 request per 3 seconds
        self.rate_limit_delay = 3
        
    def _load_unique_combinations(self) -> Optional[List[Dict]]:
        """Load unique boolean combinations from JSON file"""
        try:
            with open(self.unique_combinations_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            logger.error(f"Error: {self.unique_combinations_file} not found.")
            return None
        except json.JSONDecodeError:
            logger.error(f"Error: Invalid JSON format in {self.unique_combinations_file}.")
            return None
    
    def _clean_text(self, text: str) -> str:
        """Clean and normalize text content"""
        if not text:
            return ""
        
        # Remove extra whitespace and normalize
        text = re.sub(r'\s+', ' ', text.strip())
        # Remove newlines and excessive spacing
        text = re.sub(r'\n+', ' ', text)
        return text
    
    def _extract_key_terms_from_boolean(self, boolean_combination: str) -> List[str]:
        """
        Extract key terms from complex boolean combination for simpler arXiv search
        This is a more practical approach given arXiv's search limitations
        """
        # Remove quotes, parentheses, and boolean operators
        cleaned = re.sub(r'["\(\)]', '', boolean_combination)
        cleaned = re.sub(r'\s+(AND|OR)\s+', ' ', cleaned, flags=re.IGNORECASE)
        
        # Split into individual terms and clean
        terms = [term.strip() for term in cleaned.split() if term.strip()]
        
        # Remove duplicates while preserving order and limit to most important terms
        unique_terms = []
        seen = set()
        for term in terms:
            term_lower = term.lower()
            if term_lower not in seen and len(term) > 2:  # Filter very short terms
                unique_terms.append(term)
                seen.add(term_lower)
                if len(unique_terms) >= 10:  # Limit to 10 most important terms
                    break
        
        return unique_terms
    
    def _create_arxiv_queries(self, selected_terms: List[str]) -> List[str]:
        """
        Create multiple arXiv queries based on selected terms
        Uses different search strategies to maximize paper discovery
        """
        queries = []
        
        # Strategy 1: Search for each individual term across all fields
        for term in selected_terms[:3]:  # Limit to first 3 most important terms
            if len(term) > 3:  # Only use substantial terms
                # Clean term for arXiv search
                clean_term = re.sub(r'[^\w\s-]', '', term).strip()
                if clean_term:
                    queries.append(f'all:"{clean_term}"')
        
        # Strategy 2: Combine 2 terms with AND for more specific results
        if len(selected_terms) >= 2:
            term1 = re.sub(r'[^\w\s-]', '', selected_terms[0]).strip()
            term2 = re.sub(r'[^\w\s-]', '', selected_terms[1]).strip()
            if term1 and term2:
                queries.append(f'all:"{term1}" AND all:"{term2}"')
        
        # Strategy 3: Category-specific searches for AI/ML terms
        ai_ml_terms = ['model', 'learning', 'neural', 'deep', 'machine', 'AI', 'artificial']
        for term in selected_terms[:2]:
            clean_term = re.sub(r'[^\w\s-]', '', term).strip().lower()
            if any(ai_term.lower() in clean_term for ai_term in ai_ml_terms):
                queries.append(f'cat:cs.LG OR cat:cs.AI OR cat:stat.ML')
                break
        
        return queries
    
    def _search_arxiv(self, query: str, max_results: int = 30) -> List[Dict]:
        """
        Search arXiv using the API with the given query
        """
        papers = []
        
        try:
            # Encode query for URL
            encoded_query = quote_plus(query)
            
            # Construct API URL
            url = f"{self.base_url}?search_query={encoded_query}&start=0&max_results={max_results}&sortBy=relevance&sortOrder=descending"
            
            logger.info(f"Searching arXiv with query: {query}")
            
            # Make request
            response = requests.get(url, timeout=30)
            response.raise_for_status()
            
            # Parse XML response
            root = ET.fromstring(response.content)
            
            # Define namespaces
            namespaces = {
                'atom': 'http://www.w3.org/2005/Atom',
                'arxiv': 'http://arxiv.org/schemas/atom'
            }
            
            # Extract entries
            entries = root.findall('atom:entry', namespaces)
            
            logger.info(f"Found {len(entries)} entries for query: {query}")
            
            for entry in entries:
                try:
                    # Extract basic information
                    title_elem = entry.find('atom:title', namespaces)
                    title = self._clean_text(title_elem.text) if title_elem is not None else "N/A"
                    
                    # Extract abstract
                    summary_elem = entry.find('atom:summary', namespaces)
                    abstract = self._clean_text(summary_elem.text) if summary_elem is not None else "N/A"
                    
                    # Extract authors
                    authors = []
                    for author in entry.findall('atom:author', namespaces):
                        name_elem = author.find('atom:name', namespaces)
                        if name_elem is not None:
                            authors.append(name_elem.text)
                    
                    authors_str = ', '.join(authors) if authors else "N/A"
                    
                    # Extract publication date/year
                    published_elem = entry.find('atom:published', namespaces)
                    year = "N/A"
                    if published_elem is not None:
                        try:
                            year = published_elem.text[:4]  # Extract year from date
                        except:
                            year = "N/A"
                    
                    # Extract arXiv ID for potential full text extraction
                    arxiv_id = "N/A"
                    id_elem = entry.find('atom:id', namespaces)
                    if id_elem is not None:
                        arxiv_id = id_elem.text.split('/')[-1]  # Extract ID from URL
                    
                    # For now, use abstract as extracted text (full PDF processing would be needed for complete text)
                    extracted_text = abstract
                    
                    paper = {
                        'Title': title,
                        'Year': year,
                        'Authors': authors_str,
                        'Extracted abstract': abstract,
                        'Extracted text without bib and appendix': extracted_text,
                        'ArXiv_ID': arxiv_id,
                        'Search_Query': query  # Track which query found this paper
                    }
                    
                    papers.append(paper)
                    
                except Exception as e:
                    logger.warning(f"Error processing entry: {str(e)}")
                    continue
            
            logger.info(f"Successfully processed {len(papers)} papers")
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Request error: {str(e)}")
        except ET.ParseError as e:
            logger.error(f"XML parsing error: {str(e)}")
        except Exception as e:
            logger.error(f"Unexpected error during search: {str(e)}")
        
        return papers
    
    def search_by_category(self, research_category: str, max_results_per_query: int = 20) -> List[Dict]:
        """
        Search for papers by research category from unique_boolean_combinations.json
        """
        if not self.unique_combinations:
            logger.error("No unique combinations loaded")
            return []
        
        all_papers = []
        seen_papers = set()  # Track by title to avoid duplicates
        
        # Find matching combinations for the research category
        matching_combinations = [
            combo for combo in self.unique_combinations 
            if combo.get('research_category', '').lower() == research_category.lower()
        ]
        
        if not matching_combinations:
            logger.warning(f"No combinations found for research category: {research_category}")
            return []
        
        for combo in matching_combinations:
            logger.info(f"Processing combination for category: {combo['research_category']}")
            
            # Extract key terms from boolean combination
            boolean_query = combo.get('unique_boolean_combination', '')
            if not boolean_query:
                continue
            
            # Get selected terms for more targeted searching
            selected_terms = combo.get('selected_terms', [])
            
            # Create multiple arXiv queries
            arxiv_queries = self._create_arxiv_queries(selected_terms)
            
            for query in arxiv_queries:
                logger.info(f"Executing query: {query}")
                
                # Search arXiv
                papers = self._search_arxiv(query, max_results_per_query)
                
                # Add metadata about the search and filter duplicates
                for paper in papers:
                    paper_title = paper.get('Title', '').lower()
                    if paper_title not in seen_papers and paper_title != 'n/a':
                        paper['search_category'] = combo['research_category']
                        paper['selected_terms'] = combo.get('selected_terms', [])
                        all_papers.append(paper)
                        seen_papers.add(paper_title)
                
                # Rate limiting
                time.sleep(self.rate_limit_delay)
        
        logger.info(f"Total unique papers found for {research_category}: {len(all_papers)}")
        return all_papers
    
    def search_all_categories(self, max_results_per_query: int = 15) -> Dict[str, List[Dict]]:
        """
        Search for papers across all research categories
        """
        if not self.unique_combinations:
            logger.error("No unique combinations loaded")
            return {}
        
        results_by_category = {}
        
        # Get unique research categories
        categories = list(set(combo.get('research_category', '') for combo in self.unique_combinations))
        
        for category in categories:
            if category:
                logger.info(f"Searching category: {category}")
                papers = self.search_by_category(category, max_results_per_query)
                results_by_category[category] = papers
                
                # Additional rate limiting between categories
                time.sleep(self.rate_limit_delay)
        
        return results_by_category
    
    def save_results(self, papers: List[Dict], output_file: str = 'output/obtained_lit.json'):
        """
        Save search results to JSON file
        """
        try:
            # Clean papers for final output (remove internal tracking fields)
            cleaned_papers = []
            for paper in papers:
                cleaned_paper = {
                    'Title': paper.get('Title', 'N/A'),
                    'Year': paper.get('Year', 'N/A'), 
                    'Authors': paper.get('Authors', 'N/A'),
                    'Extracted abstract': paper.get('Extracted abstract', 'N/A'),
                    'Extracted text without bib and appendix': paper.get('Extracted text without bib and appendix', 'N/A')
                }
                cleaned_papers.append(cleaned_paper)
            
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(cleaned_papers, f, indent=4, ensure_ascii=False)
            logger.info(f"Results saved to {output_file}")
            logger.info(f"Total papers saved: {len(cleaned_papers)}")
        except Exception as e:
            logger.error(f"Error saving results: {str(e)}")

def test_simple_search():
    """Test with a simple search to verify the API is working"""
    searcher = ArxivPaperSearcher()
    
    # Test with a simple query that should return results
    test_papers = searcher._search_arxiv('all:"machine learning"', max_results=5)
    
    if test_papers:
        print(f"✓ API test successful! Found {len(test_papers)} papers")
        print(f"Sample paper: {test_papers[0]['Title']}")
        return True
    else:
        print("✗ API test failed - no papers found")
        return False

def main():
    """
    Main function to demonstrate usage
    """
    print("=== ArXiv Paper Search ===")
    
    # First test if the API is working
    if not test_simple_search():
        print("Please check your internet connection and try again.")
        return
    
    searcher = ArxivPaperSearcher()
    
    print("Available options:")
    print("1. Search specific research category")
    print("2. Search all categories")
    print("3. Test search with sample category")
    
    choice = input("Enter choice (1, 2, or 3): ").strip()
    
    if choice == "1":
        category = input("Enter research category: ").strip()
        papers = searcher.search_by_category(category, max_results_per_query=10)
        searcher.save_results(papers)
        
    elif choice == "2":
        print("Searching all categories...")
        results_by_category = searcher.search_all_categories(max_results_per_query=8)
        
        # Flatten results
        all_papers = []
        for category, papers in results_by_category.items():
            all_papers.extend(papers)
        
        searcher.save_results(all_papers)
        
        # Also save category-wise results
        with open('output/obtained_lit_by_category.json', 'w', encoding='utf-8') as f:
            json.dump(results_by_category, f, indent=4, ensure_ascii=False)
        
        print(f"Results saved to obtained_lit.json and obtained_lit_by_category.json")
    
    elif choice == "3":
        # Test with the provided category from your example
        papers = searcher.search_by_category("Broad Foundational Search", max_results_per_query=5)
        if papers:
            print(f"Found {len(papers)} papers for test category")
            searcher.save_results(papers, 'test_obtained_lit.json')
        else:
            print("No papers found for test category")
    
    else:
        print("Invalid choice")

if __name__ == "__main__":
    main()