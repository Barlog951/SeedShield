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
- Proper exception handling with cleanup
- Terminal resize handling
"""

import sys
import argparse
import os
import logging
from typing import Optional

from .secure_word_interface import SecureWordInterface
from .config import logger, setup_logging, DEFAULT_WORDLIST_PATH, APP_NAME, VERSION


def parse_arguments() -> argparse.Namespace:
    """
    Parse command line arguments.

    Returns:
        argparse.Namespace: Parsed arguments
    """
    parser = argparse.ArgumentParser(
        description=f'{APP_NAME} v{VERSION}: Secure BIP39 word viewer with masking and reveal'
    )
    parser.add_argument(
        '-w', '--wordlist',
        default=DEFAULT_WORDLIST_PATH,
        help=f'Path to wordlist file (default: {DEFAULT_WORDLIST_PATH})'
    )
    parser.add_argument(
        '-i', '--input',
        help='Input file with positions'
    )
    parser.add_argument(
        '-v', '--verbose',
        action='store_true',
        help='Enable verbose logging'
    )
    parser.add_argument(
        '--version',
        action='version',
        version=f'{APP_NAME} v{VERSION}'
    )

    return parser.parse_args()


def validate_wordlist_path(wordlist_path: str) -> Optional[str]:
    """
    Validate wordlist path and return the full path if valid.

    Args:
        wordlist_path: Path to wordlist file

    Returns:
        Optional[str]: Valid full path or None if invalid
    """
    # If default path, use the one bundled with the package
    if wordlist_path == DEFAULT_WORDLIST_PATH:
        return os.path.join(os.path.dirname(__file__), "data", DEFAULT_WORDLIST_PATH)

    # Otherwise validate the provided path
    if not os.path.exists(wordlist_path):
        logger.error("Wordlist file not found: %s", wordlist_path)
        return None

    if not os.path.isfile(wordlist_path):
        logger.error("Wordlist path is not a file: %s", wordlist_path)
        return None

    if not os.access(wordlist_path, os.R_OK):
        logger.error("No read permission for wordlist file: %s", wordlist_path)
        return None

    return wordlist_path


def main() -> None:
    """
    Main entry point with argument parsing and security setup.

    Handles command-line arguments, initializes logging, validates inputs,
    and runs the secure word interface with proper exception handling.
    """
    # Parse command line arguments
    args = parse_arguments()

    # Configure logging level based on verbose flag
    log_level = logging.DEBUG if args.verbose else logging.INFO
    setup_logging(log_level)

    logger.info("Starting %s v%s", APP_NAME, VERSION)

    # Validate wordlist path
    valid_wordlist_path = validate_wordlist_path(args.wordlist)
    if not valid_wordlist_path:
        print(f"Error: Invalid wordlist file: {args.wordlist}", file=sys.stderr)
        sys.exit(1)

    # Validate input file if provided
    if args.input and not os.path.exists(args.input):
        print(f"Error: Input file not found: {args.input}", file=sys.stderr)
        sys.exit(1)

    try:
        # Create the interface
        interface = SecureWordInterface(valid_wordlist_path)

        # Run the interface
        interface.run(args.input)

    except KeyboardInterrupt:
        logger.info("Received keyboard interrupt, exiting cleanly")
        sys.exit(0)
    except (ValueError, IOError, OSError) as e:
        logger.error("Error running secure word interface: %s", str(e))
        print(f"Error: {str(e)}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        logger.error("Unexpected error: %s", str(e))
        print(f"Error: {str(e)}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
