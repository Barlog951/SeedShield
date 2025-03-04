"""
Input handling for the SeedShield application.

This module processes and validates user input from various sources,
including keyboard, clipboard, and files.
"""

import curses
import time
import os
from typing import List, Optional, Any

import pyperclip  # type: ignore

from .config import logger
from .secure_memory import secure_clipboard_clear


class InputHandler:
    """
    Handles user input processing and validation for the secure word interface.
    """

    def __init__(self, word_count: int, ui_manager: Any = None) -> None:
        """
        Initialize the input handler.

        Args:
            word_count: Total number of available words
            ui_manager: UI manager instance for rendering
        """
        self.word_count = word_count
        self.ui_manager = ui_manager

    def display_input_prompt(self, stdscr: Any) -> None:
        """
        Display input instructions to the user.

        Args:
            stdscr: Curses window object for terminal display
        """
        stdscr.clear()
        stdscr.addstr(0, 0, f"Enter position (1-{self.word_count}) or:")
        stdscr.addstr(1, 0, "- Type 'v' to paste numbers from clipboard")
        stdscr.addstr(2, 0, "- Type 'q' to quit")
        stdscr.addstr(3, 0, "Press Enter after your input")
        stdscr.addstr(5, 0, "> ")
        stdscr.refresh()

    # For backward compatibility with tests
    def _clear_clipboard(self) -> None:
        """
        Safely clear clipboard contents.

        Attempts to clear the clipboard by setting it to an empty string.
        Fails silently if clipboard access is not available.
        """
        secure_clipboard_clear()

    def process_clipboard_input(self, stdscr: Any) -> Optional[List[int]]:
        """
        Process and validate input from the clipboard.

        Args:
            stdscr: Curses window object for terminal display

        Returns:
            Optional[List[int]]: List of valid position numbers, or None if no valid numbers found
        """
        try:
            content = pyperclip.paste()
            numbers = []

            # Process each line in the clipboard content
            for line in content.splitlines():
                try:
                    num = int(line.strip())
                    if 1 <= num <= self.word_count:
                        numbers.append(num)
                except ValueError:
                    continue

            # Securely clear the clipboard
            if not secure_clipboard_clear():
                logger.warning("Failed to securely clear clipboard")

            # Provide feedback based on processing results
            if numbers:
                stdscr.addstr(6, 0, f"Found {len(numbers)} valid numbers")
                stdscr.refresh()
                time.sleep(1)
                return numbers

            stdscr.addstr(6, 0, "No valid numbers found in clipboard")
            stdscr.refresh()
            time.sleep(1)
            return None

        except (pyperclip.PyperclipException, ValueError) as e:
            logger.error("Error processing clipboard: %s", str(e))
            stdscr.addstr(6, 0, "Error processing clipboard data")
            stdscr.refresh()
            time.sleep(1)
            return None
        except Exception as e:
            logger.error("Unexpected clipboard error: %s", str(e))
            stdscr.addstr(6, 0, "Unexpected error with clipboard")
            stdscr.refresh()
            time.sleep(1)
            return None

    def validate_number_input(self, input_str: str) -> Optional[List[int]]:
        """
        Validate single number input from the user.

        Args:
            input_str: String containing the user's input

        Returns:
            Optional[List[int]]: Single-element list with valid position number,
                               or None if input is invalid
        """
        try:
            num = int(input_str)
            if 1 <= num <= self.word_count:
                return [num]

            logger.debug("Input number %s out of valid range (1-%s)", num, self.word_count)
        except ValueError:
            logger.debug("Invalid non-integer input: %s", input_str)
        return None

    def load_positions_from_file(self, file_path: str) -> Optional[List[int]]:
        """
        Load position numbers from a file with security validation.

        Args:
            file_path: Path to the file containing position numbers

        Returns:
            Optional[List[int]]: List of valid position numbers or None if error
        """
        # Security check: validate file path
        if not os.path.exists(file_path):
            logger.error("File not found: %s", file_path)
            return None

        if not os.path.isfile(file_path):
            logger.error("Not a file: %s", file_path)
            return None

        try:
            # Check read permissions
            if not os.access(file_path, os.R_OK):
                logger.error("No read permission for file: %s", file_path)
                return None

            positions = []
            with open(file_path, 'r', encoding='utf-8') as f:
                for line_num, line in enumerate(f, 1):
                    line = line.strip()
                    if not line or not line.isdigit():
                        logger.warning("Skipping invalid content at line %s: '%s'", line_num, line)
                        continue

                    num = int(line)
                    if 1 <= num <= self.word_count:
                        positions.append(num)
                    else:
                        logger.warning(
                            "Skipping out-of-range number at line %s: %s "
                            "(valid range: 1-%s)", line_num, num, self.word_count
                        )

            if not positions:
                logger.warning("No valid position numbers found in file: %s", file_path)

            return positions

        except IOError as e:
            logger.error("I/O error reading positions file: %s", str(e))
            return None
        except ValueError as e:
            logger.error("Value error in positions file: %s", str(e))
            return None
        except Exception as e:
            logger.error("Unexpected error reading positions file: %s", str(e))
            return None

    def _display_error(self, stdscr: Any, message: str, error: Optional[Exception] = None) -> None:
        """
        Display an error message on the screen.

        Args:
            stdscr: Curses window object
            message: Error message to display
            error: Optional exception to log
        """
        if error:
            logger.error("%s: %s", message, str(error))
        stdscr.addstr(6, 0, message)
        stdscr.refresh()
        time.sleep(1)

    def _process_input_command(self, stdscr: Any, input_str: str) -> Optional[List[int]]:
        """
        Process a specific input command.

        Args:
            stdscr: Curses window object
            input_str: User input string

        Returns:
            Optional[List[int]]: Processed positions or None
        """
        # Handle quitting
        if input_str == 'q':
            return None

        # Handle clipboard input
        if input_str == 'v':
            return self.process_clipboard_input(stdscr)

        # Handle individual number
        validated_input = self.validate_number_input(input_str)
        if validated_input:
            return validated_input

        # Invalid input
        err_msg = f"Invalid input. Please enter a number between 1-{self.word_count}"
        self._display_error(stdscr, err_msg)
        return []  # Empty list indicates continuing input loop

    def get_input(self, stdscr: Any) -> Optional[List[int]]:
        """
        Get user input, validating it and handling different input types.

        Args:
            stdscr: Curses window object for terminal display

        Returns:
            Optional[List[int]]: List of valid position numbers or None for quit command
        """
        while True:
            # Clear any previous error messages
            stdscr.move(6, 0)
            stdscr.clrtoeol()
            self.display_input_prompt(stdscr)
            curses.echo()

            try:
                input_str = stdscr.getstr().decode('utf-8').strip().lower()
                # Skip empty input
                if not input_str:
                    continue

                result = self._process_input_command(stdscr, input_str)
                # None means quit, empty list means continue, otherwise return the result
                if result is None:
                    return None
                if result:  # Non-empty list
                    return result

            except UnicodeDecodeError as e:
                self._display_error(stdscr, "Invalid character input", e)
            except ValueError as e:
                self._display_error(stdscr, "Invalid input format", e)
            except Exception as e:
                self._display_error(stdscr, "Error processing input", e)
            finally:
                curses.noecho()
