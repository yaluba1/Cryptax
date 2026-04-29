FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    WORKER_HOME=worker/

WORKDIR ${WORKER_HOME}

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    gcc \
    curl \
    ca-certificates \
    default-libmysqlclient-dev \
    pkg-config \
    && rm -rf /var/lib/apt/lists/*

RUN useradd -ms /bin/bash workeruser

COPY worker/requirements.txt /tmp/requirements.txt

RUN python -m pip install --upgrade pip setuptools wheel && \
    pip install -r /tmp/requirements.txt

# RUN mkdir -p /data/input /data/output /data/tmp && \
#     chown -R workeruser:workeruser ${WORKER_HOME} /data

COPY . .
RUN chown -R workeruser:workeruser ../worker

USER workeruser

# CMD ["python", "./main.py"]