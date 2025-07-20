#!/bin/bash

# Exit on any error
set -e

# Define project root
PROJECT_DIR=$(dirname "$0")

cd "$PROJECT_DIR"

# Set environment variables
export PYTHONDONTWRITEBYTECODE=1
export PYTHONUNBUFFERED=1
export FLASK_APP=src/app.py
export FLASK_RUN_HOST=0.0.0.0
export FLASK_RUN_PORT=5000
export FLASK_ENV=development
export FLASK_ENV_FILE=.env.dev

# Create virtual environment if not exists
if [ ! -d ".venv" ]; then
  python3.13 -m venv .venv
fi

# Activate virtual environment
source .venv/bin/activate

# Install dependencies
pip install --upgrade pip
pip install --no-cache-dir -r requirements.txt

# Run the Flask development server
flask run