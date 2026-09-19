---
title: Stage 4 — Multi-repository search
---

# Multi-Repository Research Paper Web Scraper

## Overview
This script orchestrates automated paper discovery across multiple academic repositories including Google Scholar, OpenAlex, Europe PMC, and ArXiv. It transforms Boolean search combinations into a unified literature collection pipeline, automatically downloading papers, extracting full text, and aggregating results into a single comprehensive dataset.

## Data Flow
```
../output/unique_boolean_combinations.json → Process → ../output/obtained_lit.json
```

**Input Directory:** `../output/`  
**Input Format:** JSON file with unique Boolean combinations by research category  
**Process:** Multi-repository search, PDF download, text extraction, result aggregation  
**Output:** Comprehensive JSON database with full paper content and metadata  
**Output Directory:** `../output/`  
**Output Format:** JSON with unified paper records from all repositories

## Repository Integration Architecture

### Supported Academic Repositories

| Repository | Coverage | Strengths | Search Method |
|------------|----------|-----------|---------------|
| **Google Scholar** | Broad academic coverage | Citation tracking, diverse sources | `scholarly` library with filtering |
| **OpenAlex** | Open access focus | Structured metadata, API reliability | REST API with cursor pagination |
| **Europe PMC** | Life sciences emphasis | Full-text access, medical literature | RESTful web services |
| **ArXiv** | Preprints and CS/Physics | Latest research, open access | Integration with existing arXiv module |

### Core Processing Components

#### 1. Multi-Repository Search Engine
**Purpose:** Coordinates searches across all repositories using unified Boolean queries
- **Query Adaptation:** Transforms Boolean combinations for repository-specific formats
- **Rate Limiting:** Respects each repository's API guidelines
- **Error Recovery:** Continues processing if individual repositories fail
- **Result Standardization:** Normalizes data formats across different sources

#### 2. Intelligent PDF Download System
**Purpose:** Automated paper acquisition with fallback strategies
- **Direct PDF Detection:** Identifies PDF URLs from content headers
- **HTML Parsing:** Extracts PDF links from publisher pages using BeautifulSoup
- **Multi-Format Support:** Handles various publisher link formats (/pdf, /epdf)
- **Error Handling:** Graceful degradation when papers are behind paywalls

#### 3. Full-Text Extraction Engine  
**Purpose:** Converts downloaded PDFs to searchable text
- **Multi-Library Support:** Uses PyPDF2 and PyMuPDF for robust extraction
- **PDF Validation:** Checks PDF headers and repairs missing EOF markers
- **Error Recovery:** Handles corrupted or encrypted PDFs gracefully
- **Text Cleaning:** Normalizes extracted content for consistency

#### 4. Result Aggregation System
**Purpose:** Merges results from all repositories into unified format
- **Incremental Building:** Appends results progressively to avoid memory issues
- **Source Tracking:** Maintains repository attribution for each paper
- **Duplicate Handling:** Basic duplicate prevention across sources
- **Progress Monitoring:** Real-time feedback on collection progress

## Repository-Specific Implementation

### Google Scholar Integration
```python
def search_google_scholar_scholarly(query, max_results, pub_year=2020, num_citations=0)
```

**Features:**
- **Quality Filtering:** Minimum publication year and citation thresholds
- **Citation Analysis:** Leverages Google Scholar's citation tracking
- **Rate Limiting:** Built-in delays to prevent blocking
- **Metadata Extraction:** Author lists, publication years, abstracts

**Filtering Criteria:**
- Publication year >= 2020 (configurable)
- Minimum citation count >= 0 (configurable)
- Only papers with successful PDF downloads

### OpenAlex Integration
```python
def search_openalex(query, per_page=200, max_pages=None, sleep_between=1.0)
```

**Features:**
- **Cursor Pagination:** Efficient handling of large result sets
- **Abstract Reconstruction:** Rebuilds abstracts from inverted indexes
- **Open Access Priority:** Focuses on freely available content
- **Structured Metadata:** Rich bibliographic information

**API Capabilities:**
- Up to 200 results per page
- Unlimited pagination with cursor support
- 1-second delays between requests
- Comprehensive work metadata

### Europe PMC Integration
```python
def search_europepmc(query, result_type='core', page_size=1000, max_pages=None)
```

**Features:**
- **Medical Focus:** Specialized for life sciences literature
- **Full-Text Access:** Direct links to publisher content
- **Flexible Result Types:** 'lite' for metadata, 'core' for abstracts
- **Large Page Sizes:** Up to 1000 results per request

**Metadata Extraction:**
- Journal and book publication details
- Comprehensive author information
- Abstract and full-text URL handling
- Publication year from multiple sources

### ArXiv Integration
```python
def get_arxiv_results(path_to_unique_boolean_combinations)
```

**Features:**
- **Module Reuse:** Integrates existing ArXiv search functionality
- **Temporary File Handling:** Manages intermediate results efficiently
- **Error Recovery:** Graceful handling of import or execution failures
- **Result Standardization:** Converts ArXiv format to unified structure

## Input Format Requirements

The script expects output from `unique_boolean_combinations.py`:

