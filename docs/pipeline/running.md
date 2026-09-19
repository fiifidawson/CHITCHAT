---
title: Running the pipeline
---

# Running

## Shell Scripts

### Overview
This bash script provides automated environment setup and execution for the AI-powered research paper screening system. It handles dependency installation, API key management, and secure execution of the screening process with comprehensive error checking and validation.

### Data Flow
```
prompt.txt + papers.json → Environment Setup → screen_papers.py → screening_results.jsonl
```

**Input Directory:** Current working directory  
**Input Format:** Text prompt file + JSON paper collection  
**Process:** Dependency installation, API key loading, Python script execution  
**Output:** Timestamped JSONL file with screening results  
**Output Directory:** `./output/`  
**Output Format:** JSONL with structured screening assessments

### Script Features

#### Core Functionality
- **Automated Dependency Installation:** Installs all required Python packages
- **Secure API Key Management:** Loads OpenAI API key from external file
- **Comprehensive Validation:** Checks all inputs before execution
- **Error Handling:** Detailed error codes and messages for debugging
- **Environment Configuration:** Sets up proper Python environment

#### Security Features
- **API Key File Protection:** Keeps API keys out of command line and environment
- **Input Validation:** Verifies all required files exist before processing
- **Secure Key Loading:** Strips whitespace and validates non-empty keys
- **Clean Environment:** Proper variable export and cleanup

### Usage 

#### Basic Usage
```bash
# Make script executable
chmod +x screen_papers.sh

# Run screening with prompt and papers
./screen_papers.sh screening_prompt.txt obtained_lit.json
```

#### Directory Structure Setup
```bash
# Expected file structure
chitchat/ # Refine
├── screen_papers.sh
├── screen_papers.py
├── openai_key.txt              # Your OpenAI API key
├── screening_prompt.txt        # Screening instructions
├── obtained_lit.json          # Papers to screen
└── output/                     # Generated results
```

#### API Key File Setup
```bash
# Create API key file (one-time setup)
echo "sk-your-openai-api-key-here" > openai_key.txt

# Verify key file (should show your key)
cat openai_key.txt
```

### Input Requirements

#### Command Line Arguments
```bash
./screen_papers.sh <path-to-prompt.txt> <path-to-papers.json>
```

**Required Arguments:**
1. **Prompt File:** Text file containing screening instructions for AI
2. **Papers JSON:** JSON file with paper collection from web scraping

#### File Dependencies
- **`screen_papers.py`:** Main Python screening script
- **`openai_key.txt`:** File containing OpenAI API key
- **Prompt file:** Custom screening instructions
- **Papers JSON:** Literature collection to be screened

### Environment Setup

#### Python Dependencies Installed
```bash
pip install --upgrade pip
pip install \
    openai \
    pypdf2 \
    pydantic \
    tqdm
```

**Package Functions:**
- **`openai`:** AI-powered structured assessment
- **`pypdf2`:** PDF text extraction capabilities
- **`pydantic`:** Structured data validation models
- **`tqdm`:** Progress bar visualization

### Working Directory
```bash
cd /mloscratch/users/username/chitchat/CHITCHAT
```
**Note:** Script changes to specific working directory for execution

### Error Handling & Exit Codes

#### Exit Code Reference
- **Exit 1:** Incorrect number of command line arguments
- **Exit 2:** Python script `screen_papers.py` not found
- **Exit 3:** Prompt file not found
- **Exit 4:** Papers JSON file not found
- **Exit 5:** API key file not found
- **Exit 6:** API key file is empty

#### Error Message Examples
```bash
# Incorrect usage
$ ./screen_papers.sh
Usage: ./screen_papers.sh <path-to-prompt.txt> <path-to-papers.json>

# Missing files
$ ./screen_papers.sh missing.txt papers.json
Error: Prompt file 'missing.txt' not found.

# Missing API key
$ ./screen_papers.sh prompt.txt papers.json
Error: API key file 'openai_key.txt' not found.
Please create a file named 'openai_key.txt' containing your OpenAI API key.
```

### Security Considerations

#### API Key Management
- **File-Based Storage:** Keeps API keys out of command line history
- **Whitespace Cleaning:** Removes trailing newlines and carriage returns
- **Validation:** Ensures non-empty key before proceeding
- **Environment Export:** Properly exports key for Python script access

#### Input Validation
- **File Existence Checks:** Verifies all required files before execution
- **Script Validation:** Ensures Python script is available
- **Argument Count:** Validates correct number of parameters

### Processing Workflow

