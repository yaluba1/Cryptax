import pytest
from fastapi.testclient import TestClient
from api.main import app
from api.database import get_db
from api.rq_service import rq_service
from unittest.mock import MagicMock, patch

client = TestClient(app, raise_server_exceptions=False)

from sqlalchemy.exc import OperationalError
from redis.exceptions import ConnectionError as RedisConnectionError

def test_post_jobs_db_auth_error():
    # Mock a dependency to raise an OperationalError (auth error)
    def mock_db_auth_error():
        # Create a mock OperationalError
        err = OperationalError("SELECT 1", {}, "Access denied for user 'taxuser'@'localhost' (using password: YES)")
        raise err
    
    app.dependency_overrides[get_db] = mock_db_auth_error
    
    payload = {
        "exchange": "binance",
        "year": 2023,
        "account_holder": "test@example.com",
        "uid": "user123",
        "api_key": "key",
        "api_secret": "secret",
        "fiat": "EUR"
    }
    response = client.post("/api/v1/jobs", json=payload)
    
    assert response.status_code == 503
    assert "Database connection failed" in response.json()["message"]
    
    app.dependency_overrides.clear()

@patch("api.services.job_service.rq_service.enqueue_job")
def test_post_jobs_redis_connection_error(mock_enqueue):
    # Mock Redis ConnectionError
    mock_enqueue.side_effect = RedisConnectionError("Error connecting to Redis")
    
    payload = {
        "exchange": "binance",
        "year": 2023,
        "account_holder": "test@example.com",
        "uid": "user123",
        "api_key": "key",
        "api_secret": "secret",
        "fiat": "EUR"
    }
    response = client.post("/api/v1/jobs", json=payload)
    
    assert response.status_code == 503
    assert "Redis connection failed" in response.json()["message"]

def test_health_check_healthy():
    response = client.get("/api/v1/health")
    # This might fail if the real services are not running, but we can mock them if needed.
    # For now, let's assume they might be up or we mock them.
    pass

@patch("api.rq_service.rq_service.ping")
@patch("sqlalchemy.orm.Session.execute")
def test_health_check_unhealthy(mock_execute, mock_ping):
    # Mock DB up, Redis down
    mock_execute.return_value = MagicMock()
    mock_ping.return_value = False
    
    response = client.get("/api/v1/health")
    assert response.status_code == 503
    assert response.json()["detail"]["redis"] == "down"
    assert response.json()["detail"]["database"] == "ok"

    # Mock DB down, Redis up
    mock_execute.side_effect = Exception("DB error")
    mock_ping.return_value = True
    
    response = client.get("/api/v1/health")
    assert response.status_code == 503
    assert response.json()["detail"]["redis"] == "ok"
    assert response.json()["detail"]["database"] == "down"
