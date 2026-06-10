"""
Tests for the configuration module, focused on secure logging behavior.

File logging must be strictly opt-in: a security tool for seed phrases
must not write a usage trail to disk unless explicitly requested.
"""

import logging
import logging.handlers

from seedshield.config import setup_logging


def _handler_types(log):
    return [type(h) for h in log.handlers]


def test_setup_logging_default_has_no_file_handler():
    """By default no log file is created and level is WARNING."""
    log = setup_logging()

    assert logging.handlers.RotatingFileHandler not in _handler_types(log)
    assert log.level == logging.WARNING


def test_setup_logging_with_file_adds_file_handler(tmp_path):
    """File logging is enabled only when a log file is explicitly given."""
    log_file = tmp_path / "test.log"
    log = setup_logging(logging.DEBUG, log_file=str(log_file))

    assert logging.handlers.RotatingFileHandler in _handler_types(log)
    assert log.level == logging.DEBUG

    # Restore default console-only configuration for other tests
    setup_logging()


def test_setup_logging_is_idempotent():
    """Reconfiguring must not stack duplicate handlers."""
    setup_logging()
    log = setup_logging()

    assert len(log.handlers) == 1


def test_setup_logging_file_failure_falls_back_to_console(tmp_path):
    """An unwritable log file must not break logging setup."""
    log = setup_logging(logging.DEBUG, log_file=str(tmp_path))  # a directory: open fails

    assert logging.handlers.RotatingFileHandler not in _handler_types(log)
    assert logging.StreamHandler in _handler_types(log)

    # Restore default console-only configuration for other tests
    setup_logging()
