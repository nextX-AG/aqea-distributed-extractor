# AQEA Distributed Extractor
# Multi-stage Docker build for both master and worker nodes

FROM python:3.11-slim as base

# Set environment variables
ENV PYTHONPATH=/app
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Create app directory
WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code
COPY src/ ./src/
COPY config/ ./config/

# Create logs directory
RUN mkdir -p /app/logs /app/data

# Create non-root user for security
RUN groupadd -r aqea && useradd -r -g aqea -s /bin/bash aqea
RUN chown -R aqea:aqea /app
USER aqea

# Health check script
COPY --chown=aqea:aqea <<EOF /app/healthcheck.py
#!/usr/bin/env python3
import sys
import requests
import os

def check_health():
    role = os.getenv('AQEA_ROLE', 'worker')
    port = int(os.getenv('AQEA_PORT', '8080'))
    
    try:
        if role == 'master':
            response = requests.get(f'http://localhost:{port}/api/health', timeout=5)
            return response.status_code == 200
        else:
            # For workers, check if process is running
            return True
    except:
        return False

if __name__ == '__main__':
    sys.exit(0 if check_health() else 1)
EOF

RUN chmod +x /app/healthcheck.py

# Set up health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python /app/healthcheck.py

# Default command (can be overridden)
CMD ["python", "-m", "src.main", "--help"]

# Labels for metadata
LABEL maintainer="AQEA Project"
LABEL version="1.0.0"
LABEL description="AQEA Distributed Language Data Extractor"

# Production image
FROM base as production

# Set production environment
ENV ENVIRONMENT=production
ENV AQEA_CONFIG_FILE=/app/config/production.yml

# Copy production config if available
COPY config/production.yml ./config/production.yml 2>/dev/null || echo "No production config found"

# Development image
FROM base as development

# Install development dependencies
RUN pip install --no-cache-dir pytest pytest-asyncio pytest-cov black flake8 mypy

# Set development environment
ENV ENVIRONMENT=development
ENV AQEA_CONFIG_FILE=/app/config/default.yml

# Expose default ports
EXPOSE 8080 8090

# Master node variant
FROM production as master

ENV AQEA_ROLE=master
ENV AQEA_PORT=8080

CMD ["python", "-m", "src.main", "start_master", "--language", "de", "--source", "wiktionary"]

# Worker node variant
FROM production as worker

ENV AQEA_ROLE=worker
ENV MASTER_HOST=master
ENV MASTER_PORT=8080

CMD ["python", "-m", "src.main", "start_worker"] 