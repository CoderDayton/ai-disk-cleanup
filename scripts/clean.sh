#!/bin/bash
# AI Disk Cleaner - Simple Shell Wrapper
# Quick and easy project cleanup

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

echo -e "${BLUE}🤖 AI Disk Cleaner - Quick Cleanup${NC}"
echo -e "${BLUE}📁 Project: $PROJECT_ROOT${NC}"
echo

# Check if Python script exists
if [[ ! -f "$SCRIPT_DIR/clean_project.py" ]]; then
    echo -e "${RED}❌ Error: clean_project.py not found in $SCRIPT_DIR${NC}"
    exit 1
fi

# Check for execute flag
if [[ "$1" == "--execute" || "$1" == "-e" ]]; then
    echo -e "${YELLOW}⚠️  EXECUTION MODE - This will permanently delete files!${NC}"
    read -p "Are you sure you want to continue? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo -e "${YELLOW}❌ Cancelled${NC}"
        exit 1
    fi
    echo -e "${GREEN}🚀 Executing cleanup...${NC}"
    python3 "$SCRIPT_DIR/clean_project.py" "$PROJECT_ROOT" --execute
else
    echo -e "${BLUE}🔍 DRY RUN MODE - No files will be deleted${NC}"
    echo -e "${YELLOW}💡 Use --execute to perform actual cleanup${NC}"
    echo
    python3 "$SCRIPT_DIR/clean_project.py" "$PROJECT_ROOT"
fi

echo
echo -e "${GREEN}✅ Done!${NC}"