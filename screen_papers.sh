#!/usr/bin/env bash
set -euo pipefail

# -------------------------------------------------------------------
# screen_papers.sh
#
# Usage:
#   ./screen_papers.sh path/to/prompt.txt path/to/papers.json
#
# This script:
#  1. Installs required Python deps
#  2. Sets the OpenAI API key from a file
#  3. Runs screen_papers.py with your prompt and papers JSON
# -------------------------------------------------------------------

cd /mloscratch/users/arni/chitchat/CHITCHAT

PY_SCRIPT="screen_papers.py"
API_KEY_FILE="openai_key.txt"  # Change this path if needed

# 1. Check arguments
if [ "$#" -ne 2 ]; then
  echo "Usage: $0 <path-to-prompt.txt> <path-to-papers.json>"
  exit 1
fi
PROMPT_FILE="$1"
PAPERS_JSON="$2"

# 2. Ensure the Python script exists
if [ ! -f "$PY_SCRIPT" ]; then
  echo "Error: '$PY_SCRIPT' not found in current directory."
  exit 2
fi

# 3. Check that input files exist
if [ ! -f "$PROMPT_FILE" ]; then
  echo "Error: Prompt file '$PROMPT_FILE' not found."
  exit 3
fi

if [ ! -f "$PAPERS_JSON" ]; then
  echo "Error: Papers JSON file '$PAPERS_JSON' not found."
  exit 4
fi

# 4. Check and load API key file
if [ ! -f "$API_KEY_FILE" ]; then
  echo "Error: API key file '$API_KEY_FILE' not found."
  echo "Please create a file named '$API_KEY_FILE' containing your OpenAI API key."
  exit 5
fi

# Read API key from file (removes trailing newlines)
OPENAI_API_KEY=$(cat "$API_KEY_FILE" | tr -d '\n\r')

if [ -z "$OPENAI_API_KEY" ]; then
  echo "Error: API key file '$API_KEY_FILE' is empty."
  exit 6
fi

# 5. Install dependencies
echo "Installing Python dependencies..."
pip install --upgrade pip
pip install \
    openai \
    pypdf2 \
    pydantic \
    tqdm

# 6. Export OpenAI API key
export OPENAI_API_KEY="$OPENAI_API_KEY"

# 7. Run the screening script
echo "Running $PY_SCRIPT with prompt $PROMPT_FILE and papers $PAPERS_JSON..."
python3 "$PY_SCRIPT" "$PROMPT_FILE" "$PAPERS_JSON"

echo "Done."