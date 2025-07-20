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

(python -m uvicorn dashboard.backend.main:app --reload --port 5030) &
BACKEND_PID=$!

echo "Starting Vite frontend..."
# Pass backend URL to Vite for proper redirects during development
export VITE_REACT_APP_API_URL="http://localhost"
(cd dashboard/frontend && npm install && npm run dev) &
FRONTEND_PID=$!

wait $BACKEND_PID $FRONTEND_PID
