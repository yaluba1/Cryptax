import uuid
from sqlalchemy.orm import Session
from api.models import Job, JobEvent, Document
from api.pydantic_models import JobRequestBody, InternalJob, JobListItem, DocumentInfo, JobStatusEnum
from api.rq_service import rq_service
from loguru import logger
import json
from datetime import datetime

class JobService:
    def create_job(self, db: Session, job_request: JobRequestBody) -> str:
        """Create a new job and enqueue it."""
        job_id = str(uuid.uuid4())
        
        # 1. Create Internal Job Object
        internal_job = InternalJob(
            job_id=job_id,
            exchange=job_request.exchange,
            year=job_request.year,
            account_holder=job_request.account_holder,
            uid=job_request.uid,
            api_key=job_request.api_key,
            api_secret=job_request.api_secret,
            fiat=job_request.fiat
        )
        
        # 2. Queue in RQ
        rq_service.enqueue_job(internal_job)
        
        # 3. Store in jobs table
        new_job = Job(
            id=job_id,
            exchange=job_request.exchange.value,
            tax_year=job_request.year,
            account_holder=job_request.account_holder,
            uid=job_request.uid,
            status=JobStatusEnum.pending.value,
            request_payload_json=job_request.model_dump(),
            result_payload_json={},
            error_message="",
            created_at=datetime.now()
        )
        db.add(new_job)
        
        # 4. Store event in job_events table
        event = JobEvent(
            job_id=job_id,
            event_type="created",
            event_payload_json={}
        )
        db.add(event)
        
        db.commit()
        logger.info(f"Job {job_id} created and stored in database.")
        
        return job_id

    def get_jobs_for_account(self, db: Session, account_holder: str) -> list[JobListItem]:
        """Retrieve all jobs for an account holder."""
        jobs = db.query(Job).filter(Job.account_holder == account_holder).all()
        
        result = []
        for job in jobs:
            docs = []
            if job.status == JobStatusEnum.done.value:
                # Retrieve documents for this job
                documents = db.query(Document).filter(Document.job_id == job.id).all()
                docs = [
                    DocumentInfo(
                        document_id=doc.id,
                        document_type=doc.document_type
                    ) for doc in documents
                ]
            
            # Extract fiat from request_payload_json
            request_payload = job.request_payload_json
            if isinstance(request_payload, str):
                request_payload = json.loads(request_payload)
            fiat = request_payload.get("fiat", "USD")
            
            result.append(JobListItem(
                job_id=job.id,
                exchange=job.exchange,
                year=job.tax_year,
                fiat=fiat,
                status=job.status,
                documents=docs
            ))
        
        return result

    def get_document(self, db: Session, document_id: str) -> Document:
        """Retrieve document metadata by ID."""
        return db.query(Document).filter(Document.id == document_id).first()

job_service = JobService()
