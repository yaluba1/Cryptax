import pytest
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient
from api.main import app
from api.database import get_db

client = TestClient(app)

@patch("api.services.job_service.rq_service.enqueue_job")
def test_create_job(mock_enqueue):
    # Mock database session
    mock_db = MagicMock()
    app.dependency_overrides[get_db] = lambda: mock_db
    
    job_payload = {
        "exchange": "binance",
        "year": 2023,
        "account_holder": "test@example.com",
        "uid": "user123",
        "api_key": "key123",
        "api_secret": "secret123",
        "fiat": "EUR"
    }
    
    response = client.post("/api/v1/jobs", json=job_payload)
    
    assert response.status_code == 200
    assert "job_id" in response.json()
    assert mock_enqueue.called
    assert mock_db.add.called
    assert mock_db.commit.called
    
    # Cleanup overrides
    app.dependency_overrides.clear()

def test_list_jobs():
    mock_db = MagicMock()
    app.dependency_overrides[get_db] = lambda: mock_db
    
    # Mock return value of query
    mock_job = MagicMock()
    mock_job.id = "uuid-123"
    mock_job.exchange = "binance"
    mock_job.tax_year = 2023
    mock_job.account_holder = "test@example.com"
    mock_job.status = "pending"
    mock_job.request_payload_json = {"fiat": "EUR"}
    
    mock_db.query.return_value.filter.return_value.all.return_value = [mock_job]
    
    response = client.get("/api/v1/jobs?acc=test@example.com")
    
    assert response.status_code == 200
    assert len(response.json()) == 1
    assert response.json()[0]["job_id"] == "uuid-123"
    assert response.json()[0]["fiat"] == "EUR"
    
    app.dependency_overrides.clear()
