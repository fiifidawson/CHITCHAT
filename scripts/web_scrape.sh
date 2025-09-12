#!/usr/bin/env bash
set -euo pipefail

# -------------------------------------------------------------------
# web_scrape.sh
#
# Usage:
#   ./web_scrape.sh path/to/queries.json
#
# This script:
#  2. Installs required Python deps
#  3. Runs web_scrape.py with your JSON of Boolean queries
# -------------------------------------------------------------------

cd /mloscratch/users/arni/chitchat/CHITCHAT

PY_SCRIPT="web_scrape.py"

# 1. Check arguments
if [ "$#" -ne 1 ]; then
  echo "Usage: $0 <path-to-queries.json>"
  exit 1
fi
QUERIES_JSON="$1"

# 2. Ensure the Python script exists
if [ ! -f "$PY_SCRIPT" ]; then
  echo "Error: '$PY_SCRIPT' not found in current directory."
  exit 2
fi

# 4. Upgrade pip and install deps
pip install --upgrade pip
pip install \
    requests \
    beautifulsoup4 \
    scholarly \
    PyMuPDF \
    PyPDF2

# 6. Run the web_scrape
echo "Running $PY_SCRIPT with queries $QUERIES_JSON..."
python "$PY_SCRIPT" "$QUERIES_JSON"

echo "Done."