#### Phase 1: Argument Validation
1. **Count Check:** Ensure exactly 2 arguments provided
2. **Assignment:** Store prompt file and papers JSON paths
3. **Usage Display:** Show correct usage on argument errors

#### Phase 2: File Validation
1. **Python Script Check:** Verify `screen_papers.py` exists
2. **Input File Verification:** Confirm prompt and papers files exist
3. **API Key File Check:** Validate API key file presence and content

#### Phase 3: Environment Setup
1. **Pip Upgrade:** Update package manager to latest version
2. **Dependency Installation:** Install all required Python packages
3. **API Key Loading:** Read and clean API key from file
4. **Environment Export:** Make API key available to Python script

#### Phase 4: Script Execution
1. **Status Display:** Show execution parameters
2. **Python Invocation:** Run screening script with arguments
3. **Completion Message:** Confirm successful execution

### Customization Options

#### API Key File Location
```bash
# Modify API_KEY_FILE variable
API_KEY_FILE="path/to/your/api_key.txt"
```

#### Working Directory
```bash
# Change working directory
cd /your/project/directory
```

#### Additional Dependencies
```bash
# Add more Python packages
pip install \
    openai \
    pypdf2 \
    pydantic \
    tqdm \
    your-additional-package
```

### Troubleshooting Guide

#### Common Issues

##### Permission Denied
```bash
# Make script executable
chmod +x screen_papers.sh
```

##### API Key Issues
```bash
# Check API key file
cat openai_key.txt

# Recreate API key file
echo "sk-your-actual-key" > openai_key.txt
```

##### Python Environment Issues
```bash
# Check Python version
python3 --version

# Manual dependency installation
pip3 install openai pydantic tqdm pypdf2
```

##### File Path Issues
```bash
# Use absolute paths if needed
./screen_papers.sh /full/path/to/prompt.txt /full/path/to/papers.json
```

### Integration with Paper Screening Pipeline

#### Pipeline Position
This script serves as the **execution wrapper** for the final step in the research automation pipeline:

1. Boolean combinations generation
2. Unique combinations creation  
3. ArXiv paper search
4. Multi-repository web scraping
5. **Shell script execution** → AI-powered screening

#### Execution Flow
```bash
# Previous steps generate these files:
# - obtained_lit.json (from web scraping)
# - screening_prompt.txt (custom screening instructions)

# This script executes:
./screen_papers.sh screening_prompt.txt obtained_lit.json

# Generates:
# - output/screening_results_TIMESTAMP.jsonl
```

### Best Practices

#### Security Best Practices
- **API Key Protection:** Never commit API key files to version control
- **File Permissions:** Restrict access to API key file (chmod 600)
- **Key Rotation:** Regularly rotate OpenAI API keys
- **Environment Isolation:** Use virtual environments for Python dependencies

#### Operational Best Practices
- **Backup Strategy:** Backup screening results before re-running
- **Progress Monitoring:** Monitor script output for errors or issues
- **Resource Management:** Ensure sufficient disk space for results
- **Cost Monitoring:** Track OpenAI API usage and costs

#### Development Best Practices
- **Version Control:** Track script changes and improvements
- **Documentation:** Maintain clear documentation for team use
- **Testing:** Test with small paper sets before full runs
- **Error Logging:** Capture and analyze error patterns

### Performance Considerations

#### Resource Requirements
- **Memory:** Sufficient RAM for Python dependencies and paper processing
- **Storage:** Adequate disk space for screening results
- **Network:** Stable internet connection for OpenAI API calls
- **CPU:** Moderate processing power for JSON manipulation

#### Optimization Tips
- **Batch Size:** Process papers in manageable batches
- **Monitoring:** Use progress indicators to track completion
- **Parallel Processing:** Consider multiple script instances for large datasets
- **Cost Control:** Monitor API usage to manage costs

### Technical Implementation Notes

- **Bash Best Practices:** Uses `set -euo pipefail` for strict error handling
- **Cross-Platform:** Compatible with Unix-like systems (Linux, macOS)
- **Environment Management:** Proper variable scoping and cleanup
- **Process Control:** Clean script termination on errors
- **Logging:** Comprehensive status messages throughout execution

## Running Locally

!!! warning "Incomplete"

    A full local walkthrough — running every stage end to end on one machine —
    has not been written yet. The command-line entry point below is the part
    that is documented; see [Quickstart](../getting-started/quickstart.md) for
    what else is still missing.

### Run using the command line

1. Add your OpenAI API key with `export OPENAI_API_KEY="your-api-key-here"`.
2. Run the screening stage:

    ```bash
    python3 screen_papers.py path/to/paper_screening_prompt.txt path/to/papers.json
    ```

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
