"""
Test secure memory handling utilities.

Strings under test are built at runtime (never literals): the compiler
interns identifier-like literals, and overwriting an interned string's
buffer would corrupt that constant for the whole process.
"""

import ctypes
import platform
import subprocess
import sys
from unittest.mock import patch

import pytest

from seedshield.secure_memory import (
    _ascii_buffer_offset,
    secure_clear_string,
    secure_clear_list,
    secure_clipboard_clear,
)


def _fresh_string(seed: str) -> str:
    """Build a non-interned string at runtime."""
    return "".join(list(seed))


def test_secure_clear_string_empty():
    """Test secure_clear_string with empty string."""
    secure_clear_string("")
    # No assertion needed, just verifying it doesn't crash


def test_secure_clear_string_non_string():
    """Test secure_clear_string with non-string input."""
    secure_clear_string(123)
    # No assertion needed, just verifying it doesn't crash


@patch("ctypes.memmove")
def test_secure_clear_string(mock_memmove):
    """Test secure_clear_string with valid string."""
    secure_clear_string(_fresh_string("sensitive data"))
    mock_memmove.assert_called_once()


@patch("ctypes.memmove")
def test_secure_clear_string_skips_cached_singletons(mock_memmove):
    """Single-char strings are interpreter-cached and must never be touched."""
    secure_clear_string("a")
    mock_memmove.assert_not_called()


@patch("ctypes.memmove")
def test_secure_clear_string_skips_non_ascii(mock_memmove):
    """Non-ASCII strings use a different layout and must be skipped."""
    secure_clear_string(_fresh_string("héslo-čžý"))
    mock_memmove.assert_not_called()


@patch("ctypes.memmove")
def test_secure_clear_string_attribute_error(mock_memmove):
    """Test handling of AttributeError in secure_clear_string."""
    mock_memmove.side_effect = AttributeError("Test error")

    # Should not raise exception
    secure_clear_string(_fresh_string("sensitive data"))


@patch("ctypes.memmove")
def test_secure_clear_string_general_exception(mock_memmove):
    """Test handling of general exceptions in secure_clear_string."""
    mock_memmove.side_effect = Exception("Unexpected test error")

    # Should not raise exception
    secure_clear_string(_fresh_string("sensitive data"))


@pytest.mark.skipif(platform.python_implementation() != "CPython", reason="CPython layout")
def test_secure_clear_string_overwrites_buffer_not_header():
    """The character buffer must change while the object header stays intact."""
    secret = _fresh_string("correct horse battery staple")
    offset = _ascii_buffer_offset(secret)
    assert offset is not None and offset > 0

    secure_clear_string(secret)

    buffer = ctypes.string_at(id(secret) + offset, len(secret))
    assert buffer != b"correct horse battery staple"
    # Header intact: the object is still a usable str of the same length
    assert isinstance(secret, str) and len(secret) == 28


def test_secure_clear_survives_garbage_collection():
    """
    Regression test: overwriting the object header (instead of the buffer)
    crashed the interpreter with SIGBUS in gc_collect on Python 3.14.
    """
    code = (
        "import gc\n"
        "from seedshield.secure_memory import secure_clear_string, secure_clear_list\n"
        "words = ['' .join(chr(97 + (i + j) % 26) for j in range(10)) for i in range(200)]\n"
        "secure_clear_list(words)\n"
        "secure_clear_string(''.join(chr(98 + i % 24) for i in range(50)))\n"
        "gc.collect()\n"
    )
    result = subprocess.run(
        [sys.executable, "-c", code], capture_output=True, text=True, check=False
    )
    assert result.returncode == 0, f"interpreter crashed: {result.stderr}"


def test_secure_clear_list_non_list():
    """Test secure_clear_list with non-list input."""
    secure_clear_list("not a list")
    # No assertion needed, just verifying it doesn't crash


def test_secure_clear_list_empty():
    """Test secure_clear_list with empty list."""
    test_list = []
    secure_clear_list(test_list)
    assert test_list == []


def test_secure_clear_list_strings():
    """Test secure_clear_list with a list of strings."""
    test_list = [_fresh_string("secret1"), _fresh_string("secret2")]
    secure_clear_list(test_list)
    assert test_list == []


def test_secure_clear_list_nested():
    """Test secure_clear_list with nested lists."""
    test_list = [_fresh_string("secret1"), [_fresh_string("nested_secret")], _fresh_string("s2")]
    secure_clear_list(test_list)
    assert test_list == []


@patch("pyperclip.copy")
def test_secure_clipboard_clear_success(mock_copy):
    """Test successful clipboard clearing."""
    mock_copy.return_value = None

    result = secure_clipboard_clear()
    assert result is True
    mock_copy.assert_called_once_with("")


@patch("builtins.__import__")
def test_secure_clipboard_clear_import_error(mock_import):
    """Test ImportError handling in secure_clipboard_clear."""

    def mock_import_function(name, *args, **kwargs):
        if name == "pyperclip":
            raise ImportError("Mock import error")
        return __import__(name, *args, **kwargs)

    mock_import.side_effect = mock_import_function

    result = secure_clipboard_clear()
    assert result is False


@patch("pyperclip.copy")
def test_secure_clipboard_clear_general_exception(mock_copy):
    """Test general exception handling in secure_clipboard_clear."""
    mock_copy.side_effect = Exception("Test exception")

    result = secure_clipboard_clear()
    assert result is False
