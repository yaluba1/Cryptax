from redis import Redis
from rq import Queue
from api.config import settings
from api.pydantic_models import InternalJob
from loguru import logger
import json

class RQService:
    def __init__(self):
        self.redis_conn = Redis(
            host=settings.redis_host,
            port=settings.redis_port,
            db=settings.redis_db
        )
        self.queue = Queue(settings.rq_queue_name, connection=self.redis_conn)
        logger.info(f"Connected to Redis at {settings.redis_host}:{settings.redis_port} (DB {settings.redis_db}), Queue: {settings.rq_queue_name}")

    def enqueue_job(self, internal_job: InternalJob):
        """Enqueue a job for processing."""
        # Convert Pydantic model to dict for storage in Redis
        job_data = internal_job.model_dump()
        
        # Enqueue the job. 
        # Note: We need a worker function to process this. 
        # For now, we just enqueue the data as a task to a hypothetical worker function.
        # The prompt says "queue the internal job object in redis for processing".
        # In RQ, we usually enqueue a function call.
        # I'll use a placeholder function 'process_tax_job'.
        
        try:
            job = self.queue.enqueue("worker.process_tax_job", job_data)
            logger.info(f"Enqueued job {internal_job.job_id} to RQ. RQ Job ID: {job.id}")
            return job.id
        except Exception as e:
            logger.error(f"Failed to enqueue job {internal_job.job_id}: {str(e)}")
            raise

rq_service = RQService()
