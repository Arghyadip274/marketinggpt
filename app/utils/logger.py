"""Centralized logging configuration for MarketingGPT."""

import logging
import os
from logging.handlers import RotatingFileHandler
from pathlib import Path

from app.config.settings import settings


def configure_logging() -> None:
    """Setup application-wide logging configuration."""
    log_level_name = settings.log_level.upper()
    log_level = getattr(logging, log_level_name, logging.INFO)

    # Define standard format
    log_format = "%(asctime)s - %(levelname)s - [%(name)s] - %(message)s"
    formatter = logging.Formatter(log_format)

    # 1. Console Handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    console_handler.setLevel(log_level)

    # 2. File Handler (Rotating)
    logs_dir = Path("logs")
    logs_dir.mkdir(parents=True, exist_ok=True)
    log_file_path = logs_dir / "marketing_gpt.log"
    
    file_handler = RotatingFileHandler(
        log_file_path, 
        maxBytes=5 * 1024 * 1024,  # 5 MB
        backupCount=3,
        encoding="utf-8"
    )
    file_handler.setFormatter(formatter)
    file_handler.setLevel(log_level)

    # 3. Configure root logger
    root_logger = logging.getLogger()
    
    # Remove existing handlers to prevent duplicates during testing or reloads
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
        
    root_logger.setLevel(log_level)
    root_logger.addHandler(console_handler)
    root_logger.addHandler(file_handler)

    # Set library loggers to WARNING to avoid noise
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("requests").setLevel(logging.WARNING)
    
    # Let our app logger be set
    app_logger = logging.getLogger("app")
    app_logger.setLevel(log_level)

    app_logger.info("Centralized logging configured successfully (Level: %s)", log_level_name)
