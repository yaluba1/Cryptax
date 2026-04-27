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
        
        # 1. Store in jobs table (excluding secrets)
        payload = job_request.model_dump()
        payload.pop("api_key", None)
        payload.pop("api_secret", None)

        new_job = Job(
            id=job_id,
            lang=job_request.lang.value,
            country=job_request.country.value,
            exchange=job_request.exchange.value,
            tax_year=job_request.year,
            account_holder=job_request.account_holder,
            uid=job_request.uid,
            status=JobStatusEnum.pending.value,
            request_payload_json=payload,
            result_payload_json={},
            error_message="",
            created_at=datetime.now()
        )
        db.add(new_job)
        
        # 2. Store event in job_events table
        event = JobEvent(
            job_id=job_id,
            event_type="created",
            event_payload_json={}
        )
        db.add(event)
        
        # 3. Commit to database
        db.commit()
        logger.info(f"Job {job_id} created and stored in database.")
        
        # 4. Create Internal Job Object and Queue in RQ
        # We do this AFTER database commit. If Redis fails, the job is at least in the DB.
        internal_job = InternalJob(
            job_id=job_id,
            api_key=job_request.api_key,
            api_secret=job_request.api_secret
        )
        
        try:
            rq_service.enqueue_job(internal_job)
        except Exception as e:
            logger.error(f"Failed to enqueue job {job_id} in Redis: {str(e)}")
            # We don't raise here because the job IS created in DB. 
            # In a real system, we might want to update the job status to 'error' or 'failed_to_queue'.
        
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
            
            # Extract info from request_payload_json
            request_payload = job.request_payload_json
            if isinstance(request_payload, str):
                request_payload = json.loads(request_payload)
            fiat = request_payload.get("fiat", "USD")
            generic_data = request_payload.get("generic")
            generic = GenericInfo(**generic_data) if generic_data else None
            
            result.append(JobListItem(
                job_id=job.id,
                lang=job.lang,
                country=job.country,
                generic=generic,
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
