# Dockerfile for OpenProject MCP Server
# Optimized for Smithery.ai cloud builds

# Use standard Python image for better cloud compatibility
FROM python:3.12-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better Docker layer caching
COPY requirements.txt .

# Upgrade pip and install dependencies
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY openproject/ ./openproject/
COPY spec.yml .

# Create non-root user for security
RUN useradd --create-home --shell /bin/bash app && \
    chown -R app:app /app
USER app

# Set environment variables
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1
ENV PORT=8081

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import os; import requests; requests.get(f'http://localhost:{os.getenv(\"PORT\", 8081)}/health', timeout=5)" || exit 1

# Expose port
EXPOSE 8081

# Run the application
CMD ["python", "-m", "openproject.server"]