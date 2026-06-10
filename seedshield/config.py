"""
Configuration module for SeedShield application.

This module centralizes all configuration settings and constants used throughout
the application to improve maintainability and consistency.
"""

import os
import logging
import logging.handlers
import sys
from typing import Optional

# Application constants
APP_NAME = "SeedShield"
VERSION = "0.2.3"

# Security settings
REVEAL_TIMEOUT = 3  # Seconds before auto-hiding revealed words
MASK_CHARACTER = "*"
MASK_LENGTH = 5
LOG_MAX_SIZE = 1024 * 1024  # 1MB
LOG_BACKUP_COUNT = 3

# Default paths
DEFAULT_WORDLIST_PATH = "english.txt"
DEFAULT_WORDLIST_FULLPATH = os.path.join(os.path.dirname(__file__), "data", DEFAULT_WORDLIST_PATH)
DEFAULT_LOG_PATH = "seedshield.log"

# UI settings
SCROLL_INDICATOR_UP = "↑ More ↑"
SCROLL_INDICATOR_DOWN = "↓ More ↓"
MENU_TEXT = {
    "standard": "'n' - new input, 's' - show one by one, 'q' - quit, ↑↓ - scroll",
    "with_reset": "'n' - input, 's' - show one by one, 'r' - reset, 'q' - quit, ↑↓ - scroll",
    "mouse_help": "Mouse over to reveal word",
}


def setup_logging(
    log_level: int = logging.WARNING, log_file: Optional[str] = None
) -> logging.Logger:
    """
    Set up application logging with proper security measures.

    File logging is opt-in: no usage trail is written to disk unless a log
    file is explicitly requested (e.g. via the --verbose flag).

    Args:
        log_level: Desired logging level (default: WARNING)
        log_file: Optional path for file logging; None disables it

    Returns:
        logging.Logger: Configured logger instance
    """
    log = logging.getLogger(APP_NAME)
    log.setLevel(log_level)

    # Reconfiguring must not stack duplicate handlers
    for handler in log.handlers[:]:
        log.removeHandler(handler)
        handler.close()

    # Console handler for error messages only
    console_handler = logging.StreamHandler(sys.stderr)
    console_handler.setLevel(logging.ERROR)
    console_formatter = logging.Formatter("%(levelname)s: %(message)s")
    console_handler.setFormatter(console_formatter)

    # File handler with rotation, only when explicitly requested
    if log_file is not None:
        try:
            file_handler = logging.handlers.RotatingFileHandler(
                log_file, maxBytes=LOG_MAX_SIZE, backupCount=LOG_BACKUP_COUNT
            )
            file_handler.setLevel(log_level)
            file_formatter = logging.Formatter(
                "%(asctime)s - %(name)s - %(levelname)s - %(message)s", datefmt="%Y-%m-%d %H:%M:%S"
            )
            file_handler.setFormatter(file_formatter)

            log.addHandler(file_handler)
        except (PermissionError, IOError, OSError):
            # Fall back to console-only logging if file logging fails
            pass

    log.addHandler(console_handler)

    return log


# Create the application logger (console-only; file logging is opt-in)
logger = setup_logging()
