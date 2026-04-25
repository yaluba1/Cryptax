"""
Service for interacting with the database from the worker.
Handles job retrieval, status updates, and event logging.
"""

from sqlalchemy.orm import Session
from datetime import datetime
from worker.models import Job, JobEvent, Document
from worker.logging_config import logger
import json

class JobService:
    @staticmethod
    def get_job_by_id(db: Session, job_id: str) -> Job:
        """Fetch a job by its UUID."""
        return db.query(Job).filter(Job.id == job_id).first()

    @staticmethod
    def update_job_status(db: Session, job_id: str, status: str, error_message: str = None):
        """Update the status of a job and set timestamps if needed."""
        job = db.query(Job).filter(Job.id == job_id).first()
        if not job:
            logger.error("Job {} not found for status update", job_id)
            return

        job.status = status
        if status == "processing":
            job.started_at = datetime.now()
        elif status in ["done", "error"]:
            job.finished_at = datetime.now()
            if error_message:
                job.error_message = error_message

        db.commit()
        logger.info("Job {} status updated to {}", job_id, status)

    @staticmethod
    def add_job_event(db: Session, job_id: str, event_type: str, message: str = None, payload: dict = None):
        """Log a new event for a specific job."""
        event = JobEvent(
            job_id=job_id,
            event_type=event_type,
            message=message,
            event_payload_json=payload or {}
        )
        db.add(event)
        db.commit()
        logger.debug("Event '{}' logged for job {}", event_type, job_id)

    @staticmethod
    def register_document(db: Session, job_id: str, doc_type: str, storage_path: str, filename: str, mime_type: str, size: int):
        """Register a generated document in the database."""
        import uuid
        doc_id = str(uuid.uuid4())
        
        new_doc = Document(
            id=doc_id,
            job_id=job_id,
            document_type=doc_type,
            storage_path=storage_path,
            original_filename=filename,
            mime_type=mime_type,
            size_bytes=size,
            created_at=datetime.now()
        )
        db.add(new_doc)
        db.commit()
        logger.info("Document registered: {} (Type: {})", filename, doc_type)
        return doc_id

    @staticmethod
    def update_result_payload(db: Session, job_id: str, result_payload: dict):
        """Update the result payload of a job with document IDs etc."""
        job = db.query(Job).filter(Job.id == job_id).first()
        if job:
            job.result_payload_json = result_payload
            db.commit()
            logger.debug("Result payload updated for job {}", job_id)

job_service = JobService()
