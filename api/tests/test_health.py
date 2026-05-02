from fastapi.testclient import TestClient
from api.main import app
from unittest.mock import patch, MagicMock
from api.database import get_db

client = TestClient(app)

def test_health_check():
    # Mock rq_service.ping to return True to avoid actual redis connection
    with patch("api.routes.health.rq_service.ping", return_value=True):
        # Mock DB execute
        mock_db = MagicMock()
        app.dependency_overrides[get_db] = lambda: mock_db
        
        response = client.get("/api/v1/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert data["database"] == "ok"
        assert data["redis"] == "ok"
        
        app.dependency_overrides.clear()
