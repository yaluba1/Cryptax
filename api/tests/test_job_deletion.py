import pytest
from fastapi.testclient import TestClient
from api.main import app
from api.database import get_db
from api.auth import get_current_user
from api.config import settings
from unittest.mock import MagicMock, patch
import shutil
import os

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

def test_delete_job_success(mock_db):
    """DELETE /jobs/{id} should succeed if owner calls it."""
    app.dependency_overrides[get_current_user] = lambda: USER_A
    job_id = "job-123"
    
    # Mock job existence and ownership
    mock_job = MagicMock()
    mock_job.id = job_id
    mock_job.uid = USER_A
    mock_db.query.return_value.filter.return_value.first.return_value = mock_job
    
    # Create a dummy directory to test deletion
    job_dir = settings.jobs_data_dir / job_id
    job_dir.mkdir(parents=True, exist_ok=True)
    assert job_dir.exists()
    
    response = client.delete(f"/api/v1/jobs/{job_id}")
    
    assert response.status_code == 204
    assert not job_dir.exists()
    assert mock_db.delete.called
    assert mock_db.commit.called

def test_delete_job_unauthorized(mock_db):
    """DELETE /jobs/{id} should return 401 if wrong user calls it."""
    app.dependency_overrides[get_current_user] = lambda: USER_B # User B tries to delete User A's job
    job_id = "job-123"
    
    # Mock job existence but different owner
    mock_job = MagicMock()
    mock_job.id = job_id
    mock_job.uid = USER_A
    mock_db.query.return_value.filter.return_value.first.return_value = mock_job
    
    response = client.delete(f"/api/v1/jobs/{job_id}")
    
    assert response.status_code == 401
    assert "Access denied" in response.json()["detail"]

def test_delete_job_not_found(mock_db):
    """DELETE /jobs/{id} should return 404 if job doesn't exist."""
    app.dependency_overrides[get_current_user] = lambda: USER_A
    job_id = "non-existent"
    
    mock_db.query.return_value.filter.return_value.first.return_value = None
    
    response = client.delete(f"/api/v1/jobs/{job_id}")
    
    assert response.status_code == 404
    assert "Job not found" in response.json()["detail"]
