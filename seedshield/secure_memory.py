"""
Secure memory handling utilities for SeedShield.

This module provides functions for secure memory handling to prevent sensitive
data like seed phrases from persisting in memory longer than necessary.
"""

import ctypes
from typing import Any, List
import secrets

from .config import logger


def secure_clear_string(string_var: str) -> None:
    """
    Attempt to securely clear a string from memory.

    This function tries to overwrite the memory location of a string
    with random data before releasing the reference. Note that Python's
    garbage collection means this isn't guaranteed to fully remove the
    data from memory immediately.

    Args:
        string_var: String to be securely cleared
    """
    if not isinstance(string_var, str) or not string_var:
        return

    # Get the memory address of the string
    try:
        # Generate random data to overwrite with
        random_data = ''.join(chr(secrets.randbelow(128)) for _ in range(len(string_var)))

        # Try to directly modify the string's internal buffer
        # This is implementation-dependent and may not work in all Python versions
        if hasattr(string_var, '_wa_'):  # For PyPy
            string_var._wa_[:] = random_data
        else:
            # For CPython, try to access the internal buffer
            # This is a best-effort approach
            addr = id(string_var)

            # Overwrite with random data
            # This relies on implementation details and is not guaranteed to work
            ctypes.memmove(addr, random_data.encode('utf-8'), len(string_var))
    except (AttributeError, TypeError, ValueError) as e:
        # Log error but don't raise - best effort only
        logger.debug("Secure string clearing failed: %s", str(e))
    except Exception as e:
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
        import pyperclip  # type: ignore
        pyperclip.copy('')
        return True
    except ImportError as e:
        logger.error("Failed to import pyperclip: %s", str(e))
        return False
    except Exception as e:
        logger.error("Failed to clear clipboard: %s", str(e))
        return False
