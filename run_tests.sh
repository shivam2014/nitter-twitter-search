#!/bin/bash
# Run all unit tests for nitter-twitter-search

set -e

echo "=========================================="
echo "Running nitter-twitter-search Unit Tests"
echo "=========================================="
echo ""

# Change to script directory
cd "$(dirname "$0")"

# Set PYTHONPATH
export PYTHONPATH="src:$PYTHONPATH"

# Check if pytest is installed
if ! python3 -m pytest --version > /dev/null 2>&1; then
    echo "Installing pytest..."
    python3 -m pip install pytest -q
fi

# Run tests
echo "Running tests..."
echo ""
python3 -m pytest tests/ -v --tb=short --color=yes

echo ""
echo "=========================================="
echo "Test run completed!"
echo "=========================================="
