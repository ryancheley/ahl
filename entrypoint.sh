#!/bin/bash
set -e

# Fix permissions on mounted volumes (skip read-only files)
echo "Setting permissions on /app..."
chown -R django:django /app 2>/dev/null || true

# Ensure db.sqlite3 is writable by django user if it exists
if [ -f /app/db.sqlite3 ]; then
    chmod 664 /app/db.sqlite3 2>/dev/null || true
fi

# Run the command passed to the container
exec "$@"
