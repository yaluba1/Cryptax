"""
Configuration management for the CrypTax worker service.
Uses pydantic-settings to load configuration from environment variables,
.env files, and Docker secrets.
"""

from pathlib import Path
from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict

# Docker secrets directory
SECRETS_DIR = "/run/secrets"
if not Path(SECRETS_DIR).exists():
    SECRETS_DIR = None

class Settings(BaseSettings):
    # Database Configuration
    db_host: str = "localhost"
    db_port: int = 3306
    db_name: str = "cryptax"
    db_user: str = "cryptax_user"
    db_password: str = "cryptax_password"

    # Redis / RQ Configuration
    redis_host: str = "localhost"
    redis_port: int = 6379
    redis_db: int = 0
    rq_queue_name: str = "tax_jobs"

    # Worker Configuration
    country: str = "ES" # Default country for DaLI/RP2 (e.g., ES, US, GENERIC)

    # Logging Configuration
    log_level: str = "INFO"
    log_dir: Path = Path("./logs")
    log_rotation: str = "00:00"
    log_retention: str = "31 days"
    log_compression: str = "zip"

    # Email / SMTP Configuration
    email_smtp_svr: str = "localhost"
    email_smtp_port: int = 587
    email_smtp_cypher: str = "STARTTLS"
    email_acc_name: str = "info@cryptax.com"
    email_acc_pws: str = "password"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        secrets_dir=SECRETS_DIR,
        extra="ignore",
    )

settings = Settings()
