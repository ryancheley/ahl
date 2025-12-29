#!/bin/bash
set -e

# Fix permissions on mounted volumes
echo "Setting permissions on /app..."
chown -R django:django /app 2>/dev/null || true

# Make games.db readable by everyone (even though mounted read-only)
if [ -f /app/games.db ]; then
    chmod 644 /app/games.db 2>/dev/null || true
fi

# Fix permissions on mounted volumes (skip read-only files)
echo "Setting permissions on /app..."
chown -R django:django /app 2>/dev/null || true

# Ensure db.sqlite3 is writable by django user if it exists
if [ -f /app/db.sqlite3 ]; then
    chmod 664 /app/db.sqlite3 2>/dev/null || true
fi

# Run the command passed to the container
exec "$@"
