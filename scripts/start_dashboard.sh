#!/bin/bash

echo "Starting FastAPI backend..."
# Ensure the project root is on the Python path so the backend can
# import modules such as the `database` package.
export PYTHONPATH="$(pwd)"
# Load environment variables, if available
if [ -f .env ]; then
    set -o allexport
    source .env
    set +o allexport
fi
(cd dashboard/backend && python -m uvicorn main:app --reload --port 5030) &

echo "Starting React frontend..."
# Pass backend URL to React for proper redirects during development
export REACT_APP_API_URL="http://localhost:5030"
(cd dashboard/frontend && npm install && npm start) &

wait
