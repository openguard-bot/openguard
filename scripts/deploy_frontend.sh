#!/bin/bash
set -e

echo "Building React frontend..."
(cd dashboard/frontend && npm install && npm run build)

echo "Deploying React frontend to /srv/http/dashboard..."
rm -rf /srv/http/dashboard/*
cp -r dashboard/frontend/dist/* /srv/http/dashboard/
chown -R http:http /srv/http/dashboard

echo "Frontend deployment successful."