```json
[
  {
    "Combination_title": "Broad Foundational Search",
    "boolean_combination": "(\"Foundation model\" OR \"Large language model\") AND (\"Machine Learning\" OR \"ML\")"
  },
  {
    "Combination_title": "Humanitarian & Social Impact Search",
    "boolean_combination": "(\"Humanitarian\" OR \"Crisis response\") AND (\"Social Good\" OR \"Social impact\")"
  }
]
```

## Output Format

The script generates a comprehensive literature database:

```json
[
  {
    "title": "Large Language Models in Crisis Response: A Survey",
    "authors": "Smith, J., Johnson, M., Chen, L.",
    "url": "https://example.com/paper1",
    "abstract": "This comprehensive survey examines the application of large language models...",
    "year": "2023",
    "extracted_text": "Complete full-text content of the paper including methodology, results, and conclusions..."
  },
  {
    "title": "Ethical Considerations in AI for Humanitarian Applications",
    "authors": "Brown, K., Davis, R., Wilson, S.",
    "url": "https://example.com/paper2", 
    "abstract": "We explore the ethical implications of deploying AI systems in humanitarian contexts...",
    "year": "2023",
    "extracted_text": "Full paper content extracted from PDF including all sections and references..."
  }
]
```

## Core Functions Reference

### `get_llit_papers(path_to_unique_boolean_combinations)`
**Purpose:** Main orchestration function for literature collection  
**Process:**
1. Load Boolean combinations from JSON
2. Iterate through each research category
3. Execute searches across all repositories
4. Aggregate results progressively
5. Return path to comprehensive literature file

**Parameters:**
- `path_to_unique_boolean_combinations` (str): Input file path

**Returns:** 
- Path to output JSON file with all collected papers

### `download_research_paper(url, save_dir)`
**Purpose:** Generic paper download with publisher support  
**Strategy:**
1. **Direct PDF Check:** Verify if URL is direct PDF link
2. **HTML Parsing:** Extract PDF links from publisher pages  
3. **Fallback Handling:** Multiple link pattern recognition
4. **File Management:** Organized storage with proper naming

**Parameters:**
- `url` (str): Paper URL or direct PDF link
- `save_dir` (str): Directory for downloaded papers

**Returns:**
- File path on success, None on failure

### `extract_paper_text(research_paper_path)`
**Purpose:** Robust PDF text extraction  
**Features:**
- **PDF Validation:** Checks for valid PDF format
- **EOF Repair:** Fixes common PDF corruption issues
- **Multi-Page Handling:** Extracts from all pages
- **Error Recovery:** Handles encrypted or corrupted files

**Parameters:**
- `research_paper_path` (str): Path to downloaded PDF

**Returns:**
- Extracted text string or raises appropriate exceptions

### `append_results_to_json(output_file, new_results, source_name)`
**Purpose:** Incremental result aggregation  
**Features:**
- **File Creation:** Creates output file if it doesn't exist
- **Progressive Building:** Appends results without memory overload
- **Source Tracking:** Maintains attribution for debugging
- **Error Recovery:** Continues processing despite write failures

## Search Strategy Implementation

### Query Processing Pipeline
1. **Boolean Combination Loading:** Read research category combinations
2. **Query Adaptation:** Transform Boolean logic for each repository
3. **Repository Sequencing:** Execute searches in optimal order
4. **Result Collection:** Gather papers with metadata extraction
5. **Text Processing:** Download and extract full content
6. **Aggregation:** Merge results into unified format

### Quality Control Measures
- **Publication Year Filtering:** Focus on recent research (2020+)
- **Citation Threshold:** Prioritize impactful papers
- **Download Verification:** Ensure successful PDF acquisition
- **Text Extraction Validation:** Verify readable content extraction
- **Source Attribution:** Track which repository found each paper

### Rate Limiting Strategy
- **Google Scholar:** Built-in delays in `scholarly` library
- **OpenAlex:** 1-second delays between requests
- **Europe PMC:** 1-second delays between requests  
- **ArXiv:** Handled by existing module (3-second delays)

## Usage

### Basic Literature Collection
```python
from web_scrape import get_llit_papers

# Collect papers using all repositories
output_file = get_llit_papers('./output/unique_boolean_combinations.json')
print(f"Literature collection saved to: {output_file}")
```

### Repository-Specific Search
```python
from web_scrape import search_repository

# Search specific repository
query = '"machine learning" AND "healthcare"'
results = search_repository(query, "openalex")
print(f"Found {len(results)} papers from OpenAlex")
```

### Manual PDF Processing
```python
from web_scrape import download_research_paper, extract_paper_text

# Download and extract specific paper
paper_url = "https://example.com/paper.pdf"
pdf_path = download_research_paper(paper_url)
if pdf_path:
    text_content = extract_paper_text(pdf_path)
    print(f"Extracted {len(text_content)} characters")
```

### Command Line Execution
```bash
python web_scrape.py ./output/unique_boolean_combinations.json
```

## Error Handling & Recovery

