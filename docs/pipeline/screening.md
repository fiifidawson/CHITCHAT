---
title: Stage 5 — LLM-assisted screening
---

# Research Paper Screening

## Overview
This script transforms large collections of research papers into prioritized, systematically evaluated datasets using OpenAI's structured output capabilities. It performs comprehensive multi-dimensional analysis including publication quality assessment, technical scope evaluation, ethical framework analysis, and humanitarian principle scoring to automatically prioritize papers for systematic literature reviews.

## Data Flow
```
../output/obtained_lit.json → Process → ../output/screening_results_TIMESTAMP.jsonl
```

**Input Directory:** `../output/`  
**Input Format:** JSON file with comprehensive paper metadata and full text  
**Process:** AI-powered structured screening with multi-phase evaluation  
**Output:** JSONL file with detailed screening results and priority classifications  
**Output Directory:** `../output/`  
**Output Format:** JSONL with structured screening assessments per paper

## AI-Powered Assessment Architecture

### Evaluation Framework Structure

The system employs a **three-phase assessment model** using structured Pydantic models for consistent evaluation:

#### Phase 1: Publication Quality & Technical Scope
- **Publication Quality Assessment:** Venue ranking, citation analysis, recency evaluation
- **Technical Scope Evaluation:** Relevance to LLM data collection and NLP corpus creation

#### Phase 2: Ethical & Humanitarian Analysis  
- **Ethical Flag Detection:** Identifies papers with ethical concerns or omissions
- **Humanitarian Principles Scoring:** Quantitative assessment against humanitarian principles

#### Phase 3: Contribution Analysis
- **Methodology Contributions:** Novel approaches and reproducible implementations
- **Ethical Contributions:** Framework development and bias analysis

### Structured Assessment Models

#### `PublicationQuality` Model
```python
class PublicationQuality(BaseModel):
    venue_name: str                    # Publication venue identification
    is_top_tier_venue: bool           # Q1/Q2 journal or top-tier conference
    publication_year: int             # Publication year
    citation_count: int               # Citation metrics
    is_recent_promising: bool         # Recent papers with promise indicators
    full_text_english: bool           # Accessibility and language verification
```

#### `TechnicalScope` Model  
```python
class TechnicalScope(BaseModel):
    addresses_llm_data_collection: bool      # LLM training data focus
    addresses_text_corpus_creation: bool     # Text corpus development
    addresses_web_scraping_nlp: bool         # Web scraping for NLP datasets
    addresses_multilingual_compilation: bool # Multilingual dataset work
```

#### `HumanitarianPrinciples` Model
```python
class HumanitarianPrinciples(BaseModel):
    humanity_score: int      # Harm prevention (0-3 scale)
    impartiality_score: int  # Fair representation (0-3 scale)  
    independence_score: int  # Autonomy from bias (0-3 scale)
    neutrality_score: int    # Non-discriminatory practices (0-3 scale)
```

#### `EthicalFlags` Model
```python
class EthicalFlags(BaseModel):
    focuses_only_on_performance: bool     # Ethics discussion presence
    disregards_ethical_principles: bool   # Consent/privacy violations
    missing_ethical_approval: bool        # IRB approval for vulnerable groups
    violates_humanitarian_principles: bool # Discriminatory or military intent
```

#### `MethodologyContributions` Model
```python
class MethodologyContributions(BaseModel):
    novel_methodology: bool           # Novel data collection methods
    systematic_evaluation: bool       # Comparative analysis presence
    reproducible_implementation: bool # Implementation detail adequacy
```

#### `EthicalContributions` Model
```python
class EthicalContributions(BaseModel):
    explicit_framework: bool          # Ethical framework inclusion
    empirical_bias_analysis: bool     # Bias analysis in data
    harm_mitigation_strategies: bool  # Concrete mitigation proposals
    policy_recommendations: bool      # Data governance recommendations
    acknowledges_tensions: bool       # Ethical trade-off discussion
```

## Priority Classification System

### `PriorityLevel` Enumeration
```python
class PriorityLevel(str, Enum):
    HIGH = "HIGH PRIORITY"      # Critical papers for inclusion
    MEDIUM = "MEDIUM PRIORITY"  # Important supporting papers
    LOW = "LOW PRIORITY"        # Tangentially relevant papers
    EXCLUDE = "EXCLUDE"         # Papers failing inclusion criteria
```

