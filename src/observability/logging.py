"""Structured logging for GCP Cloud Logging compatibility."""

import logging
import sys
from typing import Any, Dict
from pythonjsonlogger import jsonlogger


class StructuredLogger:
    """Provides structured JSON logging for GCP compatibility."""

    def __init__(self, name: str = "quran-assistant", level: str = "INFO"):
        self.logger = logging.getLogger(name)
        self.logger.setLevel(getattr(logging, level.upper()))

        # Remove existing handlers
        self.logger.handlers.clear()

        # Create console handler with JSON formatter
        handler = logging.StreamHandler(sys.stdout)

        # Custom JSON formatter
        formatter = jsonlogger.JsonFormatter(
            fmt='%(asctime)s %(name)s %(levelname)s %(message)s',
            rename_fields={
                "asctime": "timestamp",
                "levelname": "severity",
                "name": "logger"
            }
        )

        handler.setFormatter(formatter)
        self.logger.addHandler(handler)

    def info(self, message: str, **kwargs: Any) -> None:
        """Log info message with additional fields."""
        self.logger.info(message, extra=kwargs)

    def error(self, message: str, **kwargs: Any) -> None:
        """Log error message with additional fields."""
        self.logger.error(message, extra=kwargs)

    def warning(self, message: str, **kwargs: Any) -> None:
        """Log warning message with additional fields."""
        self.logger.warning(message, extra=kwargs)

    def debug(self, message: str, **kwargs: Any) -> None:
        """Log debug message with additional fields."""
        self.logger.debug(message, extra=kwargs)


# Global logger instance
logger = StructuredLogger()
