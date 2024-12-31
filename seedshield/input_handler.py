import curses
import time
import pyperclip
from typing import List, Optional


class InputHandler:
    """
    Handles user input processing and validation for the secure word interface.
    """

    def __init__(self, word_count: int):
        """
        Initialize the input handler.

        Args:
            word_count: Total number of available words
        """
        self.word_count = word_count

    def _clear_clipboard(self) -> None:
        """
        Safely clear clipboard contents.

        Attempts to clear the clipboard by setting it to an empty string.
        Fails silently if clipboard access is not available.
        """
        try:
            pyperclip.copy('')
        except Exception:
            pass

    def display_input_prompt(self, stdscr) -> None:
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

    def process_clipboard_input(self, stdscr) -> Optional[List[int]]:
        """
        Process and validate input from the clipboard.

        Args:
            stdscr: Curses window object for terminal display

        Returns:
            Optional[List[int]]: List of valid position numbers, or None if no valid numbers found
        """
        content = pyperclip.paste()
        numbers = []
        for line in content.splitlines():
            try:
                num = int(line.strip())
                if 1 <= num <= self.word_count:
                    numbers.append(num)
            except ValueError:
                continue

        self._clear_clipboard()

        if numbers:
            stdscr.addstr(6, 0, f"Found {len(numbers)} valid numbers")
            stdscr.refresh()
            time.sleep(1)
            return numbers
        else:
            stdscr.addstr(6, 0, "No valid numbers found in clipboard")
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
        except ValueError:
            return None

    def get_input(self, stdscr) -> Optional[List[int]]:
        """
        Get user input, validating it and handling different input types.

        Args:
            stdscr: Curses window object for terminal display

        Returns:
            Optional[List[int]]: List of valid position numbers or None for quit command
        """
        while True:
            self.display_input_prompt(stdscr)
            curses.echo()

            try:
                input_str = stdscr.getstr().decode('utf-8').strip().lower()

                # Handle quitting
                if input_str == 'q':
                    return None

                # Handle clipboard input
                elif input_str == 'v':
                    clipboard_numbers = self.process_clipboard_input(stdscr)
                    if clipboard_numbers:
                        return clipboard_numbers

                # Handle individual number
                else:
                    validated_input = self.validate_number_input(input_str)
                    if validated_input:
                        return validated_input

            finally:
                curses.noecho()