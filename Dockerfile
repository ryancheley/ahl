FROM python:3.14-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install uv
RUN pip install --no-cache-dir uv

# Copy dependency files
COPY pyproject.toml uv.lock ./

# Install Python dependencies using uv
RUN uv pip install --python /usr/local/bin/python --no-cache-dir -e .

# Copy application code
COPY . .

# Create a non-root user for running the app
RUN groupadd -r datasette && useradd -r -g datasette datasette && \
    chown -R datasette:datasette /app

# Create data directory for persistent database storage
# Database files are stored in /data for persistence (configured via VOLUME mount in Coolify)
RUN mkdir -p /data && chown -R datasette:datasette /data

# Create entrypoint script to ensure database exists at runtime
RUN printf '#!/bin/sh\nset -e\nif [ ! -f /data/my_database.db ]; then\n  echo "Creating empty database..."\n  python3 -c "import sqlite3; sqlite3.connect('\''/data/my_database.db'\'').close()"\n  chown datasette:datasette /data/my_database.db\n  chmod 666 /data/my_database.db\nfi\nexec "$@"\n' > /entrypoint.sh && \
    chmod +x /entrypoint.sh

# Expose port for datasette
EXPOSE 8001

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8001/ || exit 1

# Use entrypoint script to initialize database
ENTRYPOINT ["/entrypoint.sh"]

# Start datasette with database from persistent volume
CMD ["datasette", "/data/my_database.db", "--metadata", "metadata.yaml", "--host", "0.0.0.0", "--port", "8001"]