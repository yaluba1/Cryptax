"""
Main job processing logic for the worker.
Coordinates DB updates, tool execution (DaLI/RP2), and notifications.
"""

import os
from pathlib import Path
from rq import get_current_job
from worker.db import get_db_session
from worker.services.job_service import job_service
from worker.services.dali_service import dali_service
from worker.services.rp2_service import rp2_service
from worker.services.email_service import email_service
from worker.logging_config import logger

def process_job(job_payload: dict):
    """
    Main entry point for a queued job.
    Expects payload: {'job_id': str, 'api_key': str, 'api_secret': str}
    """
    # Safety: Increase job timeout to 1 hour if running in an RQ worker
    job_obj = get_current_job()
    if job_obj:
        logger.debug("Increasing current RQ job timeout to 3600s")
        job_obj.timeout = 3600
        # On some RQ versions, we might need to save or it might not work at runtime,
        # but it doesn't hurt.
    
    job_id = job_payload.get("job_id")
    api_key = job_payload.get("api_key")
    api_secret = job_payload.get("api_secret")
    
    if not job_id:
        logger.error("Job payload missing 'job_id': {}", job_payload)
        return

    logger.info("Processing job: {}", job_id)
    db = get_db_session()
    
    try:
        # 1. Fetch full job data from DB
        job = job_service.get_job_by_id(db, job_id)
        if not job:
            logger.error("Job {} not found in database.", job_id)
            return

        # 2. Update status to processing
        job_service.update_job_status(db, job_id, "processing")
        job_service.add_job_event(db, job_id, "job_started", f"Worker started processing job {job_id}")

        # 3. Create working directory
        job_dir = Path("./data/jobs") / job_id
        job_dir.mkdir(parents=True, exist_ok=True)
        logger.debug("Working directory created: {}", job_dir)

        # 4. Run DaLI
        job_service.add_job_event(db, job_id, "dali_started", "Executing DaLI to fetch transaction data")
        
        # Get fiat from request payload
        request_payload = job.request_payload_json
        fiat = request_payload.get("fiat", "USD")
        
        config_path = dali_service.generate_config(
            job_dir=job_dir,
            account_holder=job.account_holder,
            exchange=job.exchange,
            api_key=api_key,
            api_secret=api_secret,
            native_fiat=fiat
        )
        
        success = dali_service.run_dali(job.country, config_path, job_dir)
        if not success:
            raise RuntimeError("DaLI execution failed.")
            
        job_service.add_job_event(db, job_id, "dali_completed", "DaLI finished successfully")

        # 5. Run RP2
        job_service.add_job_event(db, job_id, "rp2_started", f"Executing RP2 for country {job.country}")
        
        success = rp2_service.run_rp2(
            country=job.country,
            input_dir=job_dir,
            output_dir=job_dir,
            from_date=f"{job.tax_year}-01-01",
            to_date=f"{job.tax_year}-12-31"
        )
        if not success:
            raise RuntimeError("RP2 execution failed.")
            
        job_service.add_job_event(db, job_id, "rp2_completed", "RP2 finished successfully")

        # 6. Register documents
        attachments = []
        result_metadata = {"documents": []}
        
        # Files to register
        # DaLI outputs: crypto_data.ods, crypto_data.ini (actually DaLI generates dali.ini, but dali_main generates a copy in output)
        # RP2 ES outputs: tax_report_es.ods
        
        files_to_register = [
            ("input_ods", "crypto_data.ods", "application/vnd.oasis.opendocument.spreadsheet"),
            ("config", "dali.ini", "text/plain")
        ]
        
        if job.country.upper() == "ES":
            files_to_register.append(("rp2_full_report", "tax_report_es.ods", "application/vnd.oasis.opendocument.spreadsheet"))
        
        for doc_type, filename, mime in files_to_register:
            file_path = job_dir / filename
            if file_path.exists():
                size = file_path.stat().st_size
                doc_id = job_service.register_document(
                    db=db,
                    job_id=job_id,
                    doc_type=doc_type,
                    storage_path=str(file_path),
                    filename=filename,
                    mime_type=mime,
                    size=size
                )
                attachments.append(file_path)
                result_metadata["documents"].append({"id": doc_id, "type": doc_type, "filename": filename})
        
        job_service.update_result_payload(db, job_id, result_metadata)

        # 7. Finalize Job
        job_service.update_job_status(db, job_id, "done")
        job_service.add_job_event(db, job_id, "job_completed", "Job processed successfully")

        # 8. Send Email
        email_success = email_service.send_job_completed_email(
            recipient_email=job.account_holder,
            job_id=job_id,
            country=job.country,
            exchange=job.exchange,
            year=job.tax_year,
            attachments=attachments
        )
        
        if email_success:
            job_service.add_job_event(db, job_id, "email_sent", f"Email notification sent to {job.account_holder}")
        else:
            job_service.add_job_event(db, job_id, "email_failed", f"Failed to send email to {job.account_holder}")

    except Exception as e:
        error_msg = str(e)
        logger.error("Job {} failed: {}", job_id, error_msg)
        logger.exception(e)
        
        job_service.update_job_status(db, job_id, "error", error_message=error_msg)
        job_service.add_job_event(db, job_id, "job_failed", f"Error: {error_msg}")
        
    finally:
        db.close()
