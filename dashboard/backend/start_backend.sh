#!/bin/bash
# Navigate to the directory containing this script

# Install Python dependencies if not already installed
pip install -r requirements.txt

# Ensure the project root is on the Python path so the backend can
# import modules such as the `database` package.
export PYTHONPATH="$(realpath .)"

# Start the FastAPI server
uvicorn dashboard.backend.main:app --reload --port 5030

