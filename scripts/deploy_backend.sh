#!/bin/bash
set -e

cd /home/discordbot/openguard

echo "Activating virtual environment..."
source .venv/bin/activate

echo "Installing Python dependencies..."
pip install -r dashboard/backend/requirements.txt

echo "Restarting backend service..."
systemctl restart openguard-backend

echo "Backend deployment successful."
