FROM python:3.14-slim

# Set timezone
ENV TZ=America/Los_Angeles

# Install curl, datasette, and uv
RUN apt-get update && apt-get install -y curl && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir datasette uv

WORKDIR /app

# Copy project files
COPY pyproject.toml uv.lock ./
COPY program.py monte_carlo.py retrain.py playoff_predictor.py ./
COPY plugins ./plugins

# Download metadata from GitHub
RUN curl -L -o /app/metadata.yaml https://raw.githubusercontent.com/ryancheley/ahl/refs/heads/main/metadata.yaml

# Compile and install dependencies from pyproject.toml using uv
RUN uv pip compile pyproject.toml -o /tmp/requirements.txt && \
    uv pip install --python /usr/local/bin/python --no-cache-dir -r /tmp/requirements.txt

# Create data directory for persistent database storage
WORKDIR /data

# Expose port for datasette
EXPOSE 8001

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8001/ || exit 1

# Start datasette with database from persistent volume
CMD ["datasette", "serve", "/data/my_database.db", "--metadata", "/app/metadata.yaml", "--host", "0.0.0.0", "--port", "8001", "--plugins-dir", "/app/plugins", "--template-dir", "/app/plugins/templates"]