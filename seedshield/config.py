"""
Configuration module for SeedShield application.

This module centralizes all configuration settings and constants used throughout
the application to improve maintainability and consistency.
"""

import os
import logging
import logging.handlers
import sys
from contextlib import contextmanager
from collections.abc import Iterator

# Application constants
APP_NAME = "SeedShield"
VERSION = "0.5.0"

# Security settings
REVEAL_TIMEOUT = 3  # Seconds before auto-hiding revealed words
MASK_CHARACTER = "*"
MASK_LENGTH = 5
LOG_MAX_SIZE = 1024 * 1024  # 1MB
LOG_BACKUP_COUNT = 3
MAX_POSITIONS_FILE_SIZE = 64 * 1024  # characters; a seed needs at most 24 positions

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
    "mouse_help": "Mouse: hover or click a word to reveal",
}

# Terminal layout (rows)
ROW_SPACING = 2  # each word occupies this many rows
RESERVED_BOTTOM_ROWS = 7  # rows kept free for the menu and scroll indicators
MENU_OFFSET = 5  # menu starts this many rows above the bottom
INPUT_PROMPT_ROW = 5  # row of the "> " prompt on the input screen
INPUT_MESSAGE_ROW = 6  # row used for input-screen feedback messages

# xterm private mode 1003 ("any event" tracking): ncurses only enables click
# reporting, so hover (motion) events must be requested explicitly
MOUSE_MOTION_ON = "\033[?1003h"
MOUSE_MOTION_OFF = "\033[?1003l"


CONSOLE_HANDLER_NAME = "console"


class PrivateRotatingFileHandler(logging.handlers.RotatingFileHandler):
    """Rotating log handler whose files are readable by the owner only (0600)."""

    def _open(self):  # type: ignore[no-untyped-def]
        fd = os.open(self.baseFilename, os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o600)
        if hasattr(os, "fchmod"):
            # Tighten files that already existed with looser permissions
            os.fchmod(fd, 0o600)
        return open(fd, "a", encoding=self.encoding, errors=self.errors)


@contextmanager
def console_logging_suppressed() -> Iterator[None]:
    """
    Silence stderr logging while curses owns the terminal.

    Anything written to stderr during the TUI would be drawn over the
    interface; errors are reported by main() after the terminal is restored.
    """
    handlers = [
        handler
        for handler in logging.getLogger(APP_NAME).handlers
        if handler.get_name() == CONSOLE_HANDLER_NAME
    ]
    levels = [handler.level for handler in handlers]
    for handler in handlers:
        handler.setLevel(logging.CRITICAL + 1)
    try:
        yield
    finally:
        for handler, level in zip(handlers, levels):
            handler.setLevel(level)


def setup_logging(
    log_level: int = logging.WARNING, log_file: str | None = None
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
    console_handler.set_name(CONSOLE_HANDLER_NAME)
    console_handler.setLevel(logging.ERROR)
    console_formatter = logging.Formatter("%(levelname)s: %(message)s")
    console_handler.setFormatter(console_formatter)

    # File handler with rotation, only when explicitly requested
    if log_file is not None:
        try:
            file_handler = PrivateRotatingFileHandler(
                log_file, maxBytes=LOG_MAX_SIZE, backupCount=LOG_BACKUP_COUNT
            )
            file_handler.setLevel(log_level)
            file_formatter = logging.Formatter(
                "%(asctime)s - %(name)s - %(levelname)s - %(message)s", datefmt="%Y-%m-%d %H:%M:%S"
            )
            file_handler.setFormatter(file_formatter)

            log.addHandler(file_handler)
        except (PermissionError, OSError):
            # Fall back to console-only logging if file logging fails
            pass

    log.addHandler(console_handler)

    return log


# Create the application logger (console-only; file logging is opt-in)
logger = setup_logging()
