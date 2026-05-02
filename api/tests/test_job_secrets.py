import pytest
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient
from api.main import app
from api.database import get_db
from api.auth import get_current_user
from api.pydantic_models import InternalJob

client = TestClient(app)

# Mock user for auth dependency
async def mock_get_current_user():
    return "user123"

@patch("api.services.job_service.rq_service.enqueue_job")
def test_create_job_country_handling(mock_enqueue):
    # Mock database session and auth
    mock_db = MagicMock()
    app.dependency_overrides[get_db] = lambda: mock_db
    app.dependency_overrides[get_current_user] = mock_get_current_user
    
    # 1. Test standard country (ES)
    job_payload = {
        "country": "ES",
        "exchange": "binance",
        "year": 2023,
        "account_holder": "test@example.com",
        "uid": "user123",
        "api_key": "SUPER_SECRET_KEY",
        "api_secret": "SUPER_SECRET_VALUE",
        "fiat": "EUR"
    }
    
    response = client.post("/api/v1/jobs", json=job_payload)
    assert response.status_code == 200
    job_id = response.json()["job_id"]
    
    # Verify Redis Enqueue
    internal_job = mock_enqueue.call_args[0][0]
    # Check that it ONLY has the 3 minimal fields
    job_dict = internal_job.model_dump()
    assert set(job_dict.keys()) == {"job_id", "api_key", "api_secret"}
    assert internal_job.job_id == job_id
    
    # Verify Database Storage
    job_added = next(call[0][0] for call in mock_db.add.call_args_list if hasattr(call[0][0], 'country'))
    assert job_added.country == "ES"
    
    # 2. Test GENERIC country with info
    mock_db.reset_mock()
    job_payload["country"] = "GENERIC"
    job_payload["generic"] = {
        "long_term_capital_gains_days": 365,
        "accounting_method": "FIFO"
    }
    
    response = client.post("/api/v1/jobs", json=job_payload)
    assert response.status_code == 200
    
    # Verify Redis Enqueue (still only 3 fields)
    internal_job = mock_enqueue.call_args[0][0]
    job_dict = internal_job.model_dump()
    assert set(job_dict.keys()) == {"job_id", "api_key", "api_secret"}
    
    # 3. Test GENERIC country WITHOUT info (should fail)
    job_payload.pop("generic")
    response = client.post("/api/v1/jobs", json=job_payload)
    assert response.status_code == 422 # Validation Error
    
    # Cleanup overrides
    app.dependency_overrides.clear()
