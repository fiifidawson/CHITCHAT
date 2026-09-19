---
title: Stage 2 — Unique combinations
---

# Unique Boolean Combinations Generator

## Overview
This script creates unique Boolean search combinations by combining multiple predefined research categories. It takes the output from the basic boolean combinations generator and creates complex search queries tailored for academic research across different domains like AI, humanitarian work, and social impact.

## Data Flow
```
../data/boolean_combinations.json → Process → ../output/unique_boolean_combinations.json
```

**Input Directory:** `./data/`  
**Input Format:** JSON file with individual Boolean combinations  
**Process:** Combine multiple Boolean terms using AND operators for research categories  
**Output:** JSON file with complex multi-category Boolean search strings  
**Output Directory:** `./output/`  
**Output Format:** JSON with unique category-based combinations

## Core Components

### `UniqueBooleanCombinationsGenerator` Class

**Purpose:** Main class that handles the generation of unique Boolean combinations for specific research categories.

**Key Features:**
- Loads existing Boolean combinations from JSON
- Maps predefined research categories to relevant search terms
- Combines multiple Boolean expressions using AND operators
- Provides detailed feedback on missing or found keys
- Handles error cases gracefully

## Predefined Research Categories

The script includes 8 specialized research categories:

### 1. Broad Foundational Search
**Focus:** Core AI and ML concepts  
**Key Terms:** Foundation model, AI Systems, Machine Learning, Deep Learning, Applications & Domains

### 2. Humanitarian & Social Impact Search
**Focus:** Crisis response and humanitarian applications  
**Key Terms:** Humanitarian principles, Neutrality, Social Good, Vulnerable Populations, Human Rights

### 3. Inclusion & Representation Search
**Focus:** Equity and representation in AI  
**Key Terms:** Vulnerable Populations, Human Rights, Data Collection Methods, Rights & Protection

### 4. Transparency & Accountability Search
**Focus:** AI governance and accountability  
**Key Terms:** AI Systems, Data Processing, Rights Frameworks, Development Guides

### 5. Harm Reduction & Safety Search
**Focus:** AI safety and risk mitigation  
**Key Terms:** Mitigation Strategies, Environmental Concerns, Rights Frameworks, Safety Guides

### 6. Control, Consent & Personal Data Rights
**Focus:** Data privacy and user control  
**Key Terms:** Rights Frameworks, Data Collection, Privacy Protection, AI Systems

### 7. Consent, Agency & Participatory AI
**Focus:** User agency and participatory design  
**Key Terms:** Human Rights, Organizations, Key Actions, Social Good

### 8. Environmental & Infrastructural Cost
**Focus:** Environmental impact of AI systems  
**Key Terms:** Environmental Concerns, Mitigation, AI Development, Infrastructure

## Input Format Requirements

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

## Output Format

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

## Class Methods Reference

### `__init__(boolean_combinations_file)`
**Purpose:** Initialize the generator with input file path  
**Parameters:** Path to boolean combinations JSON file  
**Default:** `'./data/boolean_combinations.json'`

### `generate_all_unique_combinations()`
**Purpose:** Generate combinations for all predefined categories  
**Returns:** List of dictionaries with combination details  
**Output:** Console feedback with progress and warnings

### `save_unique_combinations(combinations, output_file)`
**Purpose:** Save generated combinations to JSON file  
**Parameters:**
- `combinations`: List of generated combinations
- `output_file`: Output file path (default: `'./data/unique_boolean_combinations.json'`)

### `display_available_keys()`
**Purpose:** Show all available keys from input file  
**Use Case:** Debugging and verification of available terms

### `display_predefined_combinations()`
**Purpose:** Display all predefined category mappings  
**Use Case:** Understanding what categories and terms are configured

### `update_predefined_combination(category, new_keys)`
**Purpose:** Modify predefined combinations for a category  
**Parameters:**
- `category`: Category name to update
- `new_keys`: List of new key terms for the category

## Processing Logic

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

## Usage 

### Basic Usage
```python
from unique_boolean_combinations import generate_unique_boolean_combinations

# Generate with default paths
success = generate_unique_boolean_combinations()
```

### Custom File Paths
```python
# Specify custom input and output files
success = generate_unique_boolean_combinations(
    input_file='./data/boolean_combinations.json',
    output_file='./output/unique_boolean_combinations.json'
)
```

### Using the Class Directly
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

### Customizing Categories
```python
generator = UniqueBooleanCombinationsGenerator()

# Update a specific category
new_keys = ["Machine Learning", "Deep Learning", "Neural Networks"]
generator.update_predefined_combination("Broad Foundational Search", new_keys)

# Generate with updated configuration
combinations = generator.generate_all_unique_combinations()
```

### Command Line Execution
```bash
python unique_boolean_combinations.py
```

## Error Handling & Feedback

The script provides error handling:

### File-Related Errors
- **Missing Input File:** Clear message if boolean combinations file doesn't exist
- **Invalid JSON:** Handles corrupted or malformed JSON input
- **Save Errors:** Reports issues when writing output file

### Data-Related Warnings
- **Missing Keys:** Reports when predefined keys aren't found in input data
- **Empty Categories:** Handles categories with no valid combinations
- **Key Mismatches:** Detailed reporting of found vs. missing terms

### Console Feedback
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

## File Structure Requirements

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

## Integration Workflow

This script is designed to work in sequence with `boolean_combinations.py`:

1. **Step 1:** Run `boolean_combinations.py` to generate basic Boolean combinations
2. **Step 2:** Run `unique_boolean_combinations.py` to create complex research-focused combinations
3. **Step 3:** Use the generated combinations in academic databases and search engines

## Customization Options

### Adding New Categories
```python
# Add to predefined_combinations dictionary
"New Research Category": [
    "Key Term 1",
    "Key Term 2", 
    "Key Term 3"
]
```

### Modifying Existing Categories
Use the `update_predefined_combination()` method or directly edit the predefined combinations dictionary.

### Changing Combination Logic
The current implementation uses AND operators between different Boolean groups. This can be modified in the `_generate_combination_for_category()` method.

## Technical Notes

- **Encoding:** Full UTF-8 support for international characters
- **Logic:** Uses AND operators to combine different Boolean groups
- **Validation:** checking for missing keys and empty results
- **Performance:** Efficient lookup using dictionary mapping
- **Memory:** Loads all data in memory for fast processing
