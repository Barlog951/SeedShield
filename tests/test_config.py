"""
Tests for the configuration module, focused on secure logging behavior.

File logging must be strictly opt-in: a security tool for seed phrases
must not write a usage trail to disk unless explicitly requested.
"""

import logging
import logging.handlers

import os
import stat
import sys

import pytest

from seedshield.config import (
    APP_NAME,
    CONSOLE_HANDLER_NAME,
    console_logging_suppressed,
    setup_logging,
)


def _has_file_handler(log):
    return any(isinstance(h, logging.handlers.RotatingFileHandler) for h in log.handlers)


def test_setup_logging_default_has_no_file_handler():
    """By default no log file is created and level is WARNING."""
    log = setup_logging()

    assert not _has_file_handler(log)
    assert log.level == logging.WARNING


def test_setup_logging_with_file_adds_file_handler(tmp_path):
    """File logging is enabled only when a log file is explicitly given."""
    log_file = tmp_path / "test.log"
    log = setup_logging(logging.DEBUG, log_file=str(log_file))

    assert _has_file_handler(log)
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

    assert not _has_file_handler(log)
    assert any(h.get_name() == CONSOLE_HANDLER_NAME for h in log.handlers)

    # Restore default console-only configuration for other tests
    setup_logging()


@pytest.mark.skipif(sys.platform == "win32", reason="POSIX permissions")
def test_log_file_is_private(tmp_path):
    """The verbose log must be readable by the owner only, even if it pre-existed."""
    log_file = tmp_path / "test.log"
    log_file.write_text("")
    os.chmod(log_file, 0o644)
    log = setup_logging(logging.DEBUG, log_file=str(log_file))
    log.debug("entry")

    assert stat.S_IMODE(os.stat(log_file).st_mode) == 0o600
    setup_logging()


def test_console_logging_suppressed_restores_level():
    """stderr logging is silenced inside the TUI and restored afterwards."""
    setup_logging()
    console = next(
        h for h in logging.getLogger(APP_NAME).handlers if h.get_name() == CONSOLE_HANDLER_NAME
    )

    with console_logging_suppressed():
        assert console.level > logging.CRITICAL
    assert console.level == logging.ERROR


def test_console_logging_suppressed_restores_on_error():
    """The console level is restored even if the TUI raises."""
    setup_logging()
    console = next(
        h for h in logging.getLogger(APP_NAME).handlers if h.get_name() == CONSOLE_HANDLER_NAME
    )

    with pytest.raises(RuntimeError):
        with console_logging_suppressed():
            raise RuntimeError("boom")
    assert console.level == logging.ERROR
