#!/bin/bash

# Create venv if not exists
if [ ! -d ".venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv .venv
fi

# Activate venv
source .venv/bin/activate

# Install requirements
echo "Installing dependencies..."
pip install -r requirements.txt

# Run app
echo "Starting application..."
python3 -m streamlit run Main.py --theme.base="light"
