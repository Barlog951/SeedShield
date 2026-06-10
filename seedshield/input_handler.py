"""
Input handling for the SeedShield application.

This module processes and validates user input from various sources,
including keyboard, clipboard, and files.
"""

import curses
import os
import re
from typing import List, Optional, Tuple

import pyperclip  # type: ignore

from .config import logger, INPUT_PROMPT_ROW, INPUT_MESSAGE_ROW
from .secure_memory import secure_clipboard_clear


class InputHandler:
    """
    Handles user input processing and validation for the secure word interface.
    """

    def __init__(self, word_count: int) -> None:
        """
        Initialize the input handler.

        Args:
            word_count: Total number of available words
        """
        self.word_count = word_count

    def display_input_prompt(self, stdscr: "curses.window", message: Optional[str] = None) -> None:
        """
        Display input instructions and an optional feedback message.

        Args:
            stdscr: Curses window object for terminal display
            message: Optional feedback from the previous input attempt
        """
        stdscr.clear()
        stdscr.addstr(0, 0, f"Enter position(s) (1-{self.word_count}), e.g. 5 12 19, or:")
        stdscr.addstr(1, 0, "- Type 'v' to paste numbers from clipboard")
        stdscr.addstr(2, 0, "- Type 'q' to quit")
        stdscr.addstr(3, 0, "Press Enter after your input")
        if message:
            stdscr.addstr(INPUT_MESSAGE_ROW, 0, message)
        # Drawn last so the cursor lands right after the prompt
        stdscr.addstr(INPUT_PROMPT_ROW, 0, "> ")
        stdscr.refresh()

    def process_clipboard_input(self) -> Optional[List[int]]:
        """
        Process and validate input from the clipboard.

        The clipboard is securely cleared immediately after reading.

        Returns:
            Optional[List[int]]: List of valid position numbers, or None if
                no valid numbers were found
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

            return numbers or None

        except (pyperclip.PyperclipException, ValueError) as e:
            logger.error("Error processing clipboard: %s", str(e))
            return None
        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.error("Unexpected clipboard error: %s", str(e))
            return None

    def validate_number_input(self, input_str: str) -> Optional[List[int]]:
        """
        Validate number input from the user.

        Accepts one or more positions separated by spaces and/or commas
        (e.g. "5", "5 12 19", "5,12,19"). All values must be valid for
        the input to be accepted.

        Args:
            input_str: String containing the user's input

        Returns:
            Optional[List[int]]: List of valid position numbers,
                               or None if any value is invalid
        """
        tokens = [token for token in re.split(r"[,\s]+", input_str.strip()) if token]
        if not tokens:
            return None

        positions = []
        for token in tokens:
            # Never log the entered values: positions encode the seed
            try:
                num = int(token)
            except ValueError:
                logger.debug("Invalid non-integer input")
                return None

            if not 1 <= num <= self.word_count:
                logger.debug("Input number out of valid range (1-%s)", self.word_count)
                return None

            positions.append(num)

        return positions

    @staticmethod
    def _validate_readable_file(file_path: str) -> bool:
        """
        Check that the path exists, is a regular file, and is readable.

        Args:
            file_path: Path to validate

        Returns:
            bool: True if the file can be read
        """
        if not os.path.exists(file_path):
            logger.error("File not found: %s", file_path)
            return False

        if not os.path.isfile(file_path):
            logger.error("Not a file: %s", file_path)
            return False

        if not os.access(file_path, os.R_OK):
            logger.error("No read permission for file: %s", file_path)
            return False

        return True

    def load_positions_from_file(self, file_path: str) -> Optional[List[int]]:
        """
        Load position numbers from a file with security validation.

        Args:
            file_path: Path to the file containing position numbers

        Returns:
            Optional[List[int]]: List of valid position numbers or None if error
        """
        if not self._validate_readable_file(file_path):
            return None

        try:
            positions = []
            with open(file_path, "r", encoding="utf-8") as f:
                for line_num, line in enumerate(f, 1):
                    line = line.strip()
                    # Never log line contents or values: positions encode the seed
                    if not line or not line.isdigit():
                        logger.warning("Skipping invalid content at line %s", line_num)
                        continue

                    num = int(line)
                    if 1 <= num <= self.word_count:
                        positions.append(num)
                    else:
                        logger.warning(
                            "Skipping out-of-range number at line %s (valid range: 1-%s)",
                            line_num,
                            self.word_count,
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
        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.error("Unexpected error reading positions file: %s", str(e))
            return None

    def _process_input_command(self, input_str: str) -> Tuple[Optional[List[int]], Optional[str]]:
        """
        Process a single input command.

        Args:
            input_str: User input string

        Returns:
            Tuple[Optional[List[int]], Optional[str]]: Positions (None means
                quit, an empty list means retry) and an optional feedback
                message for the next prompt
        """
        # Handle quitting
        if input_str == "q":
            return None, None

        # Handle clipboard input
        if input_str == "v":
            numbers = self.process_clipboard_input()
            if numbers:
                return numbers, None
            return [], "No valid numbers found in clipboard"

        # Handle one or more numbers
        validated_input = self.validate_number_input(input_str)
        if validated_input:
            return validated_input, None

        return [], f"Invalid input. Enter numbers between 1-{self.word_count}"

    def get_input(self, stdscr: "curses.window") -> Optional[List[int]]:
        """
        Get user input, validating it and handling different input types.

        Feedback messages stay visible on the redrawn prompt instead of
        blocking the UI; input is fully blocking while the user types.

        Args:
            stdscr: Curses window object for terminal display

        Returns:
            Optional[List[int]]: List of valid position numbers or None for quit command
        """
        # Block while the user types; the display loop restores its own timeout
        stdscr.timeout(-1)
        message: Optional[str] = None

        while True:
            try:
                self.display_input_prompt(stdscr, message)
                message = None
                curses.echo()
                try:
                    input_str = stdscr.getstr().decode("utf-8").strip().lower()
                finally:
                    curses.noecho()

                # Skip empty input
                if not input_str:
                    continue

                result, message = self._process_input_command(input_str)
                # None means quit, empty list means retry with feedback shown
                if result is None:
                    return None
                if result:
                    return result

            except UnicodeDecodeError as e:
                logger.error("Invalid character input: %s", str(e))
                message = "Invalid character input"
            except ValueError as e:
                logger.error("Invalid input format: %s", str(e))
                message = "Invalid input format"
            except Exception as e:  # pylint: disable=broad-exception-caught
                logger.error("Error processing input: %s", str(e))
                message = "Error processing input"
