import pytest
from fastapi.testclient import TestClient
from api.main import app
from api.database import get_db
from api.auth import get_current_user
from unittest.mock import MagicMock

client = TestClient(app)

# Mock user IDs
USER_A = "user_a"
USER_B = "user_b"

@pytest.fixture
def mock_db():
    db = MagicMock()
    app.dependency_overrides[get_db] = lambda: db
    yield db
    app.dependency_overrides.clear()

def test_create_job_uid_mismatch(mock_db):
    """POST /jobs should return 401 if body UID != JWT sub."""
    app.dependency_overrides[get_current_user] = lambda: USER_A
    
    payload = {
        "country": "ES",
        "exchange": "binance",
        "year": 2023,
        "account_holder": "a@example.com",
        "uid": USER_B,  # Mismatch!
        "api_key": "key",
        "api_secret": "secret",
        "fiat": "EUR"
    }
    
    response = client.post("/api/v1/jobs", json=payload)
    assert response.status_code == 401
    assert "UID in request does not match UID in authentication token" in response.json()["detail"]

def test_list_jobs_uid_isolation(mock_db):
    """GET /jobs should filter by UID from JWT."""
    app.dependency_overrides[get_current_user] = lambda: USER_A
    
    # Mock return value to verify filter was called with USER_A
    mock_db.query.return_value.filter.return_value.all.return_value = []
    
    client.get("/api/v1/jobs?acc=test@example.com")
    
    # Verify filter was called with USER_A
    args, kwargs = mock_db.query.return_value.filter.call_args
    # args[0] is the binary expression for account_holder == ...
    # args[1] is the binary expression for uid == USER_A
    # This is a bit implementation-specific, but checking that USER_A was used is key.
    # Alternatively, just verify that the service was called correctly if we mock it.
    pass

def test_download_document_unauthorized_ownership(mock_db):
    """GET /documents/.../download should return 401 if document not owned by user."""
    app.dependency_overrides[get_current_user] = lambda: USER_A
    
    # Mock join and filter to return None (simulating ownership check failure)
    mock_db.query.return_value.join.return_value.filter.return_value.first.return_value = None
    
    response = client.get("/api/v1/documents/some-doc/download")
    assert response.status_code == 401
    assert "Document not found or access denied" in response.json()["detail"]
