"""
Logging configuration for the CrypTax worker service using loguru.
Configures file and console logging with rotation, retention, and compression.
"""

import sys
from pathlib import Path
from loguru import logger
from worker.config import settings

def setup_logging():
    """
    Initialize loguru with the settings from config.
    Creates the log directory if it doesn't exist.
    """
    # 1. Create log directory if it doesn't exist
    settings.log_dir.mkdir(parents=True, exist_ok=True)

    # 2. Remove default handlers
    logger.remove()

    # 3. Add Console logging (Colorized and Prettified)
    logger.add(
        sys.stderr,
        format="<green>{time:YYYY-MM-DD at HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
        level=settings.log_level,
        colorize=True,
        backtrace=True,
        diagnose=True
    )

    # 4. Add File logging
    log_file = settings.log_dir / "worker.log"
    logger.add(
        str(log_file),
        format="{time:YYYY-MM-DD at HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
        level=settings.log_level,
        rotation=settings.log_rotation,
        retention=settings.log_retention,
        compression=settings.log_compression,
        encoding="utf-8"
    )

    logger.info("Logging initialized. Level: {}, Directory: {}", settings.log_level, settings.log_dir)

# Initialize logging when the module is imported
setup_logging()
