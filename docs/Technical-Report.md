<a id="technical-report-top"></a>

<div align="center">
  <a href="https://github.com/fiifidawson/CHITCHAT">
    <img src="../assets/doc.png" alt="Logo" width="80" height="80">
  </a>
  <h3 align="center">Technical Report</h3>
</div>

TODO: Complete Table of Contents
<!-- TABLE OF CONTENTS -->
<details>
  <summary>Table of Contents</summary>
  <ol>
    <li>
      <a href="#project-overview">Project Overview</a>
    </li>
    <li>
      <a href="#folder-structure">Folder Structure</a>
    </li>
        <li>
      <a href="#setup">Setup</a>
      <ul>      
        <li><a href="#virtual-environment-setup">Virtual Environment Setup</a>
          <ul>      
          <li><a href="#linuxunix-systems">Linux/Unix Systems</a></li>       
        </ul>
        <ul>      
          <li><a href="#windows-systems">Windows Systems</a></li>       
        </ul></li>       
      </ul>
    </li>
    </li>
        <li>
      <a href="#work-flow">Main Section</a>
      <ul>      
        <li><a href="#sub-section">Sub-Section</a></li>       
      </ul>
    </li>
    </li>
        <li>
      <a href="#main-section">Main Section</a>
      <ul>      
        <li><a href="#sub-section">Sub-Section</a></li>       
      </ul>
    </li>
    </li>
        <li>
      <a href="#contributing">Contributing</a>
    </li>
    </li>
        <li>
      <a href="#main-section">Main Section</a>
      <ul>      
        <li><a href="#sub-section">Sub-Section</a></li>       
      </ul>
    </li>
    </li>
        <li>
      <a href="#main-section">Main Section</a>
      <ul>      
        <li><a href="#sub-section">Sub-Section</a></li>       
      </ul>
    </li>
  </ol>
</details>

---

# Project Overview

---

<p align="right">[<a href="#technical-report-top">back to top</a>]</p>

# Folder Structure

````
CHITCHAT/
    ├── analysis
    ├── bucket/
    │   ├── plots/
    │   │   ├── openai_analysis/
    │   │   │   └── plots
    │   │   └── web_scrape/
    │   │       └── plots
    │   ├── paper_analysis.py
    │   ├── web_scrape_analysis.py
    │   └── word_cloud_analysis.py      
    ├── analyze_outputs/
    │   └── screening_results
    ├── assets/
    │   └── images
    ├── data/
    │   ├── boolean.csv
    │   ├── boolean_combinations.json
    │   ├── structure.json
    │   └── test_papers.json
    ├── docs/
    │   ├── prompt/
    │   │   └── paper_screening_prompt.txt
    │   ├── Technical-Report.md
    │   └── instructions.md
    ├── output/
    │   ├── screening_results.jsonl
    │   └── unique_boolean_combinations.json
    ├── scripts/
    │   ├── screen_papers.sh
    │   └── web_scrape.sh
    ├── src/
    │   ├── api/
    │   │   ├── arxiv_paper_search.py
    │   │   └── web_scrape.py
    │   ├── boolean/
    │   │   ├── boolean_combinations.py
    │   │   ├── csv_to_json.py
    │   │   └── unique_boolean_combinations.py
    │   └── screen_papers.py
    ├── .gitignore
    ├── README.md
    ├── layout.json
    ├── playground.ipynb
    └── requirements.txt
````
<p align="right">[<a href="#technical-report-top">back to top</a>]</p>

---

# Setup
## Virtual Environment Setup
### Linux/Unix Systems
1. **Prerequisites**
    Update your system and install Python 3.10 with venv support:
    ```bash
    sudo apt update
    sudo apt install python3.10 python3.10-venv
    ```

2. **Create Virtual Environment**
    ```bash
    python3.10 -m venv .venv
    ```

3. **Activate Virtual Environment**
    ```bash
    source .venv/bin/activate
    ```
4. **Install Dependencies**
    ```bash
    pip install -r requirements.txt 
    ```

5. **Deactivate Virtual Environment**
    ```bash
    deactivate
    ```
<p align="right">[<a href="#technical-report-top">back to top</a>]</p>

### Windows Systems

1. **Create Virtual Environment**
    ```cmd
    python -m venv .venv
    ```

2. **Activate Virtual Environment**
    ```cmd
    .venv\Scripts\activate
    ```
3. **Install Dependencies**
    ```cmd
    pip install -r requirements.txt 
    ```

4. **Deactivate Virtual Environment**
    ```cmd
    deactivate
    ```
<p align="right">[<a href="#technical-report-top">back to top</a>]</p>

---

# Workflow

```
Modules:
input_directory: input_format -> input -> process -> output -> output_directory: output_format
```

<p align="right">[<a href="#technical-report-top">back to top</a>]</p>

---

## Boolean Combinations Generator

### Overview
This script transforms word lists with synonyms into Boolean search combinations, making it easy to create comprehensive search queries for databases, search engines, or research applications.

### Data Flow
```
../data/structure.json → Process → ../data/boolean_combinations.json
```

**Input Directory:** `./data/`  
**Input Format:** JSON file containing words and their synonyms  
**Process:** Generate Boolean OR combinations from words and synonyms  
**Output:** JSON file with Boolean search strings  
**Output Directory:** `./data/`  
**Output Format:** JSON with Boolean combinations

### Function Reference

`generate_boolean_combinations(input_file, output_file)`

**Purpose:** Converts a structured word list into Boolean search combinations using OR operators.

**Parameters:**
- `input_file` (str, optional): Path to input JSON file (default: `'../data/structure.json'`)
- `output_file` (str, optional): Path for output JSON file (default: `'../data/boolean_combinations.json'`)

**Returns:**
- List of dictionaries with Boolean combinations on success
- `None` if an error occurs

### Input Format Requirements

Your input JSON file should contain an array of objects with the following structure:

```json
[
  {
    "WORD": "example",
    "SYNONYMS AND NEAR SYNONYMS": "sample, instance, illustration, case"
  },
  {
    "WORD": "research",
    "SYNONYMS AND NEAR SYNONYMS": "study, investigation, analysis"
  }
]
```

**Required Fields:**
- `WORD`: The primary term
- `SYNONYMS AND NEAR SYNONYMS`: Comma-separated list of related terms

### Output Format

The script generates a JSON file with Boolean search combinations:

```json
[
  {
    "WORD": "example",
    "boolean_combination": "(\"example\" OR \"sample\" OR \"instance\" OR \"illustration\" OR \"case\")"
  },
  {
    "WORD": "research", 
    "boolean_combination": "(\"research\" OR \"study\" OR \"investigation\" OR \"analysis\")"
  }
]
```

### Processing Logic

The script performs the following operations:

1. **File Reading:** Loads and parses the input JSON file
2. **Data Extraction:** Extracts the main word and synonyms from each entry
3. **Synonym Processing:** 
   - Splits comma-separated synonyms
   - Removes whitespace and empty entries
   - Eliminates duplicates while preserving order
4. **Boolean Generation:** 
   - Wraps each term in quotes for exact matching
   - Combines all terms with OR operators
   - Encloses the entire combination in parentheses
5. **Output Generation:** Saves the results as formatted JSON

### Usage 

#### Basic Usage
```python
from boolean_combinations import generate_boolean_combinations

# Use default file paths
result = generate_boolean_combinations()
```

#### Custom File Paths
```python
# Specify custom input and output files
result = generate_boolean_combinations(
    input_file='./my_data/words.json',
    output_file='./output/search_terms.json'
)
```

#### Command Line Execution
```bash
python boolean_combinations.py
```

### Error Handling

The script includes error handling for:

- **File Not Found:** Displays clear message if input file doesn't exist
- **Invalid JSON:** Catches and reports JSON parsing errors
- **General Exceptions:** Handles unexpected errors gracefully

All errors are printed to console with descriptive messages.

### Output Messages

The script provides feedback during execution:
- Success message with count of generated combinations
- Preview of first 3 Boolean combinations for verification
- Error messages for troubleshooting

