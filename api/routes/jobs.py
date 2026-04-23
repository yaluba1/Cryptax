from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from api.database import get_db
from api.pydantic_models import JobRequestBody, JobResponseBody, JobsResponseBody, JobListItem
from api.services.job_service import job_service
from fastapi.responses import FileResponse
from pathlib import Path
from loguru import logger
from typing import List

router = APIRouter()

@router.post("/jobs", response_model=JobResponseBody)
def create_job(job_request: JobRequestBody, db: Session = Depends(get_db)):
    """Create a new tax processing job."""
    try:
        job_id = job_service.create_job(db, job_request)
        return JobResponseBody(job_id=job_id)
    except Exception as e:
        logger.exception("Failed to create job")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/jobs", response_model=List[JobListItem])
def list_jobs(acc: str = Query(..., description="Account holder email"), db: Session = Depends(get_db)):
    """List all jobs for an account holder."""
    if not acc:
        raise HTTPException(status_code=400, detail="Account holder email (acc) is required")
    
    jobs = job_service.get_jobs_for_account(db, acc)
    return jobs

@router.get("/documents/{document_id}/download")
def download_document(document_id: str, db: Session = Depends(get_db)):
    """Download a document by ID."""
    doc = job_service.get_document(db, document_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    
    file_path = Path(doc.storage_path)
    if not file_path.exists():
        logger.error(f"File not found at path: {doc.storage_path}")
        raise HTTPException(status_code=404, detail="File not found on storage")
    
    return FileResponse(
        path=file_path,
        filename=doc.original_filename,
        media_type=doc.mime_type
    )
