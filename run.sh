#!/bin/bash
# Startup script for Polymarket Whale Tracker

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "Virtual environment not found. Running setup..."
    bash setup.sh
fi

# Activate virtual environment
source venv/bin/activate

# Run the tracker
python main.py