### File Structure Requirements

Ensure your directory structure includes:
```
CHITCHAT/
└── data/
        ├── structure.json                # Input file
        └── boolean_combinations.json     # Output file (generated)
└── src/
    └── boolean/
        └── boolean_combinations.py 
```

**Notes:**

- Terms are automatically wrapped in quotes to ensure exact phrase matching
- Duplicates are removed to keep combinations clean
- Order of terms is preserved from the input
- The script handles UTF-8 encoding for international characters


<p align="right">[<a href="#technical-report-top">back to top</a>]</p>

---

## Unique Boolean Combinations Generator

### Overview
This script creates unique Boolean search combinations by combining multiple predefined research categories. It takes the output from the basic boolean combinations generator and creates complex search queries tailored for academic research across different domains like AI, humanitarian work, and social impact.

### Data Flow
```
../data/boolean_combinations.json → Process → ../output/unique_boolean_combinations.json
```

**Input Directory:** `./data/`  
**Input Format:** JSON file with individual Boolean combinations  
**Process:** Combine multiple Boolean terms using AND operators for research categories  
**Output:** JSON file with complex multi-category Boolean search strings  
**Output Directory:** `./output/`  
**Output Format:** JSON with unique category-based combinations

### Core Components

#### `UniqueBooleanCombinationsGenerator` Class

**Purpose:** Main class that handles the generation of unique Boolean combinations for specific research categories.

**Key Features:**
- Loads existing Boolean combinations from JSON
- Maps predefined research categories to relevant search terms
- Combines multiple Boolean expressions using AND operators
- Provides detailed feedback on missing or found keys
- Handles error cases gracefully

<p align="right">[<a href="#technical-report-top">back to top</a>]</p>

### Predefined Research Categories

The script includes 8 specialized research categories:

#### 1. Broad Foundational Search
**Focus:** Core AI and ML concepts  
**Key Terms:** Foundation model, AI Systems, Machine Learning, Deep Learning, Applications & Domains

#### 2. Humanitarian & Social Impact Search
**Focus:** Crisis response and humanitarian applications  
**Key Terms:** Humanitarian principles, Neutrality, Social Good, Vulnerable Populations, Human Rights

#### 3. Inclusion & Representation Search
**Focus:** Equity and representation in AI  
**Key Terms:** Vulnerable Populations, Human Rights, Data Collection Methods, Rights & Protection

#### 4. Transparency & Accountability Search
**Focus:** AI governance and accountability  
**Key Terms:** AI Systems, Data Processing, Rights Frameworks, Development Guides

#### 5. Harm Reduction & Safety Search
**Focus:** AI safety and risk mitigation  
**Key Terms:** Mitigation Strategies, Environmental Concerns, Rights Frameworks, Safety Guides

#### 6. Control, Consent & Personal Data Rights
**Focus:** Data privacy and user control  
**Key Terms:** Rights Frameworks, Data Collection, Privacy Protection, AI Systems

#### 7. Consent, Agency & Participatory AI
**Focus:** User agency and participatory design  
**Key Terms:** Human Rights, Organizations, Key Actions, Social Good

#### 8. Environmental & Infrastructural Cost
**Focus:** Environmental impact of AI systems  
**Key Terms:** Environmental Concerns, Mitigation, AI Development, Infrastructure

<p align="right">[<a href="#technical-report-top">back to top</a>]</p>

### Input Format Requirements

The script requires the output from `boolean_combinations.py`:

```json
[
  {
    "WORD": "Foundation model",
    "boolean_combination": "(\"Foundation model\" OR \"Large language model\" OR \"Pre-trained model\")"
  },
  {
    "WORD": "Machine Learning",
    "boolean_combination": "(\"Machine Learning\" OR \"ML\" OR \"Statistical learning\")"
  }
]
```

### Output Format

The script generates complex Boolean combinations:

```json
[
  {
    "Combination_title": "Broad Foundational Search",
    "boolean_combination": "(\"Foundation model\" OR \"Large language model\") AND (\"Machine Learning\" OR \"ML\") AND (\"Deep Learning\" OR \"Neural networks\")"
  },
  {
    "Combination_title": "Humanitarian & Social Impact Search", 
    "boolean_combination": "(\"Humanitarian\" OR \"Crisis response\") AND (\"Social Good\" OR \"Social impact\") AND (\"Vulnerable Populations\" OR \"At-risk groups\")"
  }
]
```
<p align="right">[<a href="#technical-report-top">back to top</a>]</p>

### Class Methods Reference

#### `__init__(boolean_combinations_file)`
**Purpose:** Initialize the generator with input file path  
**Parameters:** Path to boolean combinations JSON file  
**Default:** `'./data/boolean_combinations.json'`

#### `generate_all_unique_combinations()`
**Purpose:** Generate combinations for all predefined categories  
**Returns:** List of dictionaries with combination details  
**Output:** Console feedback with progress and warnings

#### `save_unique_combinations(combinations, output_file)`
**Purpose:** Save generated combinations to JSON file  
**Parameters:**
- `combinations`: List of generated combinations
- `output_file`: Output file path (default: `'./data/unique_boolean_combinations.json'`)

#### `display_available_keys()`
**Purpose:** Show all available keys from input file  
**Use Case:** Debugging and verification of available terms

#### `display_predefined_combinations()`
**Purpose:** Display all predefined category mappings  
**Use Case:** Understanding what categories and terms are configured

#### `update_predefined_combination(category, new_keys)`
**Purpose:** Modify predefined combinations for a category  
**Parameters:**
- `category`: Category name to update
- `new_keys`: List of new key terms for the category

<p align="right">[<a href="#technical-report-top">back to top</a>]</p>

### Processing Logic

The script follows this detailed process:

1. **Initialization:**
   - Load boolean combinations from input JSON
   - Initialize predefined category mappings
   - Verify input data integrity

2. **Category Processing:**
   - Iterate through each predefined research category
   - For each category, collect the specified key terms
   - Look up Boolean combinations for each key

3. **Combination Generation:**
   - Find matching Boolean expressions for each key
   - Track found and missing keys for reporting
   - Combine multiple Boolean expressions with AND operators
   - Handle single vs. multiple combination scenarios

4. **Quality Assurance:**
   - Report missing keys that couldn't be found
   - Count successful key matches per category
   - Provide detailed console feedback

5. **Output Generation:**
   - Clean combinations for final output
   - Save to JSON with proper formatting
   - Generate success/failure reports


<p align="right">[<a href="#technical-report-top">back to top</a>]</p>

### Usage 

#### Basic Usage
```python
from unique_boolean_combinations import generate_unique_boolean_combinations

# Generate with default paths
success = generate_unique_boolean_combinations()
```

#### Custom File Paths
```python
# Specify custom input and output files
success = generate_unique_boolean_combinations(
    input_file='./data/boolean_combinations.json',
    output_file='./output/unique_boolean_combinations.json'
)
```

#### Using the Class Directly
```python
from unique_boolean_combinations import UniqueBooleanCombinationsGenerator

# Create generator instance
generator = UniqueBooleanCombinationsGenerator('./data/boolean_combinations.json')

# Display available keys
generator.display_available_keys()

# Display predefined combinations
generator.display_predefined_combinations()

# Generate combinations
combinations = generator.generate_all_unique_combinations()

# Save results
generator.save_unique_combinations(combinations, './output/results.json')
```

#### Customizing Categories
```python
generator = UniqueBooleanCombinationsGenerator()

# Update a specific category
new_keys = ["Machine Learning", "Deep Learning", "Neural Networks"]
generator.update_predefined_combination("Broad Foundational Search", new_keys)

# Generate with updated configuration
combinations = generator.generate_all_unique_combinations()
```

#### Command Line Execution
```bash
python unique_boolean_combinations.py
```
<p align="right">[<a href="#technical-report-top">back to top</a>]</p>

### Error Handling & Feedback

The script provides comprehensive error handling:

#### File-Related Errors
- **Missing Input File:** Clear message if boolean combinations file doesn't exist
- **Invalid JSON:** Handles corrupted or malformed JSON input
- **Save Errors:** Reports issues when writing output file

