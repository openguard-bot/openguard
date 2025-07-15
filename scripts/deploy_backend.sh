#!/bin/bash
set -e

cd /home/discordbot/openguard

echo "Activating virtual environment..."
source .venv/bin/activate

echo "Installing Python dependencies..."
pip install -r dashboard/backend/requirements.txt -r requirements.txt

echo "Restarting backend service..."
systemctl restart openguard-backend.service

echo "Backend deployment successful."
