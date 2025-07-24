#!/bin/bash
set -e

cd /home/discordbot/openguard

echo "Activating virtual environment..."
source .venv/bin/activate

echo "Installing Python dependencies..."
uv pip install -r pyproject.toml --group dashboard-backend --group dev

echo "Restarting backend service..."
systemctl restart openguard-backend.service

echo "Backend deployment successful."
