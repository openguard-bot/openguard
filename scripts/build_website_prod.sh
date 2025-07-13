#!/bin/bash
set -e

# Load environment variables if available
if [ -f .env ]; then
    set -o allexport
    source .env
    set +o allexport
fi

# Build Astro website for production
echo "Building Astro website..."
(cd website && npm install && npm run build)
shopt -s nullglob

if ! mkdir -p /srv/http/website; then
    echo "Failed to create /srv/http/website. See error above."
    # exit 1
fi

if ! rm -rf /srv/http/website/*; then
    echo "Failed to clear /srv/http/website. See error above."
    # exit 1
fi

if ! cp -r website/dist/* /srv/http/website/; then
    echo "Failed to copy files to /srv/http/website. See error above."
    # exit 1
fi

chown -R http:http /srv/http/website # Ensure correct ownership for web server