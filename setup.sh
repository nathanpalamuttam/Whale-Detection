#!/bin/bash
# Setup script for Polymarket Whale Tracker

set -e

echo "=================================="
echo "Polymarket Whale Tracker Setup"
echo "=================================="
echo ""

# Check Python version
echo "Checking Python version..."
python3 --version || {
    echo "Error: Python 3 is not installed"
    exit 1
}

# Create virtual environment
echo ""
echo "Creating virtual environment..."
if [ ! -d "venv" ]; then
    python3 -m venv venv
    echo "✓ Virtual environment created"
else
    echo "✓ Virtual environment already exists"
fi

# Activate virtual environment
echo ""
echo "Activating virtual environment..."
source venv/bin/activate

# Upgrade pip
echo ""
echo "Upgrading pip..."
pip install --upgrade pip

# Install dependencies
echo ""
echo "Installing dependencies..."
pip install -r requirements.txt

# Create necessary directories
echo ""
echo "Creating directories..."
mkdir -p logs state
echo "✓ Directories created"

# Copy environment file if it doesn't exist
if [ ! -f ".env" ]; then
    if [ -f ".env.example" ]; then
        cp .env.example .env
        echo "✓ Created .env file from .env.example"
    fi
fi

# Make main.py executable
chmod +x main.py
echo "✓ Made main.py executable"

echo ""
echo "=================================="
echo "Setup Complete! 🎉"
echo "=================================="
echo ""
echo "To start tracking whales, run:"
echo "  source venv/bin/activate"
echo "  python main.py"
echo ""
echo "Or simply:"
echo "  ./run.sh"
echo ""
