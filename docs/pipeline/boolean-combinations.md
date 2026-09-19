---
title: Stage 1 — Boolean combinations
---

# Boolean Combinations Generator

## Overview
This script transforms word lists with synonyms into Boolean search combinations, making it easy to create comprehensive search queries for databases, search engines, or research applications.

## Data Flow
```
../data/structure.json → Process → ../data/boolean_combinations.json
```

**Input Directory:** `./data/`  
**Input Format:** JSON file containing words and their synonyms  
**Process:** Generate Boolean OR combinations from words and synonyms  
**Output:** JSON file with Boolean search strings  
**Output Directory:** `./data/`  
**Output Format:** JSON with Boolean combinations

## Function Reference

`generate_boolean_combinations(input_file, output_file)`

**Purpose:** Converts a structured word list into Boolean search combinations using OR operators.

**Parameters:**
- `input_file` (str, optional): Path to input JSON file (default: `'../data/structure.json'`)
- `output_file` (str, optional): Path for output JSON file (default: `'../data/boolean_combinations.json'`)

**Returns:**
- List of dictionaries with Boolean combinations on success
- `None` if an error occurs

## Input Format Requirements

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

## Output Format

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

## Processing Logic

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

## Usage 

### Basic Usage
```python
from boolean_combinations import generate_boolean_combinations

# Use default file paths
result = generate_boolean_combinations()
```

### Custom File Paths
```python
# Specify custom input and output files
result = generate_boolean_combinations(
    input_file='./my_data/words.json',
    output_file='./output/search_terms.json'
)
```

### Command Line Execution
```bash
python boolean_combinations.py
```

## Error Handling

The script includes error handling for:

- **File Not Found:** Displays clear message if input file doesn't exist
- **Invalid JSON:** Catches and reports JSON parsing errors
- **General Exceptions:** Handles unexpected errors gracefully

All errors are printed to console with descriptive messages.

## Output Messages

The script provides feedback during execution:
- Success message with count of generated combinations
- Preview of first 3 Boolean combinations for verification
- Error messages for troubleshooting

## File Structure Requirements

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