### Priority Assignment Logic
The AI model synthesizes all assessment dimensions to assign final priority levels based on:
- **Publication Quality:** Top-tier venues and high citation counts increase priority
- **Technical Relevance:** Direct address of LLM data collection raises priority
- **Ethical Framework:** Comprehensive ethical analysis increases priority
- **Humanitarian Alignment:** High humanitarian principle scores boost priority
- **Methodological Innovation:** Novel approaches and reproducibility enhance priority

## Input Format Requirements

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

## Output Format

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

## Core Functions Reference

### `main()`
**Purpose:** Primary orchestration function for paper screening workflow
**Process:**
1. **Command Line Validation:** Verify prompt file and paper collection exist
2. **API Setup:** Initialize OpenAI client with structured output capability
3. **Data Loading:** Load papers and screening prompts
4. **Duplicate Prevention:** Track previously processed papers across sessions
5. **Quality Filtering:** Apply year and content length filters
6. **AI Screening:** Execute structured assessments for each paper
7. **Result Persistence:** Save assessments immediately to prevent data loss

### `screen_paper(client, prompt_text, paper)`
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

### `load_processed_ids(output_dir)`
**Purpose:** Prevent duplicate processing across multiple runs
**Features:**
- **Cross-Session Tracking:** Reads all previous JSONL output files
- **Unique ID Generation:** Creates consistent identifiers from paper titles
- **Directory Management:** Creates output directories if missing

**Returns:** Set of processed paper IDs for duplicate detection

### `append_screening_result(screening, paper, output_file)`
**Purpose:** Immediate result persistence to prevent data loss
**Features:**
- **JSONL Format:** Appends single line per paper for streaming processing
- **Complete Record:** Includes original metadata and full screening results
- **Atomic Writes:** Each paper saved immediately after processing

### `create_unique_id(title)`
**Purpose:** Generate consistent identifiers for duplicate detection
**Process:**
- Convert title to lowercase
- Remove non-alphanumeric characters
- Create reproducible hash from cleaned title

### `debug_jsonl_structure(output_dir)`
**Purpose:** Development utility for inspecting output file structure
**Features:**
- **File Discovery:** Finds all screening result files
- **Structure Inspection:** Analyzes JSONL file formats
- **Count Reporting:** Provides entry counts per file

## Processing Workflow

### Phase 1: Initialization & Validation
1. **Command Line Processing:** Validate prompt and paper file arguments
2. **File Existence Verification:** Check all required files are accessible
3. **API Key Validation:** Verify OpenAI API credentials
4. **Output Directory Setup:** Create necessary directories

### Phase 2: Data Loading & Filtering  
1. **Prompt Loading:** Read screening prompt from external file
2. **Paper Collection Loading:** Load comprehensive paper dataset
3. **Duplicate Detection:** Identify previously processed papers
4. **Quality Filtering:** Apply year (>=2020) and content length (>=500 chars) filters

### Phase 3: AI-Powered Assessment
1. **Paper Preparation:** Format content for AI analysis with truncation
2. **Structured Screening:** Execute multi-dimensional assessment via OpenAI
3. **Result Validation:** Ensure complete structured response
4. **Immediate Persistence:** Save results to prevent data loss

### Phase 4: Progress Tracking & Reporting
1. **Real-Time Feedback:** Progress bars and status updates
2. **Error Logging:** Detailed error reporting and recovery
3. **Statistics Tracking:** Count successful, failed, and filtered papers
4. **Final Summary:** Comprehensive processing report

## Quality Control & Filtering

### Pre-Processing Filters
- **Publication Year:** Only papers from 2020 onwards
- **Content Length:** Minimum 500 characters of extracted text
- **Language:** Full text must be in English
- **Duplicate Detection:** Cross-session duplicate prevention

### AI Assessment Quality
- **Structured Output:** Ensures consistent assessment format
- **Multi-Dimensional Analysis:** Comprehensive evaluation across multiple criteria
- **Quantitative Scoring:** Numerical scores for humanitarian principles
- **Binary Flags:** Clear yes/no assessments for critical factors

### Post-Processing Validation
- **Completeness Checks:** Verify all assessment fields populated
- **Consistency Validation:** Ensure logical consistency across assessments
- **Priority Logic:** Validate priority assignments match assessment patterns

## Usage 

### Basic Screening
```bash
# Screen papers using provided prompt
python screen_papers.py screening_prompt.txt obtained_lit.json
```

