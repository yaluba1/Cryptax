"""
Service for sending email notifications to users.
Uses smtplib and email.mime for HTML emails with attachments.
"""

import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication
from pathlib import Path
from worker.config import settings
from worker.logging_config import logger

class EmailService:
    @staticmethod
    def send_job_completed_email(
        recipient_email: str,
        job_id: str,
        country: str,
        exchange: str,
        year: int,
        attachments: list[Path]
    ) -> bool:
        """
        Sends an email to the user indicating that the tax job is completed.
        Includes generated reports as attachments.
        """
        logger.info("Sending job completion email to {}", recipient_email)
        
        try:
            # Create message container
            msg = MIMEMultipart()
            msg['From'] = settings.email_acc_name
            msg['To'] = recipient_email
            msg['Subject'] = f"CrypTax: Your Tax Report for {year} is Ready! (Job: {job_id[:8]})"
            
            # HTML Body with "Premium" aesthetics (clean, modern, with some colors)
            html_body = f"""
            <html>
                <body style="font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; line-height: 1.6; color: #333; max-width: 600px; margin: auto; padding: 20px; border: 1px solid #eee; border-radius: 10px;">
                    <div style="text-align: center; padding-bottom: 20px;">
                        <h1 style="color: #2c3e50;">CrypTax</h1>
                        <p style="color: #7f8c8d; font-size: 1.1em;">Your crypto tax reporting partner</p>
                    </div>
                    <hr style="border: 0; border-top: 1px solid #eee;">
                    <div style="padding: 20px 0;">
                        <h2 style="color: #27ae60;">Tax Report Completed</h2>
                        <p>Hello,</p>
                        <p>We are pleased to inform you that your tax report for the year <b>{year}</b> has been generated successfully.</p>
                        
                        <div style="background-color: #f9f9f9; padding: 15px; border-radius: 5px; margin: 20px 0;">
                            <p style="margin: 5px 0;"><b>Job ID:</b> {job_id}</p>
                            <p style="margin: 5px 0;"><b>Country:</b> {country}</p>
                            <p style="margin: 5px 0;"><b>Exchange:</b> {exchange.capitalize()}</p>
                            <p style="margin: 5px 0;"><b>Tax Year:</b> {year}</p>
                        </div>
                        
                        <p>The generated reports are attached to this email:</p>
                        <ul style="color: #34495e;">
                            <li><b>Tax Report (ODS):</b> The final tax calculation report.</li>
                            <li><b>Input Data (ODS):</b> Normalized transaction data used for the report.</li>
                            <li><b>Data Warnings (TXT):</b> Details on any data quality adjustments made for RP2 compatibility.</li>
                        </ul>
                    </div>
                    <div style="text-align: center; padding: 20px; font-size: 0.9em; color: #95a5a6;">
                        <p>&copy; 2026 CrypTax Service. All rights reserved.</p>
                    </div>
                </body>
            </html>
            """
            
            msg.attach(MIMEText(html_body, 'html'))
            
            # Attach files
            for file_path in attachments:
                if not file_path.exists():
                    logger.warning("Attachment file not found: {}", file_path)
                    continue
                    
                with open(file_path, "rb") as f:
                    part = MIMEApplication(f.read(), Name=file_path.name)
                    
                # Add header for attachment
                part['Content-Disposition'] = f'attachment; filename="{file_path.name}"'
                msg.attach(part)
                logger.debug("Attached file: {}", file_path.name)
                
            # Send the email
            logger.debug("Connecting to SMTP server {}:{}", settings.email_smtp_svr, settings.email_smtp_port)
            
            with smtplib.SMTP(settings.email_smtp_svr, settings.email_smtp_port) as server:
                if settings.email_smtp_cypher == "STARTTLS":
                    server.starttls()
                
                server.login(settings.email_acc_name, settings.email_acc_pws)
                server.send_message(msg)
                
            logger.info("Email sent successfully to {}", recipient_email)
            return True
            
        except Exception as e:
            logger.error("Failed to send email to {}: {}", recipient_email, str(e))
            logger.exception(e)
            return False

email_service = EmailService()
