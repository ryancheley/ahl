#!/bin/bash
set -e

# Fix permissions on mounted volumes and directories
echo "Setting permissions on /app..."

# Make /app directory writable (needed for SQLite lock files)
chmod 755 /app 2>/dev/null || true
chown -R django:django /app 2>/dev/null || true

# Make games.db readable by everyone (even though mounted read-only)
if [ -f /app/games.db ]; then
    chmod 644 /app/games.db 2>/dev/null || true
fi

# Ensure db.sqlite3 is fully writable by django user if it exists
if [ -f /app/db.sqlite3 ]; then
    chmod 666 /app/db.sqlite3 2>/dev/null || true
fi

# Run the command passed to the container
exec "$@"