#### Data-Related Warnings
- **Missing Keys:** Reports when predefined keys aren't found in input data
- **Empty Categories:** Handles categories with no valid combinations
- **Key Mismatches:** Detailed reporting of found vs. missing terms

#### Console Feedback
```
Generating unique boolean combinations...
==================================================

Processing: Broad Foundational Search
Keys: Foundation model, Machine Learning, Deep Learning
✓ Generated combination with 3 keys

Processing: Humanitarian & Social Impact Search  
Keys: Humanitarian & Crisis Response, Social Good & Impact
⚠ Missing keys: Social Good & Impact
✓ Generated combination with 1 keys

Generated 8 unique combinations
✓ Successfully saved to ./output/unique_boolean_combinations.json
```

### File Structure Requirements

```
CHITCHAT/
├── data/
│   └── boolean_combinations.json          # Input file (from previous script - boolean_combinations.py)
├── output/
│   └── unique_boolean_combinations.json   # Output file (generated)
└── src/
    └── boolean/
        └── unique_boolean_combinations.py
```

### Integration Workflow

This script is designed to work in sequence with `boolean_combinations.py`:

1. **Step 1:** Run `boolean_combinations.py` to generate basic Boolean combinations
2. **Step 2:** Run `unique_boolean_combinations.py` to create complex research-focused combinations
3. **Step 3:** Use the generated combinations in academic databases and search engines

<p align="right">[<a href="#technical-report-top">back to top</a>]</p>

### Customization Options

#### Adding New Categories
```python
# Add to predefined_combinations dictionary
"New Research Category": [
    "Key Term 1",
    "Key Term 2", 
    "Key Term 3"
]
```

#### Modifying Existing Categories
Use the `update_predefined_combination()` method or directly edit the predefined combinations dictionary.

#### Changing Combination Logic
The current implementation uses AND operators between different Boolean groups. This can be modified in the `_generate_combination_for_category()` method.

### Technical Notes

- **Encoding:** Full UTF-8 support for international characters
- **Logic:** Uses AND operators to combine different Boolean groups
- **Validation:** Comprehensive checking for missing keys and empty results
- **Performance:** Efficient lookup using dictionary mapping
- **Memory:** Loads all data in memory for fast processing


<p align="right">[<a href="#technical-report-top">back to top</a>]</p>

---

## ArXiv Paper Search Automation

### Overview
This script automates academic paper discovery by searching the arXiv repository using complex Boolean combinations. It transforms abstract search strategies into concrete research results, automatically retrieving relevant papers across multiple research categories with intelligent query optimization and duplicate filtering.

### Data Flow
```
../output/unique_boolean_combinations.json → Process → ../output/obtained_lit.json
```

**Input Directory:** `../output/`  
**Input Format:** JSON file with unique Boolean combinations by research category  
**Process:** Extract key terms, create arXiv queries, search API, filter duplicates  
**Output:** JSON file with comprehensive paper metadata and abstracts  
**Output Directory:** `../output/`  
**Output Format:** JSON with structured paper information

<p align="right">[<a href="#technical-report-top">back to top</a>]</p>

### Core Components

#### `ArxivPaperSearcher` Class

**Purpose:** Automated arXiv paper discovery engine that converts Boolean combinations into targeted searches.

**Key Features:**
- **Intelligent Query Generation:** Extracts key terms and creates optimized arXiv-specific queries
- **Category-Aware Searching:** Maps research categories to relevant arXiv subject classifications
- **Rate Limit Compliance:** Respects arXiv API guidelines (3-second delays)
- **Duplicate Filtering:** Prevents duplicate papers across different search strategies
- **Comprehensive Metadata Extraction:** Captures title, authors, year, abstract, and full text
- **Error Recovery:** Robust handling of network issues and malformed responses

### Search Strategy Architecture

#### 1. Key Term Extraction
**Process:** Intelligent parsing of complex Boolean combinations
- Extracts quoted terms from Boolean expressions
- Filters out common stop words and short terms
- Prioritizes domain-specific terminology
- Limits to 8 most relevant terms per combination

#### 2. Query Generation Strategies

##### Strategy 1: Individual Term Searches
- Focuses on the most important 2-4 terms
- Creates targeted searches for specific concepts
- Format: `all:"Foundation model"`

##### Strategy 2: Combined Term Searches  
- Combines related terms with AND operators
- Captures papers at intersection of concepts
- Format: `all:"Machine Learning" AND all:"Deep Learning"`

##### Strategy 3: Category-Based Searches
- Maps combination titles to arXiv categories
- Uses domain-specific search patterns
- Examples:
  - **AI/ML Categories:** `cat:cs.LG`, `cat:cs.AI`, `cat:stat.ML`
  - **Ethics Focus:** `all:"bias" OR all:"fairness"`
  - **Environmental:** `all:"sustainability" OR all:"energy consumption"`

#### 3. Category Mapping System

The script includes 16 specialized search mappings:

| Category | Search Focus | Example Queries |
|----------|--------------|-----------------|
| **Broad Foundational** | Core AI/ML concepts | `cat:cs.LG`, `cat:cs.AI` |
| **Humanitarian** | Crisis response | `all:"humanitarian"`, `all:"disaster relief"` |
| **Social Impact** | Ethics and society | `all:"social impact"`, `all:"ethics"` |
| **Inclusion** | Bias and fairness | `all:"bias" OR all:"fairness"` |
| **Safety** | Risk mitigation | `all:"safety" OR all:"security"` |
| **Privacy** | Data protection | `all:"privacy" OR all:"consent"` |
| **Environmental** | Sustainability | `all:"environmental" OR all:"sustainability"` |

<p align="right">[<a href="#technical-report-top">back to top</a>]</p>

### Input Format Requirements

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
<p align="right">[<a href="#technical-report-top">back to top</a>]</p>

### Output Format

The script generates comprehensive paper records:

```json
[
  {
    "title": "Large Language Models for Crisis Response: A Comprehensive Survey",
    "authors": "Smith, J., Johnson, M., Chen, L.",
    "url": "http://arxiv.org/abs/2023.12345",
    "abstract": "This paper presents a comprehensive survey of large language models...",
    "year": "2023",
    "extracted_text": "Full abstract text with cleaned formatting..."
  },
  {
    "title": "Ethical AI in Humanitarian Settings: Challenges and Opportunities", 
    "authors": "Brown, K., Davis, R.",
    "url": "http://arxiv.org/abs/2023.67890",
    "abstract": "We explore the ethical implications of deploying AI systems...",
    "year": "2023",
    "extracted_text": "Complete extracted abstract content..."
  }
]
```
<p align="right">[<a href="#technical-report-top">back to top</a>]</p>

### Class Methods Reference

#### `__init__(unique_combinations_file)`
**Purpose:** Initialize the searcher with input file path  
**Parameters:** Path to unique combinations JSON file  
**Default:** `'output/unique_boolean_combinations.json'`  
**Features:** Loads combinations and sets up rate limiting

#### `search_all_combinations(max_results_per_query)`
**Purpose:** Execute comprehensive search across all combinations  
**Parameters:**
- `max_results_per_query` (int): Maximum papers per query (default: 15)
**Returns:** List of dictionaries with paper metadata  
**Features:** Handles duplicate filtering and progress tracking

#### `save_results(papers, output_file)`
**Purpose:** Save search results with cleaned formatting  
**Parameters:**
- `papers`: List of paper dictionaries
- `output_file`: Output JSON file path
**Features:** Standardizes field names and removes internal tracking

#### `_extract_key_terms_from_boolean(boolean_combination)`
**Purpose:** Parse Boolean expressions to extract search terms  
**Process:**
- Uses regex to find quoted terms
- Filters stop words and short terms  
- Limits to 8 most relevant terms
- Removes duplicates and special characters

#### `_create_arxiv_queries(combination_title, key_terms)`
**Purpose:** Generate optimized arXiv-specific queries  
**Strategy:**
- Individual term searches for precision
- Combined searches for intersection discovery
- Category-based searches for domain coverage
- Limits to 4 queries per combination

