FROM python:3.14-slim

# Set timezone
ENV TZ=America/Los_Angeles

# Install curl, datasette, and uv
RUN apt-get update && apt-get install -y curl && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir datasette uv

WORKDIR /app

# Copy project files
COPY pyproject.toml uv.lock ./
COPY program.py .

# Download metadata from GitHub
RUN curl -L -o /app/metadata.json https://raw.githubusercontent.com/ryancheley/ahl/refs/heads/main/metadata.json

# Install Python dependencies using uv (without editable mode to avoid breaking datasette)
RUN uv pip install --python /usr/local/bin/python --no-cache-dir \
    beautifulsoup4 lxml pyyaml httpx pydantic pydantic-sqlite rich click

# Create data directory for persistent database storage
WORKDIR /data

# Create empty database if it doesn't exist (will be overwritten by actual database via SCP)
RUN python3 -c "import sqlite3; sqlite3.connect('my_database.db').close()" || true

# Expose port for datasette
EXPOSE 8001

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8001/ || exit 1

# Start datasette with database from persistent volume
CMD ["datasette", "serve", "/data/my_database.db", "--metadata", "/app/metadata.json", "--host", "0.0.0.0", "--port", "8001"]