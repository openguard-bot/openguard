#!/bin/bash
set -e

echo "Installing Python dependencies..."
(cd dashboard/backend && pip install -r requirements.txt)

echo "Restarting backend service..."
systemctl restart openguard-backend

echo "Backend deployment successful."