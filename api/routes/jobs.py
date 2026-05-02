from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from api.database import get_db
from api.pydantic_models import JobRequestBody, JobResponseBody, JobsResponseBody, JobListItem
from api.services.job_service import job_service
from api.auth import get_current_user
from fastapi.responses import FileResponse
from pathlib import Path
from loguru import logger
from typing import List

router = APIRouter()

@router.post("/jobs", response_model=JobResponseBody)
def create_job(
    job_request: JobRequestBody, 
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user)
):
    """Create a new tax processing job."""
    # Enforce UID equality between JWT sub and request body
    if job_request.uid != user_id:
        logger.warning(f"UID mismatch: request={job_request.uid}, jwt={user_id}")
        raise HTTPException(
            status_code=401, 
            detail="UID in request does not match UID in authentication token."
        )
    
    job_id = job_service.create_job(db, job_request)
    return JobResponseBody(job_id=job_id)

@router.get("/jobs", response_model=List[JobListItem])
def list_jobs(
    acc: str = Query(..., description="Account holder email"), 
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user)
):
    """List all jobs for an account holder."""
    if not acc:
        raise HTTPException(status_code=400, detail="Account holder email (acc) is required")
    
    # Filter by both email and UID from JWT
    jobs = job_service.get_jobs_for_account(db, acc, user_id)
    return jobs

@router.get("/documents/{document_id}/download")
def download_document(
    document_id: str, 
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user)
):
    """Download a document by ID."""
    # Verify ownership via UID from JWT
    doc = job_service.get_document(db, document_id, user_id)
    if not doc:
        logger.warning(f"Document {document_id} not found or not owned by user {user_id}")
        raise HTTPException(status_code=401, detail="Document not found or access denied.")
    
    file_path = Path(doc.storage_path)
    if not file_path.exists():
        logger.error(f"File not found at path: {doc.storage_path}")
        raise HTTPException(status_code=404, detail="File not found on storage")
    
    return FileResponse(
        path=file_path,
        filename=doc.original_filename,
        media_type=doc.mime_type
    )
