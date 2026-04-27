"""
Main entry point for the CrypTax worker service.
Initializes the RQ worker and starts listening for jobs.
"""

import redis
import sys
import os
import signal
from rq import Worker, Queue, SimpleWorker
from worker.config import settings
from worker.logging_config import logger

# Set log level for DaLI/RP2
os.environ["LOG_LEVEL"] = "DEBUG"

def signal_handler(sig, frame):
    """
    Handles termination signals to stop the worker gracefully.
    """
    logger.info("Termination signal received. Shutting down worker...")
    sys.exit(0)

# Register signal handlers
signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)

def start_worker():
    """
    Connects to Redis and starts the RQ worker loop.
    """
    logger.info("Initializing CrypTax Worker...")
    
    try:
        # Create Redis connection
        redis_conn = redis.Redis(
            host=settings.redis_host,
            port=settings.redis_port,
            db=settings.redis_db
        )
        
        # Test connection
        redis_conn.ping()
        logger.info("Connected to Redis at {}:{}", settings.redis_host, settings.redis_port)
        
        # Start worker
        # On Windows, we must use SimpleWorker because os.fork() is not supported
        worker_class = SimpleWorker if os.name == 'nt' else Worker
        worker = worker_class([settings.rq_queue_name], connection=redis_conn)
        logger.info("Worker started using {}. Listening on queue: '{}'", worker_class.__name__, settings.rq_queue_name)
        worker.work()
            
    except redis.exceptions.ConnectionError as e:
        logger.error("Could not connect to Redis: {}. Ensure Redis is running and host/port are correct.", str(e))
        sys.exit(1)
    except Exception as e:
        logger.error("An unexpected error occurred while starting the worker: {}", str(e))
        logger.exception(e)
        sys.exit(1)

if __name__ == "__main__":
    start_worker()
