from pydantic_settings import BaseSettings, SettingsConfigDict
from pathlib import Path

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

    # Logging Configuration
    log_level: str = "INFO"
    log_dir: Path = Path("./logs")
    log_rotation: str = "00:00"
    log_retention: str = "31 days"
    log_compression: str = "zip"

    # Hanko Authentication
    hanko_api_url: str = "https://7608898b-488d-4cec-b8df-acd233a92873.hanko.io"
    jwks_url: str = "https://7608898b-488d-4cec-b8df-acd233a92873.hanko.io/.well-known/jwks.json"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        secrets_dir=SECRETS_DIR,
        extra="ignore",
    )

settings = Settings()