#### `_search_arxiv(query, max_results)`
**Purpose:** Execute single arXiv API search  
**Features:**
- Handles XML response parsing
- Extracts comprehensive metadata
- Manages network errors gracefully
- Respects API rate limits

<p align="right">[<a href="#technical-report-top">back to top</a>]</p>

### Processing Workflow

The script follows this comprehensive process:

#### Phase 1: Initialization
1. **Load Combinations:** Read unique Boolean combinations from JSON
2. **Validate Input:** Check file format and content integrity
3. **Setup Tracking:** Initialize duplicate detection and logging

#### Phase 2: Query Generation
1. **Parse Boolean Logic:** Extract key terms from complex expressions
2. **Term Prioritization:** Rank terms by relevance and specificity
3. **Query Optimization:** Create multiple search strategies per combination
4. **Category Mapping:** Apply domain-specific search patterns

#### Phase 3: Search Execution
1. **Sequential Processing:** Handle each combination systematically
2. **Multi-Query Approach:** Execute multiple search strategies
3. **Rate Limit Management:** Enforce 3-second delays between requests
4. **Response Processing:** Parse XML and extract metadata

#### Phase 4: Result Management
1. **Duplicate Detection:** Filter papers by title comparison
2. **Metadata Enhancement:** Add search category information
3. **Quality Assurance:** Validate extracted information
4. **Progress Reporting:** Provide detailed console feedback

#### Phase 5: Output Generation
1. **Data Cleaning:** Standardize field names and formats
2. **JSON Generation:** Create well-structured output file
3. **Summary Statistics:** Generate category-wise paper counts
4. **Success Reporting:** Confirm completion and file locations

<p align="right">[<a href="#technical-report-top">back to top</a>]</p>

### Usage 

#### Basic Usage
```python
from arxiv_paper_search import search_arxiv_papers

# Search with default settings
success = search_arxiv_papers()
```

#### Custom File Paths
```python
# Specify custom input and output files
success = search_arxiv_papers(
    unique_combinations_file='./my_combinations.json',
    output_file='./results/papers.json'
)
```

#### Using the Class Directly
```python
from arxiv_paper_search import ArxivPaperSearcher

# Create searcher instance
searcher = ArxivPaperSearcher('./data/combinations.json')

# Execute comprehensive search
papers = searcher.search_all_combinations(max_results_per_query=25)

# Save results with custom filename
searcher.save_results(papers, './output/research_papers.json')
```

#### Advanced Configuration
```python
# Custom search with detailed control
searcher = ArxivPaperSearcher()
searcher.rate_limit_delay = 5  # Slower rate for cautious searching

# Search with higher result limits
papers = searcher.search_all_combinations(max_results_per_query=30)

# Process results
print(f"Found {len(papers)} unique papers")
for paper in papers[:5]:
    print(f"- {paper['title']} ({paper['year']})")
```

#### Command Line Execution
```bash
python arxiv_paper_search.py
```
<p align="right">[<a href="#technical-report-top">back to top</a>]</p>

### Error Handling & Recovery

#### Network-Related Errors
- **Connection Timeouts:** 30-second timeout with retry capability
- **Rate Limiting:** Automatic delay enforcement to prevent API blocks
- **HTTP Errors:** Graceful handling of 4xx/5xx responses
- **XML Parsing:** Robust handling of malformed API responses

#### Data-Related Errors
- **Missing Files:** Clear error messages for missing input files
- **Invalid JSON:** Comprehensive validation of input format
- **Empty Combinations:** Graceful skipping of invalid entries
- **Term Extraction Failures:** Fallback strategies for complex Boolean expressions

#### Console Output Examples
```
=== Starting Automated arXiv Paper Search ===
Processing 8 unique boolean combinations...

--- Processing 1/8: Broad Foundational Search ---
Extracted key terms: ['Foundation model', 'Machine Learning', 'Deep Learning']...
  Executing query: all:"Foundation model"
  Found 15 entries for query: all:"Foundation model"
  Executing query: all:"Machine Learning" AND all:"Deep Learning"
  Found 12 entries for query: all:"Machine Learning" AND all:"Deep Learning"
  Found 18 unique papers for Broad Foundational Search

=== Search Complete ===
Total unique papers found: 156
✓ Results saved to obtained_lit.json

Papers found by category:
  Broad Foundational Search: 18 papers
  Humanitarian & Social Impact Search: 12 papers
  Environmental & Infrastructural Cost: 25 papers
```

<p align="right">[<a href="#technical-report-top">back to top</a>]</p>

### API Compliance & Best Practices

#### ArXiv API Guidelines
- **Rate Limiting:** 3-second minimum delay between requests
- **Bulk Requests:** Maximum 50 results per query
- **User Agent:** Proper identification in requests
- **Error Handling:** Graceful degradation on failures

#### Search Optimization
- **Query Complexity:** Balance between precision and recall
- **Term Selection:** Prioritize domain-specific terminology
- **Category Usage:** Leverage arXiv subject classifications
- **Duplicate Prevention:** Efficient title-based deduplication

### File Structure Requirements

```
CHITCHAT/
├── output/
│   ├── unique_boolean_combinations.json   # Input file (# Input file - from previous script)
│   └── obtained_lit.json                  # Output (generated)
├── src/
│   └── api/
│       └── arxiv_paper_search.py
└── logs/
    └── arxiv_search.log                  # Optional logging
```

<p align="right">[<a href="#technical-report-top">back to top</a>]</p>

### Integration Workflow

This script completes the research automation pipeline:

1. **Step 1:** `boolean_combinations.py` - Generate basic Boolean combinations
2. **Step 2:** `unique_boolean_combinations.py` - Create research-focused combinations  
3. **Step 3:** `arxiv_paper_search.py` - Execute automated paper discovery
4. **Step 4:** Manual review and analysis of discovered papers

### Performance Considerations

#### Search Efficiency
- **Parallel Processing:** Sequential execution respects rate limits
- **Memory Usage:** Efficient streaming of search results
- **Network Optimization:** Connection reuse and timeout management
- **Duplicate Tracking:** In-memory set for fast duplicate detection

#### Scalability Factors
- **Combination Count:** Script handles dozens of research categories
- **Result Volume:** Capable of processing hundreds of papers
- **API Limits:** Respects arXiv's usage guidelines
- **Error Recovery:** Continues processing despite individual failures

<p align="right">[<a href="#technical-report-top">back to top</a>]</p>

### Customization Options

#### Query Strategy Modification
```python
# Modify category mappings in _create_arxiv_queries method
category_mappings = {
    "Custom Category": ['all:"custom term"', 'cat:cs.CR'],
    # Add your specific mappings
}
```

#### Rate Limit Adjustment
```python
# Modify delay for different use cases
searcher.rate_limit_delay = 5  # Slower for cautious use
searcher.rate_limit_delay = 1  # Faster for testing (use carefully)
```

#### Result Filtering
```python
# Add custom filters in search processing
def custom_filter(paper):
    year = int(paper.get('year', 0))
    return year >= 2020  # Only recent papers

# Apply during processing
filtered_papers = [p for p in papers if custom_filter(p)]
```

### Technical Implementation Notes

- **XML Processing:** Uses ElementTree for robust arXiv API response parsing
- **HTTP Handling:** Requests library with proper timeout and error handling  
- **Text Processing:** Comprehensive cleaning and normalization of extracted content
- **Logging:** Configurable logging levels for debugging and monitoring
- **Encoding:** Full UTF-8 support for international paper titles and authors
- **Memory Management:** Efficient processing of large result sets


<p align="right">[<a href="#technical-report-top">back to top</a>]</p>

---

## Multi-Repository Research Paper Web Scraper

### Overview
This script orchestrates automated paper discovery across multiple academic repositories including Google Scholar, OpenAlex, Europe PMC, and ArXiv. It transforms Boolean search combinations into a unified literature collection pipeline, automatically downloading papers, extracting full text, and aggregating results into a single comprehensive dataset.

