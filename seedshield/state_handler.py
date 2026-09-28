"""
State management for the SeedShield application.

This module handles application state, user interaction, and navigation.
"""

import curses

from .config import logger, REVEAL_TIMEOUT


class StateHandler:
    """
    Manages state and command handling for the secure word interface.

    This class handles:
    - Tracking word reveal state (which word is shown, when it was revealed)
    - Processing user commands and navigation
    - Managing sequential reveal mode
    - Implementing auto-hide timeout functionality
    """

    def __init__(self) -> None:
        """Initialize the state handler with default state."""
        # Currently shown word index (if any)
        self.cursor_pos: int | None = None

        # When was the current word revealed (for auto-hide)
        self.reveal_time: float | None = None

        # For sequential reveal mode
        self.current_index = 0
        self.reached_last = False

        # Optionally track terminal resize events
        self.last_known_dimensions: tuple[int, int] | None = None

    def reset_positions(self) -> None:
        """Reset all state to default values."""
        self.current_index = 0
        self.cursor_pos = None
        self.reveal_time = None
        self.reached_last = False
        logger.debug("State handler reset to initial state")

    def handle_reveal_timeout(self, current_time: float) -> None:
        """
        Auto-hide words after timeout period.

        Args:
            current_time: Current timestamp
        """
        if self.reveal_time and current_time - self.reveal_time > REVEAL_TIMEOUT:
            logger.debug("Auto-hiding revealed word after timeout")
            self.cursor_pos = None
            self.reveal_time = None

    def handle_navigation(
        self, key: int, positions: list[int], scroll_position: int, visible_count: int
    ) -> int:
        """
        Handle navigation (scrolling) input.

        Args:
            key: Input character code (curses.KEY_UP or curses.KEY_DOWN)
            positions: List of word positions
            scroll_position: Current scroll position
            visible_count: Number of currently visible words

        Returns:
            int: New scroll position
        """
        new_position = scroll_position

        # Handle up navigation
        if key == curses.KEY_UP and scroll_position > 0:
            new_position = scroll_position - 1
            logger.debug("Navigation: up to scroll position %s", new_position)

        # Handle down navigation
        elif key == curses.KEY_DOWN and scroll_position < len(positions) - visible_count:
            new_position = scroll_position + 1
            logger.debug("Navigation: down to scroll position %s", new_position)

        return new_position

    def handle_sequential_reveal(self, positions: list[int], current_time: float) -> None:
        """
        Handle sequential reveal ('s' command) logic.

        Args:
            positions: List of word positions
            current_time: Current timestamp
        """
        if not positions:
            return

        # Set current word as revealed
        self.cursor_pos = self.current_index
        self.reveal_time = current_time

        # Move to next word if available
        if self.current_index < len(positions) - 1:
            self.current_index += 1
            logger.debug("Sequential reveal: showing word %s", self.current_index)
        else:
            # Mark as having reached the last word
            self.reached_last = True
            logger.debug("Sequential reveal: reached last word")

    def handle_reset(self, positions: list[int]) -> None:
        """
        Handle reset ('r' command) logic.

        Args:
            positions: List of word positions
        """
        if not self.reached_last:
            return

        logger.debug("Resetting sequence")
        self.reset_positions()
        if positions:
            self.current_index = 0

    def handle_commands(
        self, key: int, positions: list[int], current_time: float
    ) -> list[int] | None:
        """
        Process user commands and update state accordingly.

        Args:
            key: Input character code
            positions: List of word positions
            current_time: Current timestamp

        Returns:
            list[int] | None: New positions list or None if no change
        """
        # Handle new input command
        if key == ord("n"):
            logger.debug("Command: new input")
            self.reset_positions()
            return []

        # Handle sequential reveal command
        if key == ord("s"):
            logger.debug("Command: sequential reveal")
            self.handle_sequential_reveal(positions, current_time)

        # Handle reset command
        if key == ord("r"):
            logger.debug("Command: reset")
            self.handle_reset(positions)

        return None

    def handle_mouse_reveal(self, visible_index: int, current_time: float) -> None:
        """
        Handle mouse hover reveal.

        Args:
            visible_index: Index of word to reveal
            current_time: Current timestamp
        """
        logger.debug("Mouse reveal at index %s", visible_index)
        self.cursor_pos = visible_index
        self.reveal_time = current_time

    def get_display_state(self) -> tuple[int | None, bool]:
        """
        Get current display state.

        Returns:
            tuple[int | None, bool]: Current cursor position and whether last word was reached
        """
        return self.cursor_pos, self.reached_last

    def check_terminal_resize(self, height: int, width: int) -> bool:
        """
        Check if terminal dimensions have changed.

        Args:
            height: Current terminal height
            width: Current terminal width

        Returns:
            bool: True if terminal was resized
        """
        current_dimensions = (height, width)

        # Initialize dimensions if this is the first check
        if self.last_known_dimensions is None:
            self.last_known_dimensions = current_dimensions
            return False

        # Check for changes
        if current_dimensions != self.last_known_dimensions:
            logger.debug(
                "Terminal resized from %s to %s", self.last_known_dimensions, current_dimensions
            )
            self.last_known_dimensions = current_dimensions
            return True

        return False
