# CrypTax Worker

The CrypTax Worker is an asynchronous processing service based on Redis Queue (RQ). It consumes tax processing jobs from the queue, fetches transaction data from exchanges, and generates comprehensive tax reports.

## Key Responsibilities
- **Data Fetching**: Retrieval of transaction history from exchanges (Binance, etc.) via DaLI and REST APIs.
- **Price Enrichment**: Fetching historical spot prices for crypto assets at the time of transaction.
- **Transaction Resolution**: Merging transfers between wallets and resolving internal exchange events.
- **Robustness Layer**: Sanitizing missing data and recovering account balances to ensure RP2 stability.
- **Report Generation**: Executing the RP2 engine to generate tax reports (ODS format).
- **Notification**: Sending the final reports to users via email.

## Tech Stack
- **Engine**: DaLI (Data Link) & RP2 (Rational Profit 2)
- **Task Queue**: Redis Queue (RQ)
- **Email**: SMTP with MIME support
- **Logging**: Loguru

## Getting Started

### Configuration
Configure the environment variables in `.env`:
- `REDIS_HOST`, `REDIS_PORT`
- `EMAIL_SMTP_SVR`, `EMAIL_ACC_NAME`, `EMAIL_ACC_PWS` (for notifications)

### Running Locally
To start a worker and listen for jobs:
```bash
# From the root directory
python -m worker.main
```

## Testing

The worker includes unit and integration tests for the various processing services.

```bash
# Run all worker tests
pytest worker/tests

# Run a specific test file
pytest worker/tests/test_job_processor.py

# Test balance recovery and sanitization specifically
pytest worker/tests/test_dali_service.py
```

## Directory Structure
- `services/`: Core logic for data processing.
  - `job_processor.py`: Orchestrates the full lifecycle of a job.
  - `dali_service.py`: Wraps DaLI functionality and implements robustness fixes.
  - `rp2_service.py`: Wraps the RP2 engine.
  - `email_service.py`: Handles email notifications with attachments.
- `models.py`: Internal data models and state management.
- `db.py`: Database connection management for the worker.
- `main.py`: Entry point for the RQ worker process.
