#!/bin/bash
#
# Local Test Script for SpecterDefence
# Run this before pushing to catch issues early
#

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Counters
PASSED=0
FAILED=0

# Function to print section headers
print_header() {
    echo ""
    echo -e "${BLUE}══════════════════════════════════════════════════════════${NC}"
    echo -e "${BLUE}  $1${NC}"
    echo -e "${BLUE}══════════════════════════════════════════════════════════${NC}"
}

# Function to run a test step
run_step() {
    local name="$1"
    local cmd="$2"
    
    echo ""
    echo -e "${YELLOW}▶ $name...${NC}"
    
    if eval "$cmd" > /tmp/test_output.log 2>&1; then
        echo -e "${GREEN}✓ $name PASSED${NC}"
        PASSED=$((PASSED + 1))
        return 0
    else
        echo -e "${RED}✗ $name FAILED${NC}"
        echo -e "${RED}--- Output ---${NC}"
        cat /tmp/test_output.log
        echo -e "${RED}--------------${NC}"
        FAILED=$((FAILED + 1))
        return 1
    fi
}

# Get script directory and project root
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_ROOT"

echo -e "${BLUE}╔════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║       SpecterDefence Local Test Suite                  ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "${YELLOW}Project Root: $PROJECT_ROOT${NC}"
echo ""

# ═══════════════════════════════════════════════════════════
# STEP 1: Python Linting
# ═══════════════════════════════════════════════════════════
print_header "STEP 1: Python Linting"

# Determine Python command (prefer python3)
if command -v python3 &> /dev/null; then
    PYTHON_CMD="python3"
elif command -v python &> /dev/null; then
    PYTHON_CMD="python"
else
    echo -e "${RED}✗ Python not found${NC}"
    exit 1
fi

# Check if ruff is available
if ! command -v ruff &> /dev/null; then
    echo -e "${YELLOW}⚠ ruff not found in PATH, trying with $PYTHON_CMD -m ruff${NC}"
    RUFF_CMD="$PYTHON_CMD -m ruff"
else
    RUFF_CMD="ruff"
fi

# Check if black is available
if ! command -v black &> /dev/null; then
    echo -e "${YELLOW}⚠ black not found in PATH, trying with $PYTHON_CMD -m black${NC}"
    BLACK_CMD="$PYTHON_CMD -m black"
else
    BLACK_CMD="black"
fi

run_step "Ruff lint check" "$RUFF_CMD check src/"
run_step "Black format check" "$BLACK_CMD --check src/"

# ═══════════════════════════════════════════════════════════
# STEP 2: Python Tests
# ═══════════════════════════════════════════════════════════
print_header "STEP 2: Python Tests"

# Check if pytest is available
if ! command -v pytest &> /dev/null; then
    echo -e "${YELLOW}⚠ pytest not found in PATH, trying with $PYTHON_CMD -m pytest${NC}"
    PYTEST_CMD="$PYTHON_CMD -m pytest"
else
    PYTEST_CMD="pytest"
fi

run_step "Pytest" "$PYTEST_CMD tests/ -v --tb=short"

# ═══════════════════════════════════════════════════════════
# STEP 3: Frontend Build
# ═══════════════════════════════════════════════════════════
print_header "STEP 3: Frontend Build"

if [ ! -d "frontend" ]; then
    echo -e "${RED}✗ Frontend directory not found${NC}"
    FAILED=$((FAILED + 1))
else
    cd frontend
    
    # Check if node_modules exists
    if [ ! -d "node_modules" ]; then
        echo -e "${YELLOW}⚠ node_modules not found, running npm install...${NC}"
        npm install > /tmp/npm_install.log 2>&1 || {
            echo -e "${RED}✗ npm install failed${NC}"
            cat /tmp/npm_install.log
            FAILED=$((FAILED + 1))
            cd ..
            continue
        }
    fi
    
    run_step "Frontend build" "npm run build"
    cd ..
fi

# ═══════════════════════════════════════════════════════════
# STEP 4: Docker Build
# ═══════════════════════════════════════════════════════════
print_header "STEP 4: Docker Build Test"

if ! command -v docker &> /dev/null; then
    echo -e "${YELLOW}⚠ Docker not found, skipping Docker build test${NC}"
else
    # Test main app Docker build
    run_step "Docker build (main app)" "docker build -t specterdefence:test-build ."
    
    # Clean up test image
    echo -e "${YELLOW}  Cleaning up test image...${NC}"
    docker rmi specterdefence:test-build > /dev/null 2>&1 || true
fi

# ═══════════════════════════════════════════════════════════
# SUMMARY
# ═══════════════════════════════════════════════════════════
echo ""
echo -e "${BLUE}╔════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║                     TEST SUMMARY                       ║${NC}"
echo -e "${BLUE}╠════════════════════════════════════════════════════════╣${NC}"

if [ $FAILED -eq 0 ]; then
    echo -e "${BLUE}║${NC}  ${GREEN}✓ All tests passed! ($PASSED/$((PASSED + FAILED)))${NC}                        ${BLUE}║${NC}"
    echo -e "${BLUE}╚════════════════════════════════════════════════════════╝${NC}"
    echo ""
    echo -e "${GREEN}🎉 Ready to push!${NC}"
    exit 0
else
    echo -e "${BLUE}║${NC}  ${GREEN}Passed: $PASSED${NC}                                          ${BLUE}║${NC}"
    echo -e "${BLUE}║${NC}  ${RED}Failed: $FAILED${NC}                                          ${BLUE}║${NC}"
    echo -e "${BLUE}╚════════════════════════════════════════════════════════╝${NC}"
    echo ""
    echo -e "${RED}❌ Please fix the failing tests before pushing.${NC}"
    exit 1
fi
