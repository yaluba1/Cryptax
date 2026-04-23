from pydantic_settings import BaseSettings, SettingsConfigDict
from pathlib import Path

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

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        secrets_dir="/run/secrets",
        extra="ignore",
    )

settings = Settings()
