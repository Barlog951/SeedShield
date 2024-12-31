import time
from typing import List, Optional, Tuple
import curses


class StateHandler:
    """
    Manages state and command handling for the secure word interface.
    """

    REVEAL_TIMEOUT = 3  # Seconds before auto-hiding

    def __init__(self):
        self.cursor_pos = None
        self.reveal_time = None
        self.current_index = 0
        self.reached_last = False

    def reset_positions(self) -> None:
        self.current_index = 0
        self.cursor_pos = None
        self.reveal_time = None
        self.reached_last = False

    def handle_reveal_timeout(self, current_time: float) -> None:
        if self.reveal_time and current_time - self.reveal_time > self.REVEAL_TIMEOUT:
            self.cursor_pos = None
            self.reveal_time = None

    def handle_navigation(self, c: int, positions: List[int], scroll_position: int,
                          visible_count: int) -> int:
        """
        Handle navigation (scrolling) input.

        Args:
            c: Input character code (curses.KEY_UP or curses.KEY_DOWN)
            positions: List of word positions
            scroll_position: Current scroll position
            visible_count: Number of currently visible words
        """
        if c == curses.KEY_UP and scroll_position > 0:
            return scroll_position - 1
        elif c == curses.KEY_DOWN and scroll_position < len(positions) - visible_count:
            return scroll_position + 1
        return scroll_position

    def handle_commands(self, c: int, positions: List[int], current_time: float) -> Optional[
        List[int]]:
        if c == ord('n'):  # New input
            self.reset_positions()
            return []

        elif c == ord('s'):  # Step-wise reveal
            if positions:
                self.cursor_pos = self.current_index
                self.reveal_time = current_time
                if self.current_index < len(positions) - 1:
                    self.current_index += 1
                else:
                    self.reached_last = True

        elif c == ord('r') and self.reached_last:  # Reset
            self.reset_positions()
            if positions:
                self.current_index = 0

        return None

    def handle_mouse_reveal(self, visible_index: int, current_time: float) -> None:
        self.cursor_pos = visible_index
        self.reveal_time = current_time

    def get_display_state(self) -> Tuple[Optional[int], bool]:
        return self.cursor_pos, self.reached_last

    def handle_scroll(self, positions: List[int], scroll_position: int, visible_count: int,
                      direction: int) -> int:
        """Handle scrolling navigation."""
        if direction == curses.KEY_UP and scroll_position > 0:
            return scroll_position - 1
        elif direction == curses.KEY_DOWN and scroll_position < len(positions) - visible_count:
            return scroll_position + 1
        return scroll_position