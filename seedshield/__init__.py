"""
SeedShield: Secure BIP39 seed phrase viewer with enterprise-grade security features.

Provides a secure interface for viewing seed phrases with no persistence,
secure memory handling, and automatic masking.
"""

from .secure_word_interface import SecureWordInterface
from .input_handler import InputHandler
from .display_handler import DisplayHandler
from .state_handler import StateHandler
from .ui_manager import UIManager
from .secure_memory import secure_clear_string, secure_clear_list, secure_clipboard_clear
from .config import VERSION, setup_logging, logger

__version__ = VERSION
__all__ = [
    'SecureWordInterface',
    'InputHandler',
    'DisplayHandler',
    'StateHandler',
    'UIManager',
    'secure_clear_string',
    'secure_clear_list',
    'secure_clipboard_clear',
    'setup_logging',
    'logger'
]
