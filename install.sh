#!/bin/bash
################################################################################
# HydroClaude Installation Script
# 
# This script installs all dependencies and sets up HydroClaude
#
# Usage:
#   ./install.sh              # Install all dependencies
#   ./install.sh --minimal    # Install minimal dependencies only
#   ./install.sh --dev        # Install development dependencies
################################################################################

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Print functions
print_header() {
    echo -e "${BLUE}================================${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}================================${NC}"
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

print_info() {
    echo -e "   $1"
}

# Check if Python is installed
check_python() {
    print_header "Checking Python Installation"
    
    if command -v python3 &> /dev/null; then
        PYTHON_VERSION=$(python3 --version | cut -d' ' -f2)
        print_success "Python 3 found: $PYTHON_VERSION"
        
        # Check version
        PYTHON_MAJOR=$(echo $PYTHON_VERSION | cut -d'.' -f1)
        PYTHON_MINOR=$(echo $PYTHON_VERSION | cut -d'.' -f2)
        
        if [ "$PYTHON_MAJOR" -ge 3 ] && [ "$PYTHON_MINOR" -ge 8 ]; then
            print_success "Python version >= 3.8 ✓"
        else
            print_error "Python 3.8+ required, found $PYTHON_VERSION"
            exit 1
        fi
    else
        print_error "Python 3 not found. Please install Python 3.8+"
        exit 1
    fi
}

# Check if pip is installed
check_pip() {
    print_header "Checking pip Installation"
    
    if command -v pip3 &> /dev/null; then
        PIP_VERSION=$(pip3 --version | cut -d' ' -f2)
        print_success "pip found: $PIP_VERSION"
    else
        print_error "pip3 not found. Installing..."
        python3 -m ensurepip --upgrade
    fi
}

# Install minimal dependencies
install_minimal() {
    print_header "Installing Minimal Dependencies"
    
    print_info "Installing core packages..."
    pip3 install numpy>=1.20.0 pandas>=1.3.0 matplotlib>=3.4.0 jsonschema>=4.0.0
    
    print_success "Minimal dependencies installed"
}

# Install optional dependencies
install_optional() {
    print_header "Installing Optional Dependencies"
    
    print_info "Installing h5py for HDF5 support..."
    pip3 install h5py>=3.0.0 || print_warning "h5py installation failed (optional)"
    
    print_info "Installing scipy for optimization..."
    pip3 install scipy>=1.7.0 || print_warning "scipy installation failed (optional)"
    
    print_success "Optional dependencies installed"
}

# Install development dependencies
install_dev() {
    print_header "Installing Development Dependencies"
    
    print_info "Installing testing frameworks..."
    pip3 install pytest pytest-cov || print_warning "pytest installation failed"
    
    print_info "Installing code quality tools..."
    pip3 install flake8 black isort || print_warning "code quality tools installation failed"
    
    print_info "Installing documentation tools..."
    pip3 install sphinx sphinx-rtd-theme || print_warning "documentation tools installation failed"
    
    print_success "Development dependencies installed"
}

# Verify installation
verify_installation() {
    print_header "Verifying Installation"
    
    python3 -c "import numpy; import pandas; import matplotlib; import jsonschema" 2>/dev/null
    if [ $? -eq 0 ]; then
        print_success "Core dependencies verified"
    else
        print_error "Core dependencies verification failed"
        exit 1
    fi
    
    # Test HydroClaude engine
    if [ -f "hydro_engine.py" ]; then
        python3 hydro_engine.py --version &> /dev/null
        if [ $? -eq 0 ]; then
            print_success "HydroClaude engine verified"
        else
            print_warning "HydroClaude engine test failed"
        fi
    fi
}

# Create necessary directories
setup_directories() {
    print_header "Setting Up Directories"
    
    mkdir -p results
    mkdir -p templates
    mkdir -p examples_config
    
    print_success "Directories created"
}

# Main installation function
main() {
    print_header "HydroClaude Installation"
    echo ""
    echo "Version: 1.0.0"
    echo "Platform: $(uname -s)"
    echo ""
    
    # Parse arguments
    INSTALL_MODE="full"
    if [ "$1" == "--minimal" ]; then
        INSTALL_MODE="minimal"
    elif [ "$1" == "--dev" ]; then
        INSTALL_MODE="dev"
    fi
    
    # Run installation steps
    check_python
    check_pip
    
    install_minimal
    
    if [ "$INSTALL_MODE" != "minimal" ]; then
        install_optional
    fi
    
    if [ "$INSTALL_MODE" == "dev" ]; then
        install_dev
    fi
    
    setup_directories
    verify_installation
    
    # Success message
    echo ""
    print_header "Installation Complete!"
    echo ""
    print_success "HydroClaude is ready to use"
    echo ""
    print_info "Quick start:"
    print_info "  python3 hydro_engine.py --template steady_canal"
    print_info "  python3 hydro_engine.py config_template_steady_canal.json"
    print_info "  open results/steady_canal/web/index.html"
    echo ""
    print_info "Documentation:"
    print_info "  ⭐ START_HERE.md - 30-second overview"
    print_info "  🌟 QUICK_START.md - 5-minute tutorial"
    print_info "  README.md - Complete documentation"
    echo ""
}

# Run main function
main "$@"
