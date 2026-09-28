"""
UI Manager module for SeedShield.

This module owns the curses terminal lifecycle: initialization, cleanup,
and running code within a properly managed UI context.
"""

import curses
import locale
import sys
from typing import Any
from collections.abc import Callable

from .config import logger, console_logging_suppressed, MOUSE_MOTION_ON, MOUSE_MOTION_OFF


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
        self._motion_tracking = False

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

            self._enable_mouse()

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

    def _enable_mouse(self) -> None:
        """Enable click and hover reporting; the mouse is optional, so failures are ignored."""
        try:
            # Deliver presses immediately instead of waiting to detect clicks
            curses.mouseinterval(0)
        except curses.error as e:
            logger.debug("Mouse interval setup failed: %s", str(e))
        self.set_mouse_enabled(True)

    def set_mouse_enabled(self, enabled: bool) -> None:
        """
        Turn mouse reporting on or off.

        Mouse reporting must be off on the text-input screen: getstr() beeps
        on every mouse event, and hover tracking would send dozens per second.

        Args:
            enabled: True to report clicks and hover, False to stop all reports
        """
        if not enabled and self._motion_tracking:
            self._write_terminal(MOUSE_MOTION_OFF)
            self._motion_tracking = False

        try:
            availmask, _ = curses.mousemask(
                curses.ALL_MOUSE_EVENTS | curses.REPORT_MOUSE_POSITION if enabled else 0
            )
        except (curses.error, TypeError, ValueError) as e:
            logger.debug("Mouse setup failed: %s", str(e))
            return

        if enabled and availmask and not self._motion_tracking:
            self._motion_tracking = self._write_terminal(MOUSE_MOTION_ON)

    @staticmethod
    def _write_terminal(sequence: str) -> bool:
        """
        Write a raw control sequence to the terminal.

        Args:
            sequence: Escape sequence to emit

        Returns:
            bool: True if the sequence was written
        """
        try:
            sys.stdout.write(sequence)
            sys.stdout.flush()
            return True
        except (OSError, ValueError) as e:
            logger.debug("Terminal write failed: %s", str(e))
            return False

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

        if self._motion_tracking:
            # Never leave the terminal emitting motion reports after exit
            self._write_terminal(MOUSE_MOTION_OFF)
            self._motion_tracking = False

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

    def update_dimensions(self) -> tuple[int, int]:
        """
        Update stored dimensions of the terminal.

        Returns:
            tuple[int, int]: Height and width of the terminal
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
        with console_logging_suppressed():
            try:
                self.initialize()
                return callback()
            except Exception as e:
                logger.error("Error in UI context: %s", str(e))
                raise
            finally:
                self.cleanup()
