#!/bin/bash

# Exit if any command fails
set -e

# Define your project root (adjust this if needed)
PROJECT_DIR=$(dirname "$0")

cd "$PROJECT_DIR"

# Set environment variables
export FLASK_APP=src/app.py
export FLASK_ENV=production

# Create a virtual environment if not exists
if [ ! -d ".venv" ]; then
  python3.11 -m venv .venv
fi

# Activate virtual environment
source .venv/bin/activate

# Install dependencies
pip install --upgrade pip
pip install --no-cache-dir -r requirements.txt

# Run using Gunicorn (you can change workers if needed)
gunicorn -b 0.0.0.0:5000 src.app:application
