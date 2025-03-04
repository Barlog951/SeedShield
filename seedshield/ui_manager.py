"""
UI Manager module for SeedShield.

This module provides an abstraction layer for terminal UI operations,
making the application more maintainable and easier to test.
"""

import curses
import sys
from typing import Tuple, Callable, Any

from .config import logger


class UIManager:
    """
    Manages terminal UI operations with proper initialization and cleanup.

    This class abstracts the curses library to provide a cleaner interface
    and ensure proper cleanup even in case of errors.
    """

    def __init__(self) -> None:
        """Initialize the UI manager."""
        # Initialize as Any to handle mypy validation
        # The actual value will be set in initialize()
        self.stdscr: Any = None
        self.height = 0
        self.width = 0

    def initialize(self, mock_stdscr: Any = None) -> None:
        """
        Initialize curses environment with proper settings.

        Args:
            mock_stdscr: Optional mock stdscr for testing
        """
        try:
            # If we're given a mock screen (for testing), use i
            if mock_stdscr is not None:
                self.stdscr = mock_stdscr

                # Still set up basic terminal settings for mock screen
                self.stdscr.keypad(True)

                # Set timeout based on terminal type
                if sys.stdin.isatty():
                    # Set halfdelay mode for TTY with 0.1 second timeout (10 deciseconds)
                    # This is equivalent to 100ms but uses curses' halfdelay mode
                    curses.halfdelay(1)
                else:
                    # For non-TTY mode (like pipes/redirects), use regular timeou
                    self.stdscr.timeout(100)

                # Initialize size variables
                self.update_dimensions()
                return

            self.stdscr = curses.initscr()

            # Set up colors if supported
            try:
                curses.start_color()
                # Make sure color pairs are available before initializing them
                if hasattr(curses, 'COLORS') and hasattr(curses, 'COLOR_PAIRS'):
                    if curses.COLORS > 0 and curses.COLOR_PAIRS > 0:
                        curses.init_pair(1, curses.COLOR_WHITE, curses.COLOR_BLACK)
                        curses.init_pair(2, curses.COLOR_BLACK, curses.COLOR_WHITE)
            except Exception as color_error:
                # If colors not supported, continue without them
                logger.debug("Color initialization failed: %s", str(color_error))

            # Enable mouse events
            curses.mousemask(curses.ALL_MOUSE_EVENTS | curses.REPORT_MOUSE_POSITION)

            # Set up terminal settings
            curses.noecho()
            curses.cbreak()
            self.stdscr.keypad(True)

            # Set timeout based on terminal type
            if sys.stdin.isatty():
                # Set halfdelay mode for TTY with 0.1 second timeout (10 deciseconds)
                # This is equivalent to 100ms but uses curses' halfdelay mode
                curses.halfdelay(1)
            else:
                # For non-TTY mode (like pipes/redirects), use regular timeou
                self.stdscr.timeout(100)

            # Initialize size variables
            self.update_dimensions()

        except Exception as e:
            self.cleanup()
            logger.error("Failed to initialize UI: %s", str(e))
            raise

    def cleanup(self) -> None:
        """Properly clean up curses environment."""
        if self.stdscr is not None:
            try:
                # Reset terminal settings
                curses.nocbreak()
                self.stdscr.keypad(False)
                curses.echo()
                curses.endwin()
            except Exception as e:
                logger.error("Error during UI cleanup: %s", str(e))

    def get_input(self, echo: bool = False) -> int:
        """
        Get a character of input from the user.

        Args:
            echo: Whether to echo the input to the screen

        Returns:
            int: Character code of inpu
        """
        if echo:
            curses.echo()

        try:
            c = self.stdscr.getch()
            # Explicitly convert any return value to in
            return int(c) if c is not None else -1
        except curses.error:
            return -1
        finally:
            if echo:
                curses.noecho()

    def get_string(self, y: int, x: int, prompt: str = "") -> str:
        """
        Get a string of input from the user.

        Args:
            y: Y coordinate to display promp
            x: X coordinate to display promp
            prompt: Prompt tex

        Returns:
            str: User input string
        """
        self.stdscr.addstr(y, x, prompt)
        curses.echo()

        try:
            raw_input = self.stdscr.getstr()
            if raw_input is not None:
                input_str: str = raw_input.decode('utf-8').strip()
                return input_str
            return ""
        except Exception:
            return ""
        finally:
            curses.noecho()

    def update_dimensions(self) -> Tuple[int, int]:
        """
        Update stored dimensions of the terminal.

        Returns:
            Tuple[int, int]: Height and width of the terminal
        """
        self.height, self.width = self.stdscr.getmaxyx()
        return self.height, self.width

    def clear(self) -> None:
        """Clear the screen."""
        self.stdscr.clear()

    def refresh(self) -> None:
        """Refresh the screen."""
        self.stdscr.refresh()

    def add_text(self, y: int, x: int, text: str, highlight: bool = False) -> None:
        """
        Add text to the screen at the specified position.

        Args:
            y: Y coordinate
            x: X coordinate
            text: Text to display
            highlight: Whether to highlight the tex
        """
        try:
            if highlight:
                self.stdscr.addstr(y, x, text, curses.A_REVERSE)
            else:
                self.stdscr.addstr(y, x, text)
        except curses.error:
            # This can happen when writing to the bottom-right corner
            pass

    def get_mouse_event(self) -> Tuple[int, int, int, int, int]:
        """
        Get a mouse event.

        Returns:
            Tuple[int, int, int, int, int]: ID, x, y, z, bstate
        """
        return curses.getmouse()

    def with_ui_context(self, callback: Callable[[], Any]) -> Any:
        """
        Run a function with properly initialized and cleaned up UI context.

        Args:
            callback: Function to run within UI contex

        Returns:
            Any: Return value of the callback function
        """
        try:
            self.initialize()
            return callback()
        except Exception as e:
            logger.error("Error in UI context: %s", str(e))
            raise
        finally:
            self.cleanup()