### Network-Related Errors
- **Connection Timeouts:** Configurable timeouts for each repository
- **Rate Limiting:** Automatic delays and retry mechanisms  
- **Server Errors:** Graceful handling of 4xx/5xx responses
- **Repository Unavailability:** Continues with available sources

### PDF Processing Errors
- **Download Failures:** Logs failures but continues processing
- **Corrupted PDFs:** Attempts repair before extraction
- **Paywall Detection:** Identifies and reports access restrictions
- **Format Issues:** Multiple extraction libraries as fallbacks

### Data Processing Errors
- **Missing Metadata:** Handles incomplete paper records gracefully
- **Text Extraction Failures:** Reports issues but preserves other data
- **JSON Write Errors:** Maintains data integrity during aggregation
- **File System Issues:** Creates directories and handles permissions

### Console Output Examples
```
Starting to scrape google scholar...
🚀 Searching Google Scholar for '(Foundation model OR LLM) AND (Machine Learning)'...
found pdf link using beautifulsoup and now proceeding to download the paper...
✅ Appended 15 results from Google Scholar. Total papers: 15

Starting to scrape openalex...
✅ Appended 32 results from OpenAlex. Total papers: 47

Starting to scrape europepmc...
No PDF link found on this page...https://example.com/paper1
✅ Appended 8 results from Europe PMC. Total papers: 55

Starting to scrape arxiv...
✅ ArXiv search completed - found 23 papers
✅ Appended 23 results from ArXiv. Total papers: 78

Results written to ./output/obtained_lit.json
```

## File Structure Requirements

```
CHITCHAT/
├── output/
│   ├── unique_boolean_combinations.json   # Input
│   └── obtained_lit.json                  # Output 
├── src/
│   └── api/
│       └── web_scrape.py
├── research_paper_downloads/              # (RCP) Downloaded PDFs
│   ├── paper1.pdf
│   ├── paper2.pdf
│   └── ...
└── temp/
    └── temp_arxiv_results.json             # (RCP) Temporary files
```

## Dependencies & Requirements

### Required Libraries
```python
# Web scraping and HTTP
import requests
from bs4 import BeautifulSoup
from scholarly import scholarly

# PDF processing  
import fitz  # PyMuPDF
from PyPDF2 import PdfReader

# Standard libraries
import json, time, os, io, re, tempfile
from urllib.parse import quote_plus, urljoin, urlparse
```

### External API Dependencies
- **Google Scholar:** Via `scholarly` library (unofficial)
- **OpenAlex:** Official REST API (https://api.openalex.org/)
- **Europe PMC:** Official web services (https://europepmc.org/RestfulWebService)
- **ArXiv:** Integrated via existing module

## Performance Considerations

### Memory Management
- **Incremental Processing:** Results appended progressively to avoid memory overload
- **Streaming Downloads:** PDF downloads use chunked streaming
- **Temporary File Cleanup:** Automatic cleanup of intermediate files
- **Result Aggregation:** JSON files updated incrementally

### Processing Efficiency
- **Parallel Repository Access:** Sequential processing respects rate limits
- **Caching Strategy:** Downloaded PDFs stored for potential reuse
- **Error Recovery:** Failed downloads don't block other papers
- **Progress Tracking:** Real-time feedback on collection status

### Scalability Factors
- **Result Volume:** Can handle thousands of papers per repository
- **Storage Requirements:** Downloaded PDFs require significant disk space
- **Processing Time:** Full-text extraction is time-intensive
- **API Limits:** Each repository has different rate limiting rules

## Integration Workflow

This script completes the comprehensive research automation pipeline:

1. **Step 1:** `boolean_combinations.py` - Generate basic Boolean combinations
2. **Step 2:** `unique_boolean_combinations.py` - Create research-focused combinations  
3. **Step 3:** `arxiv_paper_search.py` - Execute arXiv-specific searches
4. **Step 4:** `web_scrape.py` - **Comprehensive multi-repository collection**
5. **Step 5:** Manual analysis of comprehensive literature database

## Customization Options

### Repository Configuration
```python
# Enable/disable specific repositories
def get_llit_papers(path_to_unique_boolean_combinations):
    # Customize repository selection
    search_google_scholar = True
    search_openalex = True  
    search_europepmc = True
    search_arxiv = True
```

### Quality Filters
```python
# Modify paper quality criteria
google_scholar_results = search_google_scholar_scholarly(
    query=unique_combinations,
    pub_year=2018,  # Change minimum year
    num_citations=5  # Require minimum citations
)
```

### Download Configuration
```python
# Customize PDF download behavior
download_research_paper(
    url=paper_url,
    save_dir="custom_downloads"  # Custom storage location
)
```

## Technical Implementation Notes

- **Multi-Format PDF Support:** Handles various publisher PDF formats and protection schemes
- **Abstract Reconstruction:** Rebuilds abstracts from OpenAlex inverted indexes
- **Publisher Compatibility:** Generic PDF extraction works across major publishers
- **Error Resilience:** Continues processing despite individual paper failures
- **Result Standardization:** Normalizes metadata formats across repositories
- **Progress Monitoring:** Comprehensive logging for debugging and monitoring
