#!/bin/bash
# Navigate to the directory containing this script

# Install Python dependencies if not already installed
uv pip install -r pyproject.toml --all-extras

# Ensure the project root is on the Python path so the backend can
# import modules such as the `database` package.
export PYTHONPATH="$(realpath .)"

# Start the FastAPI server
uvicorn dashboard.backend.main:app --reload --port 5030