<p align="right">[<a href="#technical-report-top">back to top</a>]</p>

### Data Flow
```
../output/unique_boolean_combinations.json → Process → ../output/obtained_lit.json
```

**Input Directory:** `../output/`  
**Input Format:** JSON file with unique Boolean combinations by research category  
**Process:** Multi-repository search, PDF download, text extraction, result aggregation  
**Output:** Comprehensive JSON database with full paper content and metadata  
**Output Directory:** `../output/`  
**Output Format:** JSON with unified paper records from all repositories

### Repository Integration Architecture

#### Supported Academic Repositories

| Repository | Coverage | Strengths | Search Method |
|------------|----------|-----------|---------------|
| **Google Scholar** | Broad academic coverage | Citation tracking, diverse sources | `scholarly` library with filtering |
| **OpenAlex** | Open access focus | Structured metadata, API reliability | REST API with cursor pagination |
| **Europe PMC** | Life sciences emphasis | Full-text access, medical literature | RESTful web services |
| **ArXiv** | Preprints and CS/Physics | Latest research, open access | Integration with existing arXiv module |

<p align="right">[<a href="#technical-report-top">back to top</a>]</p>

#### Core Processing Components

##### 1. Multi-Repository Search Engine
**Purpose:** Coordinates searches across all repositories using unified Boolean queries
- **Query Adaptation:** Transforms Boolean combinations for repository-specific formats
- **Rate Limiting:** Respects each repository's API guidelines
- **Error Recovery:** Continues processing if individual repositories fail
- **Result Standardization:** Normalizes data formats across different sources

##### 2. Intelligent PDF Download System
**Purpose:** Automated paper acquisition with fallback strategies
- **Direct PDF Detection:** Identifies PDF URLs from content headers
- **HTML Parsing:** Extracts PDF links from publisher pages using BeautifulSoup
- **Multi-Format Support:** Handles various publisher link formats (/pdf, /epdf)
- **Error Handling:** Graceful degradation when papers are behind paywalls

##### 3. Full-Text Extraction Engine  
**Purpose:** Converts downloaded PDFs to searchable text
- **Multi-Library Support:** Uses PyPDF2 and PyMuPDF for robust extraction
- **PDF Validation:** Checks PDF headers and repairs missing EOF markers
- **Error Recovery:** Handles corrupted or encrypted PDFs gracefully
- **Text Cleaning:** Normalizes extracted content for consistency

##### 4. Result Aggregation System
**Purpose:** Merges results from all repositories into unified format
- **Incremental Building:** Appends results progressively to avoid memory issues
- **Source Tracking:** Maintains repository attribution for each paper
- **Duplicate Handling:** Basic duplicate prevention across sources
- **Progress Monitoring:** Real-time feedback on collection progress

<p align="right">[<a href="#technical-report-top">back to top</a>]</p>

### Repository-Specific Implementation

#### Google Scholar Integration
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

#### OpenAlex Integration
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

#### Europe PMC Integration
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

#### ArXiv Integration
```python
def get_arxiv_results(path_to_unique_boolean_combinations)
```

**Features:**
- **Module Reuse:** Integrates existing ArXiv search functionality
- **Temporary File Handling:** Manages intermediate results efficiently
- **Error Recovery:** Graceful handling of import or execution failures
- **Result Standardization:** Converts ArXiv format to unified structure

### Input Format Requirements

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

<p align="right">[<a href="#technical-report-top">back to top</a>]</p>

### Output Format

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

<p align="right">[<a href="#technical-report-top">back to top</a>]</p>

### Core Functions Reference

#### `get_llit_papers(path_to_unique_boolean_combinations)`
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

#### `download_research_paper(url, save_dir)`
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

#### `extract_paper_text(research_paper_path)`
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

#### `append_results_to_json(output_file, new_results, source_name)`
**Purpose:** Incremental result aggregation  
**Features:**
- **File Creation:** Creates output file if it doesn't exist
- **Progressive Building:** Appends results without memory overload
- **Source Tracking:** Maintains attribution for debugging
- **Error Recovery:** Continues processing despite write failures

<p align="right">[<a href="#technical-report-top">back to top</a>]</p>

### Search Strategy Implementation

#### Query Processing Pipeline
1. **Boolean Combination Loading:** Read research category combinations
2. **Query Adaptation:** Transform Boolean logic for each repository
3. **Repository Sequencing:** Execute searches in optimal order
4. **Result Collection:** Gather papers with metadata extraction
5. **Text Processing:** Download and extract full content
6. **Aggregation:** Merge results into unified format

#### Quality Control Measures
- **Publication Year Filtering:** Focus on recent research (2020+)
- **Citation Threshold:** Prioritize impactful papers
- **Download Verification:** Ensure successful PDF acquisition
- **Text Extraction Validation:** Verify readable content extraction
- **Source Attribution:** Track which repository found each paper

#### Rate Limiting Strategy
- **Google Scholar:** Built-in delays in `scholarly` library
- **OpenAlex:** 1-second delays between requests
- **Europe PMC:** 1-second delays between requests  
- **ArXiv:** Handled by existing module (3-second delays)

<p align="right">[<a href="#technical-report-top">back to top</a>]</p>

### Usage

#### Basic Literature Collection
```python
from web_scrape import get_llit_papers

# Collect papers using all repositories
output_file = get_llit_papers('./output/unique_boolean_combinations.json')
print(f"Literature collection saved to: {output_file}")
```

#### Repository-Specific Search
```python
from web_scrape import search_repository

# Search specific repository
query = '"machine learning" AND "healthcare"'
results = search_repository(query, "openalex")
print(f"Found {len(results)} papers from OpenAlex")
```

#### Manual PDF Processing
```python
from web_scrape import download_research_paper, extract_paper_text

# Download and extract specific paper
paper_url = "https://example.com/paper.pdf"
pdf_path = download_research_paper(paper_url)
if pdf_path:
    text_content = extract_paper_text(pdf_path)
    print(f"Extracted {len(text_content)} characters")
```

#### Command Line Execution
```bash
python web_scrape.py ./output/unique_boolean_combinations.json
```
<p align="right">[<a href="#technical-report-top">back to top</a>]</p>

### Error Handling & Recovery

#### Network-Related Errors
- **Connection Timeouts:** Configurable timeouts for each repository
- **Rate Limiting:** Automatic delays and retry mechanisms  
- **Server Errors:** Graceful handling of 4xx/5xx responses
- **Repository Unavailability:** Continues with available sources

#### PDF Processing Errors
- **Download Failures:** Logs failures but continues processing
- **Corrupted PDFs:** Attempts repair before extraction
- **Paywall Detection:** Identifies and reports access restrictions
- **Format Issues:** Multiple extraction libraries as fallbacks

#### Data Processing Errors
- **Missing Metadata:** Handles incomplete paper records gracefully
- **Text Extraction Failures:** Reports issues but preserves other data
- **JSON Write Errors:** Maintains data integrity during aggregation
- **File System Issues:** Creates directories and handles permissions

#### Console Output Examples
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

<p align="right">[<a href="#technical-report-top">back to top</a>]</p>

### File Structure Requirements

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

<p align="right">[<a href="#technical-report-top">back to top</a>]</p>

### Dependencies & Requirements

#### Required Libraries
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

