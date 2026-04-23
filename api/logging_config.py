import sys
from loguru import logger
from api.config import settings

def setup_logging():
    """Configure Loguru for the API."""
    
    # Ensure log directory exists
    settings.log_dir.mkdir(parents=True, exist_ok=True)
    
    # Remove default handler
    logger.remove()
    
    # Add stdout handler with colors
    logger.add(
        sys.stdout,
        colorize=True,
        format="<green>{time:YYYY-MM-DD at HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
        level=settings.log_level,
    )
    
    # Add file handler with rotation, retention, and compression
    log_file = settings.log_dir / "cryptax_api.log"
    logger.add(
        str(log_file),
        rotation=settings.log_rotation,
        retention=settings.log_retention,
        compression=settings.log_compression,
        format="{time:YYYY-MM-DD at HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
        level=settings.log_level,
        enqueue=True,  # Thread-safe
    )
    
    logger.info("Logging initialized.")

setup_logging()
