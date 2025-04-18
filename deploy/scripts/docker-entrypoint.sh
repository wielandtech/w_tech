#!/bin/sh

# Create media directory if it doesn't exist
mkdir -p /app/media

# Set proper permissions
chown -R 1000:1000 /app/media
chmod -R 755 /app/media

# Execute the command passed to the script
exec "$@" 