#### External API Dependencies
- **Google Scholar:** Via `scholarly` library (unofficial)
- **OpenAlex:** Official REST API (https://api.openalex.org/)
- **Europe PMC:** Official web services (https://europepmc.org/RestfulWebService)
- **ArXiv:** Integrated via existing module

<p align="right">[<a href="#technical-report-top">back to top</a>]</p>

### Performance Considerations

#### Memory Management
- **Incremental Processing:** Results appended progressively to avoid memory overload
- **Streaming Downloads:** PDF downloads use chunked streaming
- **Temporary File Cleanup:** Automatic cleanup of intermediate files
- **Result Aggregation:** JSON files updated incrementally

#### Processing Efficiency
- **Parallel Repository Access:** Sequential processing respects rate limits
- **Caching Strategy:** Downloaded PDFs stored for potential reuse
- **Error Recovery:** Failed downloads don't block other papers
- **Progress Tracking:** Real-time feedback on collection status

#### Scalability Factors
- **Result Volume:** Can handle thousands of papers per repository
- **Storage Requirements:** Downloaded PDFs require significant disk space
- **Processing Time:** Full-text extraction is time-intensive
- **API Limits:** Each repository has different rate limiting rules

### Integration Workflow

This script completes the comprehensive research automation pipeline:

1. **Step 1:** `boolean_combinations.py` - Generate basic Boolean combinations
2. **Step 2:** `unique_boolean_combinations.py` - Create research-focused combinations  
3. **Step 3:** `arxiv_paper_search.py` - Execute arXiv-specific searches
4. **Step 4:** `web_scrape.py` - **Comprehensive multi-repository collection**
5. **Step 5:** Manual analysis of comprehensive literature database

<p align="right">[<a href="#technical-report-top">back to top</a>]</p>

### Customization Options

#### Repository Configuration
```python
# Enable/disable specific repositories
def get_llit_papers(path_to_unique_boolean_combinations):
    # Customize repository selection
    search_google_scholar = True
    search_openalex = True  
    search_europepmc = True
    search_arxiv = True
```

#### Quality Filters
```python
# Modify paper quality criteria
google_scholar_results = search_google_scholar_scholarly(
    query=unique_combinations,
    pub_year=2018,  # Change minimum year
    num_citations=5  # Require minimum citations
)
```

#### Download Configuration
```python
# Customize PDF download behavior
download_research_paper(
    url=paper_url,
    save_dir="custom_downloads"  # Custom storage location
)
```

### Technical Implementation Notes

- **Multi-Format PDF Support:** Handles various publisher PDF formats and protection schemes
- **Abstract Reconstruction:** Rebuilds abstracts from OpenAlex inverted indexes
- **Publisher Compatibility:** Generic PDF extraction works across major publishers
- **Error Resilience:** Continues processing despite individual paper failures
- **Result Standardization:** Normalizes metadata formats across repositories
- **Progress Monitoring:** Comprehensive logging for debugging and monitoring


<p align="right">[<a href="#technical-report-top">back to top</a>]</p>

---

## Research Paper Screening

### Overview
This script transforms large collections of research papers into prioritized, systematically evaluated datasets using OpenAI's structured output capabilities. It performs comprehensive multi-dimensional analysis including publication quality assessment, technical scope evaluation, ethical framework analysis, and humanitarian principle scoring to automatically prioritize papers for systematic literature reviews.

### Data Flow
```
../output/obtained_lit.json → Process → ../output/screening_results_TIMESTAMP.jsonl
```

**Input Directory:** `../output/`  
**Input Format:** JSON file with comprehensive paper metadata and full text  
**Process:** AI-powered structured screening with multi-phase evaluation  
**Output:** JSONL file with detailed screening results and priority classifications  
**Output Directory:** `../output/`  
**Output Format:** JSONL with structured screening assessments per paper

<p align="right">[<a href="#technical-report-top">back to top</a>]</p>

### AI-Powered Assessment Architecture

#### Evaluation Framework Structure

The system employs a **three-phase assessment model** using structured Pydantic models for consistent evaluation:

##### Phase 1: Publication Quality & Technical Scope
- **Publication Quality Assessment:** Venue ranking, citation analysis, recency evaluation
- **Technical Scope Evaluation:** Relevance to LLM data collection and NLP corpus creation

##### Phase 2: Ethical & Humanitarian Analysis  
- **Ethical Flag Detection:** Identifies papers with ethical concerns or omissions
- **Humanitarian Principles Scoring:** Quantitative assessment against humanitarian principles

##### Phase 3: Contribution Analysis
- **Methodology Contributions:** Novel approaches and reproducible implementations
- **Ethical Contributions:** Framework development and bias analysis

<p align="right">[<a href="#technical-report-top">back to top</a>]</p>

#### Structured Assessment Models

##### `PublicationQuality` Model
```python
class PublicationQuality(BaseModel):
    venue_name: str                    # Publication venue identification
    is_top_tier_venue: bool           # Q1/Q2 journal or top-tier conference
    publication_year: int             # Publication year
    citation_count: int               # Citation metrics
    is_recent_promising: bool         # Recent papers with promise indicators
    full_text_english: bool           # Accessibility and language verification
```

##### `TechnicalScope` Model  
```python
class TechnicalScope(BaseModel):
    addresses_llm_data_collection: bool      # LLM training data focus
    addresses_text_corpus_creation: bool     # Text corpus development
    addresses_web_scraping_nlp: bool         # Web scraping for NLP datasets
    addresses_multilingual_compilation: bool # Multilingual dataset work
```

##### `HumanitarianPrinciples` Model
```python
class HumanitarianPrinciples(BaseModel):
    humanity_score: int      # Harm prevention (0-3 scale)
    impartiality_score: int  # Fair representation (0-3 scale)  
    independence_score: int  # Autonomy from bias (0-3 scale)
    neutrality_score: int    # Non-discriminatory practices (0-3 scale)
```

##### `EthicalFlags` Model
```python
class EthicalFlags(BaseModel):
    focuses_only_on_performance: bool     # Ethics discussion presence
    disregards_ethical_principles: bool   # Consent/privacy violations
    missing_ethical_approval: bool        # IRB approval for vulnerable groups
    violates_humanitarian_principles: bool # Discriminatory or military intent
```

##### `MethodologyContributions` Model
```python
class MethodologyContributions(BaseModel):
    novel_methodology: bool           # Novel data collection methods
    systematic_evaluation: bool       # Comparative analysis presence
    reproducible_implementation: bool # Implementation detail adequacy
```

##### `EthicalContributions` Model
```python
class EthicalContributions(BaseModel):
    explicit_framework: bool          # Ethical framework inclusion
    empirical_bias_analysis: bool     # Bias analysis in data
    harm_mitigation_strategies: bool  # Concrete mitigation proposals
    policy_recommendations: bool      # Data governance recommendations
    acknowledges_tensions: bool       # Ethical trade-off discussion
```

<p align="right">[<a href="#technical-report-top">back to top</a>]</p>

### Priority Classification System

#### `PriorityLevel` Enumeration
```python
class PriorityLevel(str, Enum):
    HIGH = "HIGH PRIORITY"      # Critical papers for inclusion
    MEDIUM = "MEDIUM PRIORITY"  # Important supporting papers
    LOW = "LOW PRIORITY"        # Tangentially relevant papers
    EXCLUDE = "EXCLUDE"         # Papers failing inclusion criteria
```

#### Priority Assignment Logic
The AI model synthesizes all assessment dimensions to assign final priority levels based on:
- **Publication Quality:** Top-tier venues and high citation counts increase priority
- **Technical Relevance:** Direct address of LLM data collection raises priority
- **Ethical Framework:** Comprehensive ethical analysis increases priority
- **Humanitarian Alignment:** High humanitarian principle scores boost priority
- **Methodological Innovation:** Novel approaches and reproducibility enhance priority

<p align="right">[<a href="#technical-report-top">back to top</a>]</p>

### Input Format Requirements

The script expects comprehensive paper records from `web_scrape.py`:

```json
[
  {
    "title": "Ethical Data Collection for Large Language Model Training",
    "authors": "Smith, J., Johnson, M., Chen, L.",
    "url": "https://example.com/paper1",
    "abstract": "This paper presents a comprehensive framework for ethical data collection...",
    "year": "2023",
    "extracted_text": "Complete full-text content including methodology, results, ethical considerations, and detailed implementation guidelines..."
  }
]
```

**Required Fields:**
- `title`: Paper title for identification
- `year`: Publication year for filtering (>= 2020)
- `extracted_text`: Full text content for analysis (>= 500 characters)
- `authors`, `url`: Metadata for tracking and reference

<p align="right">[<a href="#technical-report-top">back to top</a>]</p>

### Output Format

The script generates detailed structured assessments in JSONL format:

```json
{
  "title": "Ethical Data Collection for Large Language Model Training",
  "original_metadata": {
    "authors": "Smith, J., Johnson, M., Chen, L.",
    "year": "2023",
    "url": "https://example.com/paper1"
  },
  "screening_results": {
    "paper_title": "Ethical Data Collection for Large Language Model Training",
    "publication_quality": {
      "venue_name": "Nature Machine Intelligence",
      "is_top_tier_venue": true,
      "publication_year": 2023,
      "citation_count": 45,
      "is_recent_promising": true,
      "full_text_english": true
    },
    "technical_scope": {
      "addresses_llm_data_collection": true,
      "addresses_text_corpus_creation": true,
      "addresses_web_scraping_nlp": false,
      "addresses_multilingual_compilation": true
    },
    "ethical_flags": {
      "focuses_only_on_performance": false,
      "disregards_ethical_principles": false,
      "missing_ethical_approval": false,
      "violates_humanitarian_principles": false
    },
    "humanitarian_principles": {
      "humanity_score": 3,
      "impartiality_score": 2,
      "independence_score": 2,
      "neutrality_score": 3
    },
    "methodology_contributions": {
      "novel_methodology": true,
      "systematic_evaluation": true,
      "reproducible_implementation": true
    },
    "ethical_contributions": {
      "explicit_framework": true,
      "empirical_bias_analysis": true,
      "harm_mitigation_strategies": true,
      "policy_recommendations": true,
      "acknowledges_tensions": true
    },
    "priority_level": "HIGH PRIORITY"
  },
  "final_priority": "HIGH PRIORITY"
}
```

<p align="right">[<a href="#technical-report-top">back to top</a>]</p>

### Core Functions Reference

#### `main()`
**Purpose:** Primary orchestration function for paper screening workflow
**Process:**
1. **Command Line Validation:** Verify prompt file and paper collection exist
2. **API Setup:** Initialize OpenAI client with structured output capability
3. **Data Loading:** Load papers and screening prompts
4. **Duplicate Prevention:** Track previously processed papers across sessions
5. **Quality Filtering:** Apply year and content length filters
6. **AI Screening:** Execute structured assessments for each paper
7. **Result Persistence:** Save assessments immediately to prevent data loss

#### `screen_paper(client, prompt_text, paper)`
**Purpose:** Execute AI-powered structured paper assessment
**Features:**
- **Content Preparation:** Formats paper data for AI analysis
- **Text Truncation:** Limits content to 60,000 characters for cost control
- **Structured Output:** Uses OpenAI's beta structured output feature
- **Error Handling:** Comprehensive exception management

**Parameters:**
- `client` (OpenAI): Initialized OpenAI client
- `prompt_text` (str): Loaded screening prompt
- `paper` (Dict): Paper data with full text content

**Returns:** 
- `PaperScreening`: Complete structured assessment

#### `load_processed_ids(output_dir)`
**Purpose:** Prevent duplicate processing across multiple runs
**Features:**
- **Cross-Session Tracking:** Reads all previous JSONL output files
- **Unique ID Generation:** Creates consistent identifiers from paper titles
- **Directory Management:** Creates output directories if missing

**Returns:** Set of processed paper IDs for duplicate detection

#### `append_screening_result(screening, paper, output_file)`
**Purpose:** Immediate result persistence to prevent data loss
**Features:**
- **JSONL Format:** Appends single line per paper for streaming processing
- **Complete Record:** Includes original metadata and full screening results
- **Atomic Writes:** Each paper saved immediately after processing

#### `create_unique_id(title)`
**Purpose:** Generate consistent identifiers for duplicate detection
**Process:**
- Convert title to lowercase
- Remove non-alphanumeric characters
- Create reproducible hash from cleaned title

#### `debug_jsonl_structure(output_dir)`
**Purpose:** Development utility for inspecting output file structure
**Features:**
- **File Discovery:** Finds all screening result files
- **Structure Inspection:** Analyzes JSONL file formats
- **Count Reporting:** Provides entry counts per file

<p align="right">[<a href="#technical-report-top">back to top</a>]</p>

### Processing Workflow

#### Phase 1: Initialization & Validation
1. **Command Line Processing:** Validate prompt and paper file arguments
2. **File Existence Verification:** Check all required files are accessible
3. **API Key Validation:** Verify OpenAI API credentials
4. **Output Directory Setup:** Create necessary directories

#### Phase 2: Data Loading & Filtering  
1. **Prompt Loading:** Read screening prompt from external file
2. **Paper Collection Loading:** Load comprehensive paper dataset
3. **Duplicate Detection:** Identify previously processed papers
4. **Quality Filtering:** Apply year (>=2020) and content length (>=500 chars) filters

#### Phase 3: AI-Powered Assessment
1. **Paper Preparation:** Format content for AI analysis with truncation
2. **Structured Screening:** Execute multi-dimensional assessment via OpenAI
3. **Result Validation:** Ensure complete structured response
4. **Immediate Persistence:** Save results to prevent data loss

#### Phase 4: Progress Tracking & Reporting
1. **Real-Time Feedback:** Progress bars and status updates
2. **Error Logging:** Detailed error reporting and recovery
3. **Statistics Tracking:** Count successful, failed, and filtered papers
4. **Final Summary:** Comprehensive processing report

<p align="right">[<a href="#technical-report-top">back to top</a>]</p>

### Quality Control & Filtering

#### Pre-Processing Filters
- **Publication Year:** Only papers from 2020 onwards
- **Content Length:** Minimum 500 characters of extracted text
- **Language:** Full text must be in English
- **Duplicate Detection:** Cross-session duplicate prevention

#### AI Assessment Quality
- **Structured Output:** Ensures consistent assessment format
- **Multi-Dimensional Analysis:** Comprehensive evaluation across multiple criteria
- **Quantitative Scoring:** Numerical scores for humanitarian principles
- **Binary Flags:** Clear yes/no assessments for critical factors

#### Post-Processing Validation
- **Completeness Checks:** Verify all assessment fields populated
- **Consistency Validation:** Ensure logical consistency across assessments
- **Priority Logic:** Validate priority assignments match assessment patterns

<p align="right">[<a href="#technical-report-top">back to top</a>]</p>

### Usage 

#### Basic Screening
```bash
# Screen papers using provided prompt
python screen_papers.py screening_prompt.txt obtained_lit.json
```

#### Custom Configuration
```python
from screen_papers import screen_paper, load_papers_from_json
from openai import OpenAI

# Initialize client
client = OpenAI(api_key="your-api-key")

# Load data
papers = load_papers_from_json("papers.json")
prompt = "Your screening prompt here..."

# Screen individual paper
for paper in papers:
    result = screen_paper(client, prompt, paper)
    print(f"Priority: {result.priority_level}")
```

#### Batch Processing with Custom Filters
```python
# Custom filtering logic
def custom_filter(paper):
    year = int(paper.get('year', 0))
    text_length = len(paper.get('extracted_text', ''))
    return year >= 2021 and text_length >= 1000  # Stricter criteria

# Apply custom filtering
filtered_papers = [p for p in papers if custom_filter(p)]
```

<p align="right">[<a href="#technical-report-top">back to top</a>]</p>

### Error Handling & Recovery

#### Network & API Errors
- **Rate Limiting:** Automatic retry logic for API limits
- **Connection Failures:** Graceful handling of network issues
- **Authentication Errors:** Clear error messages for API key issues
- **Model Availability:** Fallback strategies for model unavailability

#### Data Processing Errors
- **Malformed Papers:** Skip papers with missing required fields
- **Text Encoding Issues:** UTF-8 handling for international content
- **JSON Parsing Errors:** Robust handling of malformed input data
- **File System Errors:** Directory creation and permission handling

#### AI Assessment Errors
- **Incomplete Responses:** Validation of structured output completeness
- **Model Errors:** Comprehensive exception handling for API failures
- **Content Length Issues:** Automatic truncation for oversized papers
- **Prompt Injection:** Safe handling of paper content in prompts

#### Console Output Examples
```
Loading prompt...
Loading papers from JSON...
Loaded 1247 papers from obtained_lit.json
Results will be saved to: output/screening_results_20231201_143022.jsonl

Loading previously processed papers...
Found 342 previously processed papers

Start screening 1247 papers...
Processing: 100%|████████████| 905/905 [2:34:17<00:00, 10.25s/it]

==================================================
SCREENING COMPLETE
==================================================
Successfully screened: 847/1247 papers
Skipped (year filters): 156 papers
Skipped (text filters): 89 papers
Skipped (duplicates): 155 papers

All results saved to: output/screening_results_20231201_143022.jsonl
```

### File Structure Requirements

```
CHITCHAT
├── docs/
│   └── prompt/
│       └── paper_screening_prompt.txt           # AI screening instructions
├── output/
│   ├── obtained_lit.json                        # Input (from web_scrape.py)
│   ├── screening_results_20231201_143022.jsonl  # Output (timestamped)
│   ├── screening_results_20231202_091534.jsonl  # Additional runs
│   └── ...
├── src/
│   └── screen_papers.py
└── logs/                                        # Optional logging
    └── screening.log
```

<p align="right">[<a href="#technical-report-top">back to top</a>]</p>

### OpenAI Integration

#### Structured Output Configuration
```python
completion = client.beta.chat.completions.parse(
    model="gpt-5",              # High-capability model for analysis
    messages=[
        {
            "role": "system", 
            "content": "Expert research paper screener providing objective assessments"
        },
        {
            "role": "user",
            "content": full_prompt
        }
    ],
    response_format=PaperScreening,   # Structured Pydantic model
    temperature=0.3                   # Low temperature for consistency
)
```

#### Cost Management Strategies
- **Text Truncation:** 60,000 character limit per paper
- **Efficient Prompting:** Focused prompts minimize token usage
- **Batch Processing:** Process papers sequentially to avoid rate limits
- **Incremental Saving:** Immediate result persistence prevents re-processing


<p align="right">[<a href="#technical-report-top">back to top</a>]</p>

---

## Integration Workflow

This script completes the research automation pipeline:

1. **Step 1:** `boolean_combinations.py` - Generate basic Boolean combinations
2. **Step 2:** `unique_boolean_combinations.py` - Create research-focused combinations  
3. **Step 3:** `arxiv_paper_search.py` - Execute arXiv-specific searches
4. **Step 4:** `web_scrape.py` - multi-repository collection
5. **Step 5:** `screen_papers.py` - **AI-based systematic screening and prioritization**

<p align="right">[<a href="#technical-report-top">back to top</a>]</p>

### Performance Considerations

#### Processing Efficiency
- **Incremental Processing:** Results saved immediately to prevent data loss
- **Duplicate Prevention:** Efficient cross-session tracking prevents re-processing
- **Memory Management:** Streaming processing avoids memory overload
- **Progress Tracking:** Real-time feedback with progress bars

#### Cost Optimization
- **Text Truncation:** Limits API costs while preserving content quality
- **Quality Pre-Filtering:** Reduces API calls on low-quality papers
- **Efficient Prompting:** Optimized prompts minimize token usage
- **Structured Output:** Eliminates parsing overhead and errors

#### Scalability Factors
- **Large Collections:** Handles thousands of papers efficiently  
- **Cross-Session Processing:** Resume capability for long-running tasks
- **Error Recovery:** Continues processing despite individual failures
- **Parallel Processing:** Sequential processing respects API rate limits

<p align="right">[<a href="#technical-report-top">back to top</a>]</p>

### Customization Options

#### Assessment Criteria Modification
```python
# Modify Pydantic models to add new assessment dimensions
class CustomTechnicalScope(TechnicalScope):
    addresses_domain_specific_data: bool = Field(description="Domain-specific focus")
    uses_synthetic_data: bool = Field(description="Synthetic data generation")
```

#### Priority Logic Customization
```python
# Custom priority assignment based on specific research needs
def custom_priority_logic(screening: PaperScreening) -> PriorityLevel:
    if screening.technical_scope.addresses_llm_data_collection:
        if screening.humanitarian_principles.humanity_score >= 2:
            return PriorityLevel.HIGH
    return PriorityLevel.MEDIUM
```

#### Filtering Criteria Adjustment
```python
# Modify filtering thresholds
MIN_YEAR = 2021              # More recent papers only
MIN_TEXT_LENGTH = 1000       # Longer papers only
MIN_CITATION_COUNT = 5       # Higher impact papers only
```

### Technical Implementation Notes

- **Pydantic Validation:** Ensures structured output consistency and type safety
- **JSONL Format:** Enables streaming processing and easy data manipulation
- **UTF-8 Encoding:** Full international character support
- **Error Resilience:** Comprehensive exception handling prevents data loss
- **API Integration:** Beta structured output features for reliable parsing
- **Cross-Platform:** Works on Windows, macOS, and Linux environments

<p align="right">[<a href="#technical-report-top">back to top</a>]</p>

---

# Running

---

## Shell Scripts

---

## Running Locally

---

## Running on RCP
### Setting up RCP
Before setting up the RCP, contact the project lead to be added to the RCP(Research Computing Platform).
[Click here to learn about setting up RCP](https://github.com/MichelDucartier/rcp-docker-images/blob/master/LIGHT_README.md)

### Run as an RCP job
1. Run the `web_scrape.sh` or `screen_papers.sh` script from RCP.
2. The script to run the `web_scrape.sh` script on RCP looks like this (change USER):
```
runai submit \
  --name paper-scraping \
  --image registry.rcp.epfl.ch/multimeditron/basic:latest-USER \
  --pvc light-scratch:/mloscratch \ # <- CAN ALSO BE LIGHTSCRATCH
  --large-shm \
  -e NAS_HOME=/mloscratch/users/USER \
  -e HF_API_KEY_FILE_AT=/mloscratch/users/USER/keys/hf_key.txt \
  -e WANDB_API_KEY_FILE_AT=/mloscratch/users/USER/keys/wandb_key.txt \
  -e GITCONFIG_AT=/mloscratch/users/USER/.gitconfig \
  -e GIT_CREDENTIALS_AT=/mloscratch/users/USER/.git-credentials \
  -e VSCODE_CONFIG_AT=/mloscratch/users/USER/.vscode-server \
  --backoff-limit 0 \
  --run-as-gid 84257 \
  --gpu 0 \
  --command -- "/mloscratch/users/USER/CHITCHAT/web_scrape.sh" \
                "/mloscratch/users/USER/CHITCHAT/output/unique_boolean_combinations.json"
```
3. For `screen_papers.sh` you need to add a file `openai_key.txt` with an openai api key.

## Run using the command line
1. Add OpenAI API key with `export OPENAI_API_KEY="your-api-key-here"`
2. Run the script with `python3 screen_papers.py path/to/paper_screening_prompt.txt path/to/papers.json`

<p align="right">[<a href="#technical-report-top">back to top</a>]</p>

---

# Script Breakdown

<p align="right">[<a href="#technical-report-top">back to top</a>]</p>

---

# Contributing

We welcome contributions!❤️ 

If you're part of the main project team, kindly reach out to **David**, **Tim**, or **Fiifi** to join the Slack channel.  

## How to Contribute
1. **Check Issues**  
   - Review the [GitHub Issues](./issues) and pick one you'd like to work on.  
   - If you encounter a new problem, [open a new issue](./issues/new) with clear details.  

2. **Get Approval**  
   - Wait for project maintainers to approve or assign the issue before starting.  

3. **Make Changes**  
   - Fork the repository.  
   - Create a new branch for your changes.  
   - Implement and test your fix or feature.  

4. **Submit a Pull Request (PR)**  
   - Open a PR describing the problem and your solution.  
   - Link the related issue in your PR description.  

**Notes** 
- PRs should be small, focused, and easy to review.  
- Communication is encouraged—ask questions on Slack if you're unsure.  
<p align="right">[<a href="#technical-report-top">back to top</a>]</p>