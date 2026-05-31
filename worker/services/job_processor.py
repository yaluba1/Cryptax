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
        attachments = []
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
        
        # NEW: Enriched workflow to avoid Kraken hanging/CSV problem and ensure high reliability
        if job.exchange.lower() in ['binance', 'binance.com', 'kraken']:
            logger.info("Using enriched {} workflow for job {}", job.exchange, job_id)
            
            # a. Get transactions directly from Exchange
            if job.exchange.lower() == 'kraken':
                job_service.add_job_event(db, job_id, "kraken_fetch", "Fetching raw transactions from Kraken REST API")
                transactions = dali_service.get_kraken_transactions(
                    account_holder=job.account_holder,
                    api_key=api_key,
                    api_secret=api_secret,
                    native_fiat=fiat,
                    country_code=job.country,
                    job_dir=job_dir
                )
            else:
                job_service.add_job_event(db, job_id, "binance_fetch", "Fetching raw transactions from Binance REST API")
                transactions = dali_service.get_binance_transactions(
                    account_holder=job.account_holder,
                    api_key=api_key,
                    api_secret=api_secret,
                    native_fiat=fiat,
                    country_code=job.country,
                    job_dir=job_dir
                )
                
                # Check for and merge Binance Bot activity CSVs
                bot_csv_dir = job_dir / "bot_activity"
                if bot_csv_dir.exists() and bot_csv_dir.is_dir():
                    bot_csv_files = list(bot_csv_dir.glob("*.csv"))
                    if bot_csv_files:
                        job_service.add_job_event(db, job_id, "bot_activity_processing_started", f"Processing {len(bot_csv_files)} uploaded Binance bot CSV file(s)")
                        from worker.services.bot_parser_service import parse_bot_csv_to_dali_transactions
                        from tools.binanceBotActivity.binance_bot_activity.__main__ import main as run_bot_activity_cli
                        
                        bot_transactions = []
                        dfs = []
                        email_username = job.account_holder.split('@')[0].replace('.', '_')
                        import pandas as pd
                        
                        for csv_file in bot_csv_files:
                            try:
                                logger.info("Loading bot activity CSV: {}", csv_file.name)
                                dfs.append(pd.read_excel(csv_file) if csv_file.suffix == '.xlsx' else pd.read_csv(csv_file))
                            except Exception as be:
                                logger.error("Failed to load bot activity CSV {}: {}", csv_file.name, str(be))
                                job_service.add_job_event(db, job_id, "bot_activity_processing_failed", f"Failed to load bot CSV {csv_file.name}: {str(be)}")
                                
                        if dfs:
                            try:
                                # Concatenate and sort/deduplicate chronologically
                                logger.info("Consolidating {} bot CSV dataframes for continuous P&L matching...", len(dfs))
                                merged_df = pd.concat(dfs, ignore_index=True)
                                
                                # Remove duplicates across different file overlaps!
                                if "OrderNo" in merged_df.columns:
                                    merged_df = merged_df.drop_duplicates(subset=["OrderNo"], keep="first")
                                    
                                merged_df["parsed_time"] = pd.to_datetime(merged_df["Time"])
                                merged_df = merged_df.sort_values(by=["parsed_time", "OrderNo"], ascending=[True, True])
                                merged_df = merged_df.drop(columns=["parsed_time"])
                                
                                merged_csv_path = job_dir / "merged_bot_activity.csv"
                                merged_df.to_csv(merged_csv_path, index=False)
                                
                                # Parse transactions ONCE from the fully merged & deduplicated CSV!
                                logger.info("Generating unified DaLI transactions from consolidated bot CSV...")
                                bot_transactions = parse_bot_csv_to_dali_transactions(merged_csv_path, job.account_holder)
                                
                                # Run premium per-bot calculator on consolidated CSV
                                output_ods_name = f"{job.exchange}_{job.tax_year}_{email_username}_bot_report_out.ods"
                                output_ods_path = job_dir / output_ods_name
                                
                                logger.info("Running premium per-bot calculator on consolidated CSV: {}", output_ods_name)
                                run_bot_activity_cli([
                                    "--input", str(merged_csv_path),
                                    "--method", "FIFO",
                                    "--output", str(output_ods_path),
                                    "--local-currency", fiat,
                                    "--language", getattr(job, "lang", "EN"),
                                    "--country", getattr(job, "country", "ES")
                                ])
                                
                                # Register bot report in database
                                if output_ods_path.exists():
                                    doc_id = job_service.register_document(
                                        db=db,
                                        job_id=job_id,
                                        doc_type="binance_bot_report",
                                        storage_path=str(output_ods_path),
                                        filename=output_ods_name,
                                        mime_type="application/vnd.oasis.opendocument.spreadsheet",
                                        size=output_ods_path.stat().st_size
                                    )
                                    attachments.append(output_ods_path)
                                    logger.info("Bot ODS report registered: {}", output_ods_name)
                                    
                            except Exception as c_err:
                                logger.error("Failed to run consolidated bot activity P&L: {}", str(c_err))
                                job_service.add_job_event(db, job_id, "bot_activity_processing_failed", f"Failed to run consolidated bot P&L: {str(c_err)}")
                                
                        if bot_transactions:
                            transactions.extend(bot_transactions)
                            job_service.add_job_event(
                                db,
                                job_id,
                                "bot_activity_processing_completed",
                                f"Successfully merged {len(bot_transactions)} bot transactions into consolidated report"
                            )
            
            # Safeguard: Remove any duplicate transactions (by unique_id) before pricing and DaLI
            seen_ids = set()
            unique_transactions = []
            for tx in transactions:
                if tx.unique_id not in seen_ids:
                    seen_ids.add(tx.unique_id)
                    unique_transactions.append(tx)
                else:
                    logger.warning("Duplicate transaction unique_id detected and skipped: {}", tx.unique_id)
            transactions = unique_transactions
            
            # b. Enrich with prices via CCXT
            job_service.add_job_event(db, job_id, "price_enrichment", f"Enriching {len(transactions)} transactions with historical prices from {job.exchange}")
            dali_service.enrich_transactions_with_prices(transactions, fiat, job.exchange)
            
            # c. Resolve and Save (generates crypto_data.ini and crypto_data.ods)
            job_service.add_job_event(db, job_id, "dali_finalizing", "Resolving transactions and generating final output files")
            success = dali_service.resolve_and_save(job_dir, transactions, fiat, job.exchange, job.account_holder)
            
            # d. Check for warnings
            warnings_path = job_dir / "warnings.txt"
            if warnings_path.exists():
                with open(warnings_path, "r", encoding="utf-8") as f:
                    warn_count = len(f.readlines())
                job_service.add_job_event(db, job_id, "data_warnings", f"Generated {warn_count} data quality warnings. See warnings.txt for details.")
            
        else:
            # Standard workflow for other exchanges (though currently only binance is supported in API)
            config_path = dali_service.generate_config(
                job_dir=job_dir,
                account_holder=job.account_holder,
                exchange=job.exchange,
                api_key=api_key,
                api_secret=api_secret,
                native_fiat=fiat
            )
            success = dali_service.run_dali(job.country, config_path, job_dir, use_spot_lookup=True)

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

        # 6. Post-processing and Registration
        import pandas as pd
        import zipfile
        import shutil
        
        result_metadata = {"documents": []}
        
        # Calculate Prefix: [Exchange]_[tax_year]_[email_username]_
        email_username = job.account_holder.split('@')[0].replace('.', '_')
        prefix = f"{job.exchange}_{job.tax_year}_{email_username}_"
        
        # 1. Identify and Rename ODS files
        # The user specified these names
        ods_files_map = {
            "fifo_open_positions.ods": "ods_open_positions",
            "fifo_rp2_full_report.ods": "ods_rp2_full_report"
        }
        
        renamed_ods_paths = {} # original_name: new_path
        
        for old_name, doc_type in ods_files_map.items():
            old_path = job_dir / old_name
            if old_path.exists():
                new_name = f"{prefix}{old_name}"
                new_path = job_dir / new_name
                shutil.move(str(old_path), str(new_path))
                renamed_ods_paths[old_name] = new_path
                
                # Automatically enrich open positions report with year-end prices
                if old_name == "fifo_open_positions.ods":
                    try:
                        from worker.services.price_enricher import price_enricher
                        price_enricher.enrich_open_positions_report(
                            ods_path=new_path,
                            fiat=fiat,
                            tax_year=job.tax_year,
                            exchange_name=job.exchange
                        )
                    except Exception as pe_err:
                        logger.error("Failed to automatically enrich open positions: {}", pe_err)
                
                # Register renamed ODS
                size = new_path.stat().st_size
                doc_id = job_service.register_document(
                    db=db,
                    job_id=job_id,
                    doc_type=doc_type,
                    storage_path=str(new_path),
                    filename=new_name,
                    mime_type="application/vnd.oasis.opendocument.spreadsheet",
                    size=size
                )
                result_metadata["documents"].append({"id": doc_id, "type": doc_type, "filename": new_name})
            else:
                logger.warning("Expected report file not found: {}", old_path)

        # 2. Create ZIP: [Exchange]_[tax_year]_[email_username].zip
        zip_name = f"{job.exchange}_{job.tax_year}_{email_username}.zip"
        zip_path = job_dir / zip_name
        logger.info("Creating ZIP archive: {}", zip_name)
        with zipfile.ZipFile(str(zip_path), 'w') as zipf:
            # Add renamed ODS
            for p in renamed_ods_paths.values():
                zipf.write(str(p), p.name)
            # Add bot reports (if any, keeping standard attachments)
            for p in attachments:
                if p.exists() and p != zip_path and p.suffix == ".ods":
                    zipf.write(str(p), p.name)
                
        # Register ZIP
        if zip_path.exists():
            size = zip_path.stat().st_size
            doc_id = job_service.register_document(
                db=db,
                job_id=job_id,
                doc_type="zip_report",
                storage_path=str(zip_path),
                filename=zip_name,
                mime_type="application/zip",
                size=size
            )
            result_metadata["documents"].append({"id": doc_id, "type": "zip_report", "filename": zip_name})
            attachments.append(zip_path)
        
        # Also keep original inputs and warnings in DB for reference (optional but good)
        # Note: they are NOT added to attachments list
        for doc_type, filename, mime in [
            ("input_ods", "crypto_data.ods", "application/vnd.oasis.opendocument.spreadsheet"),
            ("warnings", "warnings.txt", "text/plain")
        ]:
            file_path = job_dir / filename
            if file_path.exists():
                job_service.register_document(
                    db=db,
                    job_id=job_id,
                    doc_type=doc_type,
                    storage_path=str(file_path),
                    filename=filename,
                    mime_type=mime,
                    size=file_path.stat().st_size
                )
            else:
                logger.debug("Optional file {} not found, skipping registration.", filename)

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
            attachments=attachments,
            lang=job.lang
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
