"""
SeedShield: Secure BIP39 word viewer with masking and reveal functionality.

This module provides a secure interface for viewing BIP39 seed words with
built-in security features like masking, timed reveals, and secure memory handling.

Security features:
- All words are masked by default
- Auto-hide after 3 seconds
- No persistent storage of sensitive data
- Secure memory handling
- Input validation and sanitization
- Clipboard clearing after use
"""

import curses
import sys
import argparse
from .secure_word_interface import SecureWordInterface


def main() -> None:
    """Main entry point with argument parsing."""
    parser = argparse.ArgumentParser(
        description='Secure BIP39 word viewer with masking and reveal functionality'
    )
    parser.add_argument(
        '-w', '--wordlist',
        default='english.txt',
        help='Path to wordlist file (default: english.txt)'
    )
    parser.add_argument(
        '-i', '--input',
        help='Input file with positions'
    )

    args = parser.parse_args()

    try:
        interface = SecureWordInterface(args.wordlist)
        interface.run(args.input)
    except KeyboardInterrupt:
        curses.endwin()
        sys.exit(0)
    except Exception as e:
        curses.endwin()
        print(f"Error: {str(e)}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()