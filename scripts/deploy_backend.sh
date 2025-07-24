#!/bin/bash
set -e

cd /home/discordbot/openguard

echo "Activating virtual environment..."
source .venv/bin/activate

echo "Installing Python dependencies..."
uv pip install -r pyproject.toml --all-extras

echo "Restarting backend service..."
systemctl restart openguard-backend.service

echo "Backend deployment successful."
