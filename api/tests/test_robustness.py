import pytest
from fastapi.testclient import TestClient
from api.main import app
from api.database import get_db
from unittest.mock import MagicMock

client = TestClient(app, raise_server_exceptions=False)

def test_global_exception_handler():
    # Mock a dependency to raise an exception
    def mock_db_exception():
        raise Exception("Database connection failed")
    
    app.dependency_overrides[get_db] = mock_db_exception
    
    response = client.get("/api/v1/jobs?acc=test@example.com")
    
    assert response.status_code == 503
    assert response.json() == {"message": "Service Unavailable. Please try again later."}
    
    app.dependency_overrides.clear()
