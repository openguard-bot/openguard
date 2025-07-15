#!/bin/bash
set -e

# Load environment variables if available
if [ -f .env ]; then
    set -o allexport
    source .env
    set +o allexport
fi

# Build React frontend for production
echo "Building React frontend..."
(cd dashboard/frontend && npm install && npm run build)
shopt -s nullglob

if ! sudo rm -rf /srv/http/dashboard/*; then
    echo "Failed to clear /srv/http/dashboard. See error above."
    # exit 1
fi

if ! sudo cp -r dashboard/frontend/dist/* /srv/http/dashboard/; then
    echo "Failed to copy files to /srv/http/dashboard. See error above."
    # exit 1
fi

sudo chown -R http:http /srv/http/dashboard # Ensure correct ownership for web server

# Start FastAPI backend
echo "Starting FastAPI backend..."
export PYTHONPATH="$(pwd)"
(cd dashboard/backend && pip install -r requirements.txt && uvicorn main:app --host 0.0.0.0 --port 5030)
