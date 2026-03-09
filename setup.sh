#!/bin/bash

set -e

GREEN='\033[92m'
DIM='\033[2m'
BOLD='\033[1m'
RESET='\033[0m'

echo ""
echo "${BOLD}CURATOR — Setup${RESET}"
echo "${DIM}Human Connection as Intelligent Context${RESET}"
echo ""

# Create venv if it doesn't exist
if [ ! -d ".venv" ]; then
    echo "${DIM}Creating virtual environment...${RESET}"
    python3 -m venv .venv
fi

# Activate
source .venv/bin/activate

# Install dependencies
echo "${DIM}Installing dependencies...${RESET}"
pip install -r requirements.txt -q

echo ""
echo "${GREEN}✓ Setup complete${RESET}"
echo ""
echo "To run tests:"
echo "  ${DIM}source .venv/bin/activate${RESET}"
echo "  ${DIM}export ANTHROPIC_API_KEY=your_key_here${RESET}"
echo "  ${DIM}python3 test_curator.py${RESET}"
echo ""
