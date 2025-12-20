"""
Logging configuration module.

This module provides structured logging configuration with support for:
- Console logging (development)
- File logging with rotation (production)
- JSON logging (production, for log aggregation)
- Multiple log levels and formatters
- Separate error log file
"""

import logging
import logging.config
import sys
from pathlib import Path
from typing import Any

from core.config import settings


def setup_logging() -> None:
    """
    Configure application logging based on environment settings.

    Configures:
    - Log level from settings
    - Console output with colored formatting (development)
    - Rotating file handlers (if enabled)
    - JSON formatting (production)
    - Separate error log file

    Call this function at application startup, before any logging occurs.
    """
    # Create logs directory if it doesn't exist
    if settings.log_file_enabled:
        log_dir = Path(settings.log_file_path).parent
        log_dir.mkdir(parents=True, exist_ok=True)

    # Build logging configuration dictionary
    logging_config = get_logging_config()

    # Apply logging configuration
    logging.config.dictConfig(logging_config)

    # Log initialization message
    logger = logging.getLogger(__name__)
    logger.info(
        f"Logging configured: level={settings.log_level}, "
        f"format={settings.log_format}, "
        f"file_enabled={settings.log_file_enabled}"
    )


def get_logging_config() -> dict[str, Any]:
    """
    Get logging configuration dictionary.

    Returns:
        Dictionary compatible with logging.config.dictConfig()
    """
    # Determine formatters based on environment
    if settings.log_format == "json":
        console_formatter = "json"
        file_formatter = "json"
    else:
        console_formatter = "detailed"
        file_formatter = "detailed"

    # Base configuration
    config: dict[str, Any] = {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "default": {
                "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
                "datefmt": "%Y-%m-%d %H:%M:%S",
            },
            "detailed": {
                "format": (
                    "%(asctime)s - %(name)s - %(levelname)s - "
                    "[%(filename)s:%(lineno)d] - %(funcName)s() - %(message)s"
                ),
                "datefmt": "%Y-%m-%d %H:%M:%S",
            },
            "json": {
                "()": "pythonjsonlogger.jsonlogger.JsonFormatter",
                "format": (
                    "%(asctime)s %(name)s %(levelname)s %(filename)s "
                    "%(lineno)d %(funcName)s %(message)s"
                ),
            },
        },
        "filters": {
            "correlation_id": {
                "()": CorrelationIdFilter,
            },
        },
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "level": settings.log_level,
                "formatter": console_formatter,
                "stream": sys.stdout,
                "filters": ["correlation_id"],
            },
        },
        "root": {
            "level": settings.log_level,
            "handlers": ["console"],
        },
        "loggers": {
            # Configure specific loggers
            "uvicorn": {
                "level": "INFO",
                "handlers": ["console"],
                "propagate": False,
            },
            "uvicorn.access": {
                "level": "INFO",
                "handlers": ["console"],
                "propagate": False,
            },
            "sqlalchemy": {
                "level": "WARNING",  # Set to INFO to see SQL queries
                "handlers": ["console"],
                "propagate": False,
            },
            "sqlalchemy.engine": {
                "level": "WARNING",  # Set to INFO to see SQL queries
                "handlers": ["console"],
                "propagate": False,
            },
            "src": {
                "level": settings.log_level,
                "handlers": ["console"],
                "propagate": False,
            },
        },
    }

    # Add file handlers if enabled
    if settings.log_file_enabled:
        config["handlers"]["file"] = {
            "class": "logging.handlers.RotatingFileHandler",
            "level": settings.log_level,
            "formatter": file_formatter,
            "filename": settings.log_file_path,
            "maxBytes": settings.log_file_max_bytes,
            "backupCount": settings.log_file_backup_count,
            "encoding": "utf-8",
            "filters": ["correlation_id"],
        }

        config["handlers"]["error_file"] = {
            "class": "logging.handlers.RotatingFileHandler",
            "level": "ERROR",
            "formatter": file_formatter,
            "filename": str(Path(settings.log_file_path).parent / "error.log"),
            "maxBytes": settings.log_file_max_bytes,
            "backupCount": settings.log_file_backup_count,
            "encoding": "utf-8",
            "filters": ["correlation_id"],
        }

        # Add file handlers to root and application loggers
        config["root"]["handlers"].extend(["file", "error_file"])
        config["loggers"]["src"]["handlers"].extend(["file", "error_file"])

    return config


class CorrelationIdFilter(logging.Filter):
    """
    Logging filter to add correlation_id to log records.

    The correlation_id (request_id) is used to trace requests across
    the application and external services. It's set in middleware and
    should be included in all logs for a request.
    """

    def filter(self, record: logging.LogRecord) -> bool:
        """
        Add correlation_id to log record.

        The correlation_id is stored in contextvars by middleware.
        If not present, uses 'no-request-id'.

        Args:
            record: Log record to filter

        Returns:
            True (always allow the log record)
        """
        # Try to get correlation_id from context
        # This will be set by middleware in actual requests
        if not hasattr(record, "correlation_id"):
            record.correlation_id = "no-request-id"

        return True


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger instance for a module.

    This is a convenience function that wraps logging.getLogger()
    and ensures consistent logger naming across the application.

    Args:
        name: Logger name, typically __name__ of the module

    Returns:
        Logger instance

    Example:
        >>> logger = get_logger(__name__)
        >>> logger.info("Application started")
    """
    return logging.getLogger(name)
