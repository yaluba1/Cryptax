"""
Unit tests for the job processor.
Mocks external tools (DaLI, RP2, Email) to test the internal workflow.
"""

import pytest
from unittest.mock import MagicMock, patch
from pathlib import Path
from worker.services.job_processor import process_job
from worker.models import Job, JobStatusEnum

@pytest.fixture
def mock_db():
    db = MagicMock()
    return db

@pytest.fixture
def mock_job():
    job = Job(
        id="test-job-id",
        account_holder="test@example.com",
        exchange="binance",
        country="ES",
        tax_year=2023,
        request_payload_json={"fiat": "EUR"},
        status="pending"
    )
    return job

@patch("worker.services.job_processor.get_db_session")
@patch("worker.services.job_processor.job_service")
@patch("worker.services.job_processor.dali_service")
@patch("worker.services.job_processor.rp2_service")
@patch("worker.services.job_processor.email_service")
def test_process_job_success(
    mock_email, mock_rp2, mock_dali, mock_job_service, mock_get_db,
    mock_db, mock_job
):
    # Setup mocks
    mock_get_db.return_value = mock_db
    mock_job_service.get_job_by_id.return_value = mock_job
    mock_dali.run_dali.return_value = True
    mock_rp2.run_rp2.return_value = True
    mock_email.send_job_completed_email.return_value = True
    
    # Payload
    payload = {
        "job_id": "test-job-id",
        "api_key": "key",
        "api_secret": "secret"
    }
    
    # Run
    process_job(payload)
    
    # Assertions
    mock_job_service.update_job_status.assert_any_call(mock_db, "test-job-id", "processing")
    mock_job_service.update_job_status.assert_any_call(mock_db, "test-job-id", "done")
    mock_dali.run_dali.assert_called_once()
    mock_rp2.run_rp2.assert_called_once()
    mock_email.send_job_completed_email.assert_called_once()
    
    # Verify events
    assert mock_job_service.add_job_event.call_count >= 5

@patch("worker.services.job_processor.get_db_session")
@patch("worker.services.job_processor.job_service")
@patch("worker.services.job_processor.dali_service")
def test_process_job_failure(
    mock_dali, mock_job_service, mock_get_db,
    mock_db, mock_job
):
    # Setup mocks
    mock_get_db.return_value = mock_db
    mock_job_service.get_job_by_id.return_value = mock_job
    mock_dali.run_dali.return_value = False # Simulate failure
    
    # Payload
    payload = {
        "job_id": "test-job-id",
        "api_key": "key",
        "api_secret": "secret"
    }
    
    # Run
    process_job(payload)
    
    # Assertions
    mock_job_service.update_job_status.assert_any_call(mock_db, "test-job-id", "error", error_message="DaLI execution failed.")
    mock_job_service.add_job_event.assert_any_call(mock_db, "test-job-id", "job_failed", "Error: DaLI execution failed.")
