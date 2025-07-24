#!/bin/bash
set -e

cd /home/discordbot/openguard

echo "Installing Python dependencies..."
sudo -u discordbot /home/discordbot/.local/bin/uv pip install -r pyproject.toml --group dashboard-backend --group dev

echo "Restarting backend service..."
systemctl restart openguard-backend.service

echo "Backend deployment successful."
