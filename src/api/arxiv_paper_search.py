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
    Automated arXiv paper search using unique boolean combinations
    """
    
    def __init__(self, unique_combinations_file='../../output/unique_boolean_combinations.json'):
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
        Extract key terms from complex boolean combination for arXiv search
        """
        # Extract terms from quoted strings
        quoted_terms = re.findall(r'"([^"]+)"', boolean_combination)
        
        # Clean and filter terms
        key_terms = []
        seen = set()
        
        for term in quoted_terms:
            # Clean the term
            clean_term = re.sub(r'[^\w\s-]', '', term).strip()
            clean_lower = clean_term.lower()
            
            # Filter criteria
            if (len(clean_term) > 2 and 
                clean_lower not in seen and 
                clean_lower not in ['or', 'and', 'the', 'for', 'with', 'data']):
                key_terms.append(clean_term)
                seen.add(clean_lower)
                
                if len(key_terms) >= 8:  # Limit to 8 most important terms
                    break
        
        return key_terms
    
    def _create_arxiv_queries(self, combination_title: str, key_terms: List[str]) -> List[str]:
        """
        Create targeted arXiv queries based on key terms and combination title
        """
        queries = []
        
        # Strategy 1: Individual important terms
        priority_terms = []
        for term in key_terms[:4]:  # Top 4 terms
            if len(term.split()) <= 3:  # Prefer shorter, more specific terms
                clean_term = term.replace('"', '').strip()
                if clean_term:
                    priority_terms.append(clean_term)
        
        # Create individual term searches
        for term in priority_terms[:2]:  # Use top 2 terms
            queries.append(f'all:"{term}"')
        
        # Strategy 2: Combined searches for related terms
        if len(priority_terms) >= 2:
            term1, term2 = priority_terms[0], priority_terms[1]
            queries.append(f'all:"{term1}" AND all:"{term2}"')
        
        # Strategy 3: Category-based searches based on combination title
        category_mappings = {
            "Broad Foundational Search": ['cat:cs.LG', 'cat:cs.AI', 'cat:stat.ML'],
            "Humanitarian": ['all:"humanitarian" OR all:"crisis"', 'all:"disaster relief"'],
            "Social Impact": ['all:"social impact"', 'all:"ethics"'],
            "Inclusion": ['all:"bias" OR all:"fairness"', 'all:"diversity"'],
            "Representation": ['all:"representation" OR all:"inclusion"'],
            "Harm Reduction": ['all:"safety" OR all:"harm"', 'all:"risk assessment"'],
            "Safety": ['all:"safety" OR all:"security"'],
            "Control": ['all:"privacy" OR all:"consent"', 'all:"data protection"'],
            "Consent": ['all:"consent" OR all:"privacy"'],
            "Data Rights": ['all:"data rights" OR all:"privacy"'],
            "Participatory": ['all:"participatory" OR all:"human-centered"'],
            "Environmental": ['all:"environmental" OR all:"sustainability"', 'all:"energy consumption"'],
            "Infrastructural": ['all:"infrastructure" OR all:"computational"'],
            "Monitoring": ['all:"monitoring" OR all:"evaluation"'],
            "Deployment": ['all:"deployment" OR all:"production"'],
            "Redress": ['all:"accountability" OR all:"redress"']
        }
        
        # Add category-specific queries
        for category_key, category_queries in category_mappings.items():
            if category_key.lower() in combination_title.lower():
                queries.extend(category_queries[:1])  # Add one category-specific query
                break
        
        return queries[:4]  # Limit to 4 queries per combination to manage rate limiting
    
    def _search_arxiv(self, query: str, max_results: int = 20) -> List[Dict]:
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
                    
                    # For now, use abstract as extracted text (full PDF processing would be needed for complete text)
                    extracted_text = abstract
                    
                    paper = {
                        'Title': title,
                        'Year': year,
                        'Authors': authors_str,
                        'Extracted abstract': abstract,
                        'Extracted text without bib and appendix': extracted_text
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
    
    def search_all_combinations(self, max_results_per_query: int = 15) -> List[Dict]:
        """
        Search for papers using all combinations in unique_boolean_combinations.json
        """
        if not self.unique_combinations:
            logger.error("No unique combinations loaded")
            return []
        
        all_papers = []
        seen_papers = set()  # Track by title to avoid duplicates
        
        logger.info(f"Processing {len(self.unique_combinations)} unique boolean combinations...")
        
        for i, combination in enumerate(self.unique_combinations, 1):
            combination_title = combination.get('Combination_title', f'Combination {i}')
            boolean_combination = combination.get('boolean_combination', '')
            
            logger.info(f"\n--- Processing {i}/{len(self.unique_combinations)}: {combination_title} ---")
            
            if not boolean_combination:
                logger.warning(f"No boolean combination found for: {combination_title}")
                continue
            
            # Extract key terms from the boolean combination
            key_terms = self._extract_key_terms_from_boolean(boolean_combination)
            logger.info(f"Extracted key terms: {key_terms[:5]}...")  # Show first 5 terms
            
            if not key_terms:
                logger.warning(f"No valid key terms extracted for: {combination_title}")
                continue
            
            # Create targeted arXiv queries
            arxiv_queries = self._create_arxiv_queries(combination_title, key_terms)
            
            combination_papers = []
            
            for query in arxiv_queries:
                logger.info(f"  Executing query: {query}")
                
                # Search arXiv
                papers = self._search_arxiv(query, max_results_per_query)
                
                # Add papers and filter duplicates
                for paper in papers:
                    paper_title = paper.get('title', '').lower()
                    if paper_title not in seen_papers and paper_title != 'n/a':
                        # Add metadata about which combination found this paper
                        paper['Search_Category'] = combination_title
                        combination_papers.append(paper)
                        seen_papers.add(paper_title)
                
                # Rate limiting between queries
                time.sleep(self.rate_limit_delay)
            
            logger.info(f"  Found {len(combination_papers)} unique papers for {combination_title}")
            all_papers.extend(combination_papers)
            
            # Additional rate limiting between combinations
            time.sleep(self.rate_limit_delay)
        
        logger.info(f"\n=== Search Complete ===")
        logger.info(f"Total unique papers found: {len(all_papers)}")
        logger.info(f"Processed {len(self.unique_combinations)} combinations")
        
        return all_papers
    
    def save_results(self, papers: List[Dict], output_file: str = 'obtained_lit.json'):
        """
        Save search results to JSON file
        """
        try:
            # Clean papers for final output (remove internal tracking fields)
            cleaned_papers = []
            for paper in papers:
                cleaned_paper = {
                    'title': paper.get('title', 'N/A'),
                    'authors': paper.get('authors', 'N/A'),
                    'url': paper.get('url', 'N/A'),
                    'abstract': paper.get('abstract', 'N/A'),
                    'year': paper.get('year', 'N/A'),
                    'extracted_text': paper.get('extracted_text', 'N/A')
                }
                cleaned_papers.append(cleaned_paper)
            
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(cleaned_papers, f, indent=4, ensure_ascii=False)
            logger.info(f"\n✓ Results saved to {output_file}")
            logger.info(f"✓ Total papers saved: {len(cleaned_papers)}")
            return True
        except Exception as e:
            logger.error(f"✗ Error saving results: {str(e)}")
            return False

def search_arxiv_papers(unique_combinations_file='../../output/unique_boolean_combinations.json', output_file='../../output/obtained_lit.json'):
    """
    Main function to search arXiv papers using all unique boolean combinations
    
    Args:
        unique_combinations_file (str): Path to the unique combinations JSON file
        output_file (str): Path to save the results
    
    Returns:
        bool: True if successful, False otherwise
    """
    logger.info("=== Starting Automated arXiv Paper Search ===")
    
    # Initialize searcher
    searcher = ArxivPaperSearcher(unique_combinations_file)
    
    if not searcher.unique_combinations:
        logger.error("Failed to load unique combinations file")
        return False
    
    # Search all combinations
    all_papers = searcher.search_all_combinations()
    
    if all_papers:
        # Save results
        success = searcher.save_results(all_papers, output_file)
        
        if success:
            logger.info("=== Search completed successfully! ===")
            
            # Display summary by category
            categories = {}
            for paper in all_papers:
                category = paper.get('Search_Category', 'Unknown')
                categories[category] = categories.get(category, 0) + 1
            
            logger.info("\nPapers found by category:")
            for category, count in categories.items():
                logger.info(f"  {category}: {count} papers")
            
            return True
        else:
            logger.error("Failed to save results")
            return False
    else:
        logger.error("No papers found")
        return False

def main():
    """Main function - automatically search all combinations and save results"""
    success = search_arxiv_papers()
    
    if success:
        print("✓ arXiv paper search completed successfully!")
        print("✓ Results saved to 'obtained_lit.json'")
    else:
        print("✗ arXiv paper search failed")
        print("Check the log messages above for details")

if __name__ == "__main__":
    main()