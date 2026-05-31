from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File, Form
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

@router.delete("/jobs/{job_id}", status_code=204)
def delete_job(
    job_id: str, 
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user)
):
    """Delete a tax processing job and its associated data."""
    result = job_service.delete_job(db, job_id, user_id)
    
    if result is None:
        raise HTTPException(status_code=404, detail="Job not found")
    
    if result is False:
        logger.warning(f"Unauthorized deletion attempt for job {job_id} by user {user_id}")
        raise HTTPException(
            status_code=401, 
            detail="Access denied. You do not own this job."
        )
    
    return None # 204 No Content

@router.post("/jobs/{job_id}/bot-activity", status_code=200)
async def upload_bot_activity(
    job_id: str,
    api_key: str = Form(..., description="Exchange API Key"),
    api_secret: str = Form(..., description="Exchange API Secret"),
    files: List[UploadFile] = File(...),
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user)
):
    """Upload Binance bot CSV files for a job and trigger delayed processing."""
    if not files:
        raise HTTPException(status_code=400, detail="No files provided.")
    
    try:
        # Save all uploaded files first
        for file in files:
            content = await file.read()
            job_service.save_bot_activity_file(
                db=db,
                job_id=job_id,
                filename=file.filename,
                content=content,
                mime_type=file.content_type,
                size=len(content),
                uid=user_id
            )
            
        # Trigger processing by enqueuing to RQ after saving all files
        job_service.enqueue_delayed_job(
            db=db,
            job_id=job_id,
            api_key=api_key,
            api_secret=api_secret,
            uid=user_id
        )
        
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except PermissionError as e:
        raise HTTPException(status_code=401, detail=str(e))
    except Exception as e:
        logger.error(f"Error handling bot CSV upload for job {job_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error while saving files.")
        
    return {"message": "Files uploaded successfully and job enqueued for processing."}
