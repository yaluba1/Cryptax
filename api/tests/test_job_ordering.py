import pytest
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient
from api.main import app
from api.database import get_db

client = TestClient(app)

@patch("api.services.job_service.rq_service.enqueue_job")
def test_create_job_db_failure_prevents_redis(mock_enqueue):
    # Mock database session to fail on commit
    mock_db = MagicMock()
    mock_db.commit.side_effect = Exception("Database Commit Failed")
    app.dependency_overrides[get_db] = lambda: mock_db
    
    job_payload = {
        "country": "ES",
        "exchange": "binance",
        "year": 2023,
        "account_holder": "test@example.com",
        "uid": "user123",
        "api_key": "key",
        "api_secret": "secret",
        "fiat": "EUR"
    }
    
    with pytest.raises(Exception, match="Database Commit Failed"):
        client.post("/api/v1/jobs", json=job_payload)
    
    # Verify Redis Enqueue was NOT called
    assert not mock_enqueue.called
    
    app.dependency_overrides.clear()

@patch("api.services.job_service.rq_service.enqueue_job")
def test_create_job_success_order(mock_enqueue):
    # Mock database session
    mock_db = MagicMock()
    # We want to verify that commit happened BEFORE enqueue
    # We can use a side effect to check mock_enqueue.called
    def mock_commit():
        assert not mock_enqueue.called
        return None
    
    mock_db.commit.side_effect = mock_commit
    app.dependency_overrides[get_db] = lambda: mock_db
    
    job_payload = {
        "country": "ES",
        "exchange": "binance",
        "year": 2023,
        "account_holder": "test@example.com",
        "uid": "user123",
        "api_key": "key",
        "api_secret": "secret",
        "fiat": "EUR"
    }
    
    response = client.post("/api/v1/jobs", json=job_payload)
    assert response.status_code == 200
    
    # Verify Redis Enqueue WAS called AFTER commit
    assert mock_enqueue.called
    
    app.dependency_overrides.clear()
