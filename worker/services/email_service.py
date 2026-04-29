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
        attachments: list[Path],
        lang: str = "en"
    ) -> bool:
        """
        Sends an email to the user indicating that the tax job is completed.
        Includes generated reports as attachments.
        """
        from worker.services.localization_service import localization_service
        
        logger.info("Sending job completion email to {} (lang: {})", recipient_email, lang)
        
        strings = localization_service.get_email_strings(lang)
        
        try:
            # Create message container
            msg = MIMEMultipart()
            msg['From'] = settings.email_acc_name
            msg['To'] = recipient_email
            
            # Localized Subject
            subject_tmpl = strings.get("subject", "CrypTax: Your Tax Report for {year} in {exchange} is Ready")
            msg['Subject'] = subject_tmpl.format(year=year, exchange=exchange.capitalize())
            
            # Localized HTML Body
            html_body = f"""
            <html>
                <body style="font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; line-height: 1.6; color: #333; max-width: 600px; margin: auto; padding: 20px; border: 1px solid #eee; border-radius: 10px;">
                    <div style="text-align: center; padding-bottom: 20px;">
                        <h1 style="color: #2c3e50;">CrypTax</h1>
                    </div>
                    <hr style="border: 0; border-top: 1px solid #eee;">
                    <div style="padding: 20px 0;">
                        <h2 style="color: #27ae60;">{strings.get('body_title')}</h2>
                        <p>{strings.get('greeting')}</p>
                        <p>{strings.get('intro').format(year=year)}</p>
                        
                        <div style="background-color: #f9f9f9; padding: 15px; border-radius: 5px; margin: 20px 0;">
                            <p style="margin: 5px 0;"><b>{strings.get('label_job_id')}:</b> {job_id}</p>
                            <p style="margin: 5px 0;"><b>{strings.get('label_country')}:</b> {country}</p>
                            <p style="margin: 5px 0;"><b>{strings.get('label_exchange')}:</b> {exchange.capitalize()}</p>
                            <p style="margin: 5px 0;"><b>{strings.get('label_tax_year')}:</b> {year}</p>
                        </div>
                        
                        <p>{strings.get('attachment_info')}</p>
                    </div>
                    <div style="text-align: center; padding: 20px; font-size: 0.9em; color: #95a5a6;">
                        <p>{strings.get('footer')}</p>
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
