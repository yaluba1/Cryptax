import pytest
from fastapi.testclient import TestClient
from api.main import app
from api.auth import get_current_user

client = TestClient(app)

def test_jobs_unauthorized():
    """Verify that jobs endpoint returns 401 without auth."""
    response = client.get("/api/v1/jobs?acc=test@example.com")
    assert response.status_code == 401

def test_create_job_unauthorized():
    """Verify that create job endpoint returns 401 without auth."""
    response = client.post("/api/v1/jobs", json={})
    assert response.status_code == 401

def test_download_document_unauthorized():
    """Verify that download document endpoint returns 401 without auth."""
    response = client.get("/api/v1/documents/123/download")
    assert response.status_code == 401

def test_health_public():
    """Verify that health endpoint remains public."""
    response = client.get("/api/v1/health")
    assert response.status_code == 200
