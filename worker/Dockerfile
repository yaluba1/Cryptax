FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PYTHONPATH=/app

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    gcc \
    curl \
    ca-certificates \
    default-libmysqlclient-dev \
    pkg-config \
    && rm -rf /var/lib/apt/lists/*

RUN useradd -ms /bin/bash workeruser

# Copy requirements first for better caching
COPY worker/requirements.txt /tmp/requirements.txt

RUN python -m pip install --upgrade pip setuptools wheel && \
    pip install -r /tmp/requirements.txt

# Copy the worker package
COPY worker/ /app/worker/
COPY tools/ /app/tools/

# Ensure data directory exists and set permissions
RUN mkdir -p /app/data && \
    chown -R workeruser:workeruser /app

USER workeruser

# Run the worker as a module
CMD ["python", "-m", "worker.main"]
