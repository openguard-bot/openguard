#!/bin/bash

# Local CI/CD Check and Fix Script
# This script runs all the checks from the GitHub Actions workflow
# and applies fixes where possible

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Check for required tools
check_dependencies() {
    print_status "Checking dependencies..."
    
    local missing_deps=()
    
    if ! command_exists node; then
        missing_deps+=("node")
    fi
    
    if ! command_exists yarn; then
        missing_deps+=("yarn")
    fi
    
    if ! command_exists python3; then
        missing_deps+=("python3")
    fi
    
    if ! command_exists pip; then
        missing_deps+=("pip")
    fi
    
    if [ ${#missing_deps[@]} -ne 0 ]; then
        print_error "Missing dependencies: ${missing_deps[*]}"
        print_error "Please install the missing dependencies before running this script."
        exit 1
    fi
    
    print_success "All dependencies found"
}

# Node.js setup and checks
setup_nodejs() {
    print_status "Setting up Node.js environment..."
    
    if [ ! -f "yarn.lock" ]; then
        print_warning "yarn.lock not found. Make sure you're in the project root."
    fi
    
    print_status "Installing Node.js dependencies..."
    yarn install --frozen-lockfile
    
    print_success "Node.js dependencies installed"
}

# Python setup and checks
setup_python() {
    print_status "Setting up Python environment..."
    
    # Check if requirements.txt exists
    if [ ! -f "requirements.txt" ]; then
        print_warning "requirements.txt not found in root directory"
    fi
    
    # Check if dashboard backend requirements exist
    if [ ! -f "dashboard/backend/requirements.txt" ]; then
        print_warning "dashboard/backend/requirements.txt not found"
    fi
    
    print_status "Installing Python dependencies..."
    
    # Install main requirements
    if [ -f "requirements.txt" ]; then
        pip install -r requirements.txt
    fi
    
    # Install dashboard backend requirements
    if [ -f "dashboard/backend/requirements.txt" ]; then
        pip install -r dashboard/backend/requirements.txt
    fi
    
    # Install development tools
    pip install pyright pytest ruff
    
    print_success "Python dependencies installed"
}

# Run Node.js checks and fixes
run_nodejs_checks() {
    print_status "Running Node.js linting and tests..."
    
    # Run linter (assuming it has --fix capability)
    print_status "Running yarn lint..."
    if yarn lint --fix 2>/dev/null; then
        print_success "Linting passed (with fixes applied)"
    else
        print_warning "Linting failed or --fix not supported. Running without --fix..."
        yarn lint
    fi
    
    # Run tests
    print_status "Running Node.js tests..."
    yarn test
    print_success "Node.js tests passed"
    
    # Build projects
    print_status "Building Node.js projects..."
    yarn build
    print_success "Node.js build completed"
}

# Run Python checks and fixes
run_python_checks() {
    print_status "Running Python checks and fixes..."
    
    # Run Ruff with --fix and format
    print_status "Running Ruff with fixes and formatting..."
    if [ -f "bot.py" ] && [ -d "cogs" ] && [ -d "dashboard/backend" ]; then
        # Apply fixes
        ruff check bot.py cogs/ dashboard/backend --fix
        print_success "Ruff fixes applied"
        
        # Format code
        ruff format bot.py cogs/ dashboard/backend
        print_success "Code formatted with Ruff"
        
        # Run final check
        ruff check bot.py cogs/ dashboard/backend --output-format=github
        print_success "Ruff checks passed"
    else
        print_warning "Some Python directories not found. Running Ruff on available files..."
        find . -name "*.py" -not -path "./venv/*" -not -path "./.venv/*" | head -10 | xargs -r ruff check --fix
        find . -name "*.py" -not -path "./venv/*" -not -path "./.venv/*" | head -10 | xargs -r ruff format
    fi
    
    # Run Pyright
    print_status "Running Pyright type checking..."
    pyright
    print_success "Pyright type checking passed"
    
    # Run Python tests
    print_status "Running Python tests..."
    pytest
    print_success "Python tests passed"
}

# Main execution
main() {
    print_status "Starting local CI/CD checks and fixes..."
    echo
    
    # Check dependencies
    check_dependencies
    echo
    
    # Setup environments
    setup_nodejs
    echo
    setup_python
    echo
    
    # Run Node.js checks
    print_status "=== NODE.JS CHECKS ==="
    run_nodejs_checks
    echo
    
    # Run Python checks
    print_status "=== PYTHON CHECKS ==="
    run_python_checks
    echo
    
    print_success "All checks completed successfully!"
    print_status "Your code is ready for commit and push."
}

# Handle script arguments
case "${1:-}" in
    --nodejs-only)
        print_status "Running Node.js checks only..."
        check_dependencies
        setup_nodejs
        run_nodejs_checks
        ;;
    --python-only)
        print_status "Running Python checks only..."
        check_dependencies
        setup_python
        run_python_checks
        ;;
    --help|-h)
        echo "Usage: $0 [--nodejs-only|--python-only|--help]"
        echo
        echo "Options:"
        echo "  --nodejs-only    Run only Node.js checks and fixes"
        echo "  --python-only    Run only Python checks and fixes"
        echo "  --help, -h       Show this help message"
        echo
        echo "Default: Run all checks and fixes"
        ;;
    "")
        main
        ;;
    *)
        print_error "Unknown option: $1"
        echo "Use --help for usage information"
        exit 1
        ;;
esac