### Custom Configuration
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

### Batch Processing with Custom Filters
```python
# Custom filtering logic
def custom_filter(paper):
    year = int(paper.get('year', 0))
    text_length = len(paper.get('extracted_text', ''))
    return year >= 2021 and text_length >= 1000  # Stricter criteria

# Apply custom filtering
filtered_papers = [p for p in papers if custom_filter(p)]
```

## Error Handling & Recovery

### Network & API Errors
- **Rate Limiting:** Automatic retry logic for API limits
- **Connection Failures:** Graceful handling of network issues
- **Authentication Errors:** Clear error messages for API key issues
- **Model Availability:** Fallback strategies for model unavailability

### Data Processing Errors
- **Malformed Papers:** Skip papers with missing required fields
- **Text Encoding Issues:** UTF-8 handling for international content
- **JSON Parsing Errors:** Robust handling of malformed input data
- **File System Errors:** Directory creation and permission handling

### AI Assessment Errors
- **Incomplete Responses:** Validation of structured output completeness
- **Model Errors:** Comprehensive exception handling for API failures
- **Content Length Issues:** Automatic truncation for oversized papers
- **Prompt Injection:** Safe handling of paper content in prompts

### Console Output Examples
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

## File Structure Requirements

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

## OpenAI Integration

### Structured Output Configuration
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

### Cost Management Strategies
- **Text Truncation:** 60,000 character limit per paper
- **Efficient Prompting:** Focused prompts minimize token usage
- **Batch Processing:** Process papers sequentially to avoid rate limits
- **Incremental Saving:** Immediate result persistence prevents re-processing

## Integration Workflow

This script completes the research automation pipeline:

1. **Step 1:** `boolean_combinations.py` - Generate basic Boolean combinations
2. **Step 2:** `unique_boolean_combinations.py` - Create research-focused combinations  
3. **Step 3:** `arxiv_paper_search.py` - Execute arXiv-specific searches
4. **Step 4:** `web_scrape.py` - multi-repository collection
5. **Step 5:** `screen_papers.py` - **AI-based systematic screening and prioritization**

## Performance Considerations

### Processing Efficiency
- **Incremental Processing:** Results saved immediately to prevent data loss
- **Duplicate Prevention:** Efficient cross-session tracking prevents re-processing
- **Memory Management:** Streaming processing avoids memory overload
- **Progress Tracking:** Real-time feedback with progress bars

### Cost Optimization
- **Text Truncation:** Limits API costs while preserving content quality
- **Quality Pre-Filtering:** Reduces API calls on low-quality papers
- **Efficient Prompting:** Optimized prompts minimize token usage
- **Structured Output:** Eliminates parsing overhead and errors

### Scalability Factors
- **Large Collections:** Handles thousands of papers efficiently  
- **Cross-Session Processing:** Resume capability for long-running tasks
- **Error Recovery:** Continues processing despite individual failures
- **Parallel Processing:** Sequential processing respects API rate limits

## Customization Options

### Assessment Criteria Modification
```python
# Modify Pydantic models to add new assessment dimensions
class CustomTechnicalScope(TechnicalScope):
    addresses_domain_specific_data: bool = Field(description="Domain-specific focus")
    uses_synthetic_data: bool = Field(description="Synthetic data generation")
```

### Priority Logic Customization
```python
# Custom priority assignment based on specific research needs
def custom_priority_logic(screening: PaperScreening) -> PriorityLevel:
    if screening.technical_scope.addresses_llm_data_collection:
        if screening.humanitarian_principles.humanity_score >= 2:
            return PriorityLevel.HIGH
    return PriorityLevel.MEDIUM
```

### Filtering Criteria Adjustment
```python
# Modify filtering thresholds
MIN_YEAR = 2021              # More recent papers only
MIN_TEXT_LENGTH = 1000       # Longer papers only
MIN_CITATION_COUNT = 5       # Higher impact papers only
```

## Technical Implementation Notes

- **Pydantic Validation:** Ensures structured output consistency and type safety
- **JSONL Format:** Enables streaming processing and easy data manipulation
- **UTF-8 Encoding:** Full international character support
- **Error Resilience:** Comprehensive exception handling prevents data loss
- **API Integration:** Beta structured output features for reliable parsing
- **Cross-Platform:** Works on Windows, macOS, and Linux environments
