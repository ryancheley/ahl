# Multi-stage build: Copy uv from official image
FROM ghcr.io/astral-sh/uv:latest AS builder

# Use Python 3.14 slim image
FROM python:3.14-slim

# Set metadata
LABEL maintainer="Ryan Cheley"
LABEL description="AHL Datasette Application"

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Copy uv from builder stage
COPY --from=builder /uv /bin/uv

# Install system dependencies
RUN apt-get update && apt-get install -y curl wget && rm -rf /var/lib/apt/lists/*

# Create app directory
WORKDIR /app

# Copy project configuration
COPY pyproject.toml .

# Install pip and setuptools first to ensure pkg_resources is available
RUN /bin/uv pip install --no-cache-dir --system pip setuptools wheel importlib-resources

# Install Python dependencies using pip (not uv) to ensure proper pkg_resources setup
RUN pip install --no-cache-dir .

# Copy application files
COPY games.db .
COPY metadata.yaml .
COPY program.py .

# Expose port
EXPOSE 8001

# Health check (before USER to run as root)
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD wget -q --spider http://localhost:8001/ || exit 1

# Create non-root user for security
RUN useradd --create-home --shell /bin/bash datasette && \
    chown -R datasette:datasette /app
USER datasette

# Start datasette with config for canned queries
CMD ["datasette", "games.db", "-c", "metadata.yaml", "--host", "0.0.0.0", "--port", "8001"]