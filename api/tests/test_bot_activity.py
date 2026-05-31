import pytest
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient
from api.main import app
from api.database import get_db
from api.auth import get_current_user
import io

client = TestClient(app)

async def mock_get_current_user():
    return "user123"

@patch("api.services.job_service.rq_service.enqueue_job")
def test_create_job_with_bot_activity_gating(mock_enqueue):
    """Test that a job with has_bot_activity=true is gated and not enqueued immediately."""
    mock_db = MagicMock()
    app.dependency_overrides[get_db] = lambda: mock_db
    app.dependency_overrides[get_current_user] = mock_get_current_user
    
    job_payload = {
        "country": "ES",
        "exchange": "binance",
        "year": 2023,
        "account_holder": "test@example.com",
        "uid": "user123",
        "api_key": "key123",
        "api_secret": "secret123",
        "fiat": "EUR",
        "has_bot_activity": True
    }
    
    response = client.post("/api/v1/jobs", json=job_payload)
    
    assert response.status_code == 200
    assert "job_id" in response.json()
    assert not mock_enqueue.called  # Gating works! Not enqueued immediately.
    assert mock_db.add.called
    assert mock_db.commit.called
    
    app.dependency_overrides.clear()

@patch("api.services.job_service.rq_service.enqueue_job")
def test_upload_bot_activity_file_and_enqueue(mock_enqueue):
    """Test that uploading a bot CSV file successfully registers it and triggers enqueuing."""
    mock_db = MagicMock()
    app.dependency_overrides[get_db] = lambda: mock_db
    app.dependency_overrides[get_current_user] = mock_get_current_user
    
    # Mock return values for DB query
    mock_job = MagicMock()
    mock_job.id = "uuid-123"
    mock_job.uid = "user123"
    mock_db.query.return_value.filter.return_value.first.return_value = mock_job
    
    # Create fake CSV file data
    csv_data = io.BytesIO(b"Strategy_Id,Pair,Side,Time,OrderNo,Order Amount,Executed,Trading total,Status\n1,SOLUSDC,BUY,2025-01-01 10:00:00,O1,0.199SOL,0.199SOL,20.123USDC,FILLED")
    
    # Trigger files upload endpoint
    response = client.post(
        "/api/v1/jobs/uuid-123/bot-activity",
        data={
            "api_key": "key123",
            "api_secret": "secret123"
        },
        files={
            "files": ("bot_activity_2025.csv", csv_data, "text/csv")
        }
    )
    
    assert response.status_code == 200
    assert response.json()["message"] == "Files uploaded successfully and job enqueued for processing."
    assert mock_enqueue.called  # Successfully enqueued after upload!
    
    app.dependency_overrides.clear()
