"""
Logging configuration module for the LLM-driven analysis application.

This module provides a centralized logging configuration that can be used
across all components of the application.
"""

import logging
import logging.handlers
import sys
from pathlib import Path
from typing import Optional
from datetime import datetime


class ColoredFormatter(logging.Formatter):
    """Custom formatter that adds colors to log levels for terminal output."""

    # ANSI escape codes for colors
    COLORS = {
        'DEBUG': '\033[36m',    # Cyan
        'INFO': '\033[32m',     # Green
        'WARNING': '\033[33m',  # Yellow
        'ERROR': '\033[31m',    # Red
        'CRITICAL': '\033[35m', # Magenta
    }
    RESET = '\033[0m'

    def format(self, record):
        # Add color to the level name
        levelname = record.levelname
        if levelname in self.COLORS:
            record.levelname = f"{self.COLORS[levelname]}{levelname}{self.RESET}"

        # Format the message
        formatted = super().format(record)

        # Reset the levelname for other handlers
        record.levelname = levelname

        return formatted


def setup_logger(
    name: str,
    level: str = "INFO",
    log_dir: Optional[str] = None,
    console_output: bool = True,
    file_output: bool = True,
    max_bytes: int = 10485760,  # 10MB
    backup_count: int = 5,
    format_string: Optional[str] = None
) -> logging.Logger:
    """
    Set up a logger with both console and file handlers.

    Args:
        name: Name of the logger (typically __name__ from the calling module)
        level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_dir: Directory for log files. If None, uses 'logs' in current directory
        console_output: Whether to output logs to console
        file_output: Whether to output logs to file
        max_bytes: Maximum size of log file before rotation (default 10MB)
        backup_count: Number of backup files to keep
        format_string: Custom format string for log messages

    Returns:
        Configured logger instance
    """

    # Create logger
    logger = logging.getLogger(name)

    # Avoid adding handlers multiple times
    if logger.handlers:
        return logger

    logger.setLevel(getattr(logging, level.upper()))

    # Default format string
    if format_string is None:
        format_string = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'

    # Console handler with colored output
    if console_output:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(getattr(logging, level.upper()))

        # Use colored formatter for console
        console_formatter = ColoredFormatter(
            fmt='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        console_handler.setFormatter(console_formatter)
        logger.addHandler(console_handler)

    # File handler with rotation
    if file_output:
        # Create log directory if it doesn't exist
        if log_dir is None:
            log_dir = "logs"
        log_path = Path(log_dir)
        log_path.mkdir(exist_ok=True)

        # Create log file name with timestamp
        log_file = log_path / f"{name.replace('.', '_')}_{datetime.now().strftime('%Y%m%d')}.log"

        # Rotating file handler
        file_handler = logging.handlers.RotatingFileHandler(
            log_file,
            maxBytes=max_bytes,
            backupCount=backup_count
        )
        file_handler.setLevel(getattr(logging, level.upper()))

        # Regular formatter for file (no colors)
        file_formatter = logging.Formatter(
            fmt=format_string,
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        file_handler.setFormatter(file_formatter)
        logger.addHandler(file_handler)

    return logger


def get_logger(name: str) -> logging.Logger:
    """
    Get or create a logger with the default configuration.

    This is a convenience function that returns a logger with sensible defaults.

    Args:
        name: Name of the logger (typically __name__ from the calling module)

    Returns:
        Configured logger instance
    """
    return setup_logger(
        name=name,
        level="INFO",
        console_output=True,
        file_output=True
    )


# Create a root logger for the application
app_logger = setup_logger(
    name="llm_driven_analysis",
    level="INFO",
    console_output=True,
    file_output=True
)


# Utility function to log exceptions
def log_exception(logger: logging.Logger, exc: Exception, message: str = "Exception occurred"):
    """
    Log an exception with full traceback.

    Args:
        logger: Logger instance to use
        exc: Exception instance
        message: Additional context message
    """
    logger.error(f"{message}: {str(exc)}", exc_info=True)


# Configure logging for third-party libraries
def configure_third_party_loggers(level: str = "WARNING"):
    """
    Configure logging levels for third-party libraries to reduce noise.

    Args:
        level: Logging level for third-party libraries
    """
    # Reduce noise from common libraries
    logging.getLogger("urllib3").setLevel(level)
    logging.getLogger("asyncio").setLevel(level)
    logging.getLogger("httpx").setLevel(level)
    logging.getLogger("httpcore").setLevel(level)
    logging.getLogger("openai").setLevel(level)
    logging.getLogger("uvicorn.access").setLevel(level)

    # FastAPI/Starlette
    logging.getLogger("fastapi").setLevel(level)
    logging.getLogger("starlette").setLevel(level)


# Initialize third-party logger configuration on module import
configure_third_party_loggers()
