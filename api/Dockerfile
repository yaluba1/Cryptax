FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    APP_HOME=/app \
    PYTHONPATH=/app

WORKDIR ${APP_HOME}

RUN useradd -ms /bin/bash appuser


COPY api/requirements.txt /tmp/requirements.txt

RUN python -m pip install --upgrade pip setuptools wheel && \
    pip install -r /tmp/requirements.txt

RUN mkdir -p /data/input /data/output /data/tmp /app/logs && \
    chown -R appuser:appuser ${APP_HOME} /data && \
    chown -R appuser:appuser /app/logs

COPY api ${APP_HOME}/api
RUN chown -R appuser:appuser ${APP_HOME}/api

USER appuser

EXPOSE 8000

CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]