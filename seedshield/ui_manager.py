"""
UI Manager module for SeedShield.

This module owns the curses terminal lifecycle: initialization, cleanup,
and running code within a properly managed UI context.
"""

import curses
import locale
import sys
from typing import Tuple, Callable, Any

from .config import logger


class UIManager:
    """
    Manages terminal UI operations with proper initialization and cleanup.

    This class abstracts the curses lifecycle to ensure the terminal is
    always restored, even in case of errors.
    """

    def __init__(self) -> None:
        """Initialize the UI manager."""
        # Typed as Any: tests inject MagicMock screens through initialize()
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
                self._set_input_timeout()
                self.update_dimensions()
                return

            # Required for ncurses to render multibyte UTF-8 (e.g. the
            # scroll indicators) correctly; must run before initscr()
            try:
                locale.setlocale(locale.LC_ALL, "")
            except locale.Error as locale_error:
                logger.debug("Locale setup failed: %s", str(locale_error))

            self.stdscr = curses.initscr()

            # Enable mouse events
            curses.mousemask(curses.ALL_MOUSE_EVENTS | curses.REPORT_MOUSE_POSITION)

            # Set up terminal settings
            curses.noecho()
            curses.cbreak()
            self.stdscr.keypad(True)

            self._set_input_timeout()
            self.update_dimensions()

        except Exception as e:
            self.cleanup()
            logger.error("Failed to initialize UI: %s", str(e))
            raise

    def _set_input_timeout(self) -> None:
        """Configure the non-blocking input timeout for the display loop."""
        if sys.stdin.isatty():
            # Set halfdelay mode for TTY with 0.1 second timeout (10 deciseconds)
            curses.halfdelay(1)
        else:
            # For non-TTY mode (like pipes/redirects), use regular timeou
            self.stdscr.timeout(100)

    def cleanup(self) -> None:
        """Properly clean up curses environment."""
        if self.stdscr is None:
            return

        try:
            # Wipe the screen first so revealed words cannot survive in
            # scrollback on terminals without alternate-screen support
            self.stdscr.erase()
            self.stdscr.refresh()
        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.debug("Screen wipe during cleanup failed: %s", str(e))

        try:
            # Reset terminal settings
            curses.nocbreak()
            self.stdscr.keypad(False)
            curses.echo()
            curses.endwin()
        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.error("Error during UI cleanup: %s", str(e))
        finally:
            self.stdscr = None

    def update_dimensions(self) -> Tuple[int, int]:
        """
        Update stored dimensions of the terminal.

        Returns:
            Tuple[int, int]: Height and width of the terminal
        """
        self.height, self.width = self.stdscr.getmaxyx()
        return self.height, self.width

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
