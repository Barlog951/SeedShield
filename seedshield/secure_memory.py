"""
Secure memory handling utilities for SeedShield.

This module provides functions for secure memory handling to prevent sensitive
data like seed phrases from persisting in memory longer than necessary.
"""

import ctypes
import sys
from typing import Any, List, Optional
import secrets

from .config import logger


def _ascii_buffer_offset(string_var: str) -> Optional[int]:
    """
    Locate the inline character buffer of a CPython compact ASCII string.

    Compact ASCII strings store their bytes inline at the end of the object,
    followed by a NUL terminator, so the buffer starts at
    sizeof(object) - len - 1. Writing anywhere before that offset would
    corrupt the object header (refcount/type) and crash the interpreter.

    Args:
        string_var: String to inspect

    Returns:
        Optional[int]: Buffer offset from the object address, or None if the
            string does not use the compact ASCII layout
    """
    if not string_var.isascii():
        return None

    offset = sys.getsizeof(string_var) - len(string_var) - 1
    return offset if offset > 0 else None


def secure_clear_string(string_var: str) -> None:
    """
    Attempt to securely clear a string from memory.

    This function tries to overwrite the character buffer of a string
    with random data before releasing the reference. Note that Python's
    garbage collection means this isn't guaranteed to fully remove the
    data from memory immediately.

    Args:
        string_var: String to be securely cleared
    """
    # Strings shorter than 2 chars may be interpreter-cached singletons
    # shared across the whole process; never overwrite those
    if not isinstance(string_var, str) or len(string_var) < 2:
        return

    try:
        # Generate random data to overwrite with
        random_data = "".join(chr(secrets.randbelow(128)) for _ in range(len(string_var)))

        # Try to directly modify the string's internal buffer
        # This is implementation-dependent and may not work in all Python versions
        if hasattr(string_var, "_wa_"):  # For PyPy
            string_var._wa_[:] = random_data  # pylint: disable=protected-access
        else:
            # For CPython, overwrite only the inline character buffer;
            # touching the object header crashes the GC (verified on 3.14)
            offset = _ascii_buffer_offset(string_var)
            if offset is None:
                logger.debug("Secure string clearing skipped: unsupported string layout")
                return

            ctypes.memmove(id(string_var) + offset, random_data.encode("ascii"), len(string_var))
    except (AttributeError, TypeError, ValueError) as e:
        # Log error but don't raise - best effort only
        logger.debug("Secure string clearing failed: %s", str(e))
    except Exception as e:  # pylint: disable=broad-exception-caught
        # Log unexpected errors
        logger.debug("Unexpected error in secure string clearing: %s", str(e))

    # Can't actually set the parameter to None as it would only affect the local reference


def secure_clear_list(list_var: List[Any]) -> None:
    """
    Securely clear a list containing sensitive data.

    Args:
        list_var: List to be securely cleared
    """
    if not isinstance(list_var, list):
        return

    # First clear all items
    for i, item in enumerate(list_var):
        if isinstance(item, str):
            secure_clear_string(item)
        elif isinstance(item, list):
            secure_clear_list(item)

        # Set each element to None
        list_var[i] = None

    # Clear the list itself
    list_var.clear()


def secure_clipboard_clear() -> bool:
    """
    Securely clear the system clipboard.

    Returns:
        bool: True if successful, False otherwise
    """
    try:
        import pyperclip  # type: ignore  # pylint: disable=import-outside-toplevel

        pyperclip.copy("")
        return True
    except ImportError as e:
        logger.error("Failed to import pyperclip: %s", str(e))
        return False
    except Exception as e:  # pylint: disable=broad-exception-caught
        logger.error("Failed to clear clipboard: %s", str(e))
        return False
