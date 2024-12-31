"""
SeedShield: Secure BIP39 seed phrase viewer with enterprise-grade security features.
"""

from .secure_word_interface import SecureWordInterface
from .input_handler import InputHandler
from .display_handler import DisplayHandler
from .state_handler import StateHandler

__version__ = "0.1.6"
__all__ = ['SecureWordInterface', 'InputHandler', 'DisplayHandler', 'StateHandler']