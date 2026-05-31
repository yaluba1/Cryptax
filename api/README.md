# CrypTax API

The CrypTax API is a FastAPI-based service responsible for managing cryptocurrency tax processing jobs. It acts as the orchestration layer between the user (frontend) and the asynchronous processing worker.

## Key Responsibilities

- **Job Management**: Creation, status tracking, and history of tax jobs.
- **Document Management**: Registration and secure download of generated tax reports.
- **Queue Orchestration**: Enqueueing processing tasks into Redis (RQ).
- **Validation**: Strict validation of job parameters (country, language, exchange, etc.) using JSON schemas and Pydantic.

## Tech Stack

- **Framework**: FastAPI
- **Database**: SQLAlchemy (MariaDB/MySQL)
- **Task Queue**: Redis Queue (RQ)
- **Logging**: Loguru
- **Validation**: Pydantic

## Core Endpoints

- **Health Check**: `GET /api/v1/health` - System status.
- **Job Creation**: `POST /api/v1/jobs` - Create a new tax processing job. If `has_bot_activity` is `true`, the job is gated (created in `pending` state but not enqueued immediately in RQ). JWT required.
- **Bot CSV Upload**: `POST /api/v1/jobs/{job_id}/bot-activity` - Upload Binance bot CSV files. After successfully saving the files, the job is enqueued in the Redis queue for unified processing. Form-data with `files`, `api_key`, and `api_secret` is required. JWT required.
- **Job Listing**: `GET /api/v1/jobs` - List jobs for an account (JWT required).
- **Job Deletion**: `DELETE /api/v1/jobs/{job_id}` - Remove a job and its data (JWT required).
- **Document Download**: `GET /api/v1/documents/{id}/download` - Download reports (JWT required).

## Getting Started

### Configuration

Configure the environment variables in `.env` (or use `api/config.py` defaults):

- `MARIADB_HOST`, `MARIADB_USER`, `MARIADB_PASSWORD`, `MARIADB_DATABASE`
- `REDIS_HOST`, `REDIS_PORT`

### Running Locally

```bash
# From the root directory
uv run uvicorn api.main:app --reload --host localhost --port 8000
```

The API documentation will be available at `http://localhost:8000/docs`.

## Testing

Tests use `pytest` and a shared `conftest.py` that sets up a test database.

```bash
# Run all API tests
pytest api/tests

# Run a specific test file
pytest api/tests/test_jobs.py

# Run with coverage
pytest --cov=api api/tests
```

## Directory Structure

- `routes/`: API endpoint definitions.
- `services/`: Business logic (JobService, etc.).
- `models.py`: SQLAlchemy database models.
- `pydantic_models.py`: Pydantic schemas for request/response validation.
- `rq_service.py`: Redis Queue integration.
- `schemas/`: Raw JSON schemas for external validation.
