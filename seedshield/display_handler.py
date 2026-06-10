"""
Display handling for the SeedShield application.

This module manages the visual presentation of seed phrases,
ensuring proper masking and interaction.
"""

import curses
from dataclasses import dataclass
from typing import List, Optional, Any

from .config import logger, MASK_CHARACTER, MASK_LENGTH
from .config import SCROLL_INDICATOR_UP, SCROLL_INDICATOR_DOWN, MENU_TEXT
from .state_handler import StateHandler


@dataclass(frozen=True)
class Viewport:
    """Terminal viewport for one render pass; start doubles as scroll position."""

    height: int
    width: int
    start: int
    end: int


@dataclass(frozen=True)
class WordRow:
    """A single word row ready for rendering."""

    word: str
    display_num: int
    y_pos: int
    revealed: bool


@dataclass(frozen=True)
class DisplayState:
    """View state for one display pass."""

    scroll: int
    cursor: Optional[int]
    reached_last: bool


class DisplayHandler:
    """
    Handles display and UI rendering for the secure word interface.

    This class is responsible for:
    - Rendering words with proper masking
    - Calculating display metrics (visible ranges, scroll positions)
    - Managing UI elements (scroll indicators, command menu)
    - Handling terminal size changes
    """

    def __init__(self, words: List[str], ui_manager: Any = None) -> None:
        """
        Initialize the display handler.

        Args:
            words: List of words to manage for display
            ui_manager: Optional UI manager for abstracted rendering
        """
        self.words = words
        self.ui_manager = ui_manager
        self.mask = MASK_CHARACTER * MASK_LENGTH
        self.state_handler: Optional[StateHandler] = None  # Will be set later

        # Store the last state to optimize rendering
        self._last_height = 0
        self._last_width = 0

        logger.debug("DisplayHandler initialized with %s words", len(words))

    def _add_scroll_indicators(self, stdscr: Any, viewport: Viewport, total: int) -> None:
        """
        Add scroll indicators to the display if needed.

        Args:
            stdscr: Curses window objec
            viewport: Current terminal viewport
            total: Total number of positions in the list
        """
        # Show up indicator if there are hidden items above
        if viewport.start > 0:
            try:
                stdscr.addstr(
                    0, max(0, viewport.width - len(SCROLL_INDICATOR_UP) - 1), SCROLL_INDICATOR_UP
                )
                logger.debug(
                    "Added up scroll indicator at position 0,%s",
                    viewport.width - len(SCROLL_INDICATOR_UP) - 1,
                )
            except curses.error:
                pass

        # Show down indicator if there are hidden items below
        if viewport.end < total:
            try:
                stdscr.addstr(
                    viewport.height - 7,
                    max(0, viewport.width - len(SCROLL_INDICATOR_DOWN) - 1),
                    SCROLL_INDICATOR_DOWN,
                )
                logger.debug(
                    "Added down scroll indicator at position %s,%s",
                    viewport.height - 7,
                    viewport.width - len(SCROLL_INDICATOR_DOWN) - 1,
                )
            except curses.error:
                pass

    def _add_menu(self, stdscr: Any, height: int, is_last_reached: bool) -> None:
        """
        Add command menu to the display.

        Args:
            stdscr: Curses window objec
            height: Terminal heigh
            is_last_reached: Whether the last word has been reached
        """
        menu_y = height - 5

        try:
            # Display appropriate command menu based on state
            stdscr.addstr(menu_y, 0, "Commands:")

            # Show reset option only if we've reached the last word
            menu_text = MENU_TEXT["with_reset"] if is_last_reached else MENU_TEXT["standard"]
            # We no longer show the wordlist info on any screen to avoid blocking words

            # Split menu text across lines if it's too long
            if len(menu_text) > self._last_width - 2:
                # Simple word wrapping
                words = menu_text.split()
                line1: List[str] = []
                line2: List[str] = []
                current_line = line1
                current_length = 0

                for word in words:
                    if current_length + len(word) + 1 > self._last_width - 2:
                        current_line = line2
                        current_length = 0
                    current_line.append(word)
                    current_length += len(word) + 1

                stdscr.addstr(menu_y + 1, 0, " ".join(line1))
                stdscr.addstr(menu_y + 2, 0, " ".join(line2))
                stdscr.addstr(menu_y + 3, 0, MENU_TEXT["mouse_help"])
            else:
                # Menu fits on one line
                stdscr.addstr(menu_y + 1, 0, menu_text)
                stdscr.addstr(menu_y + 2, 0, MENU_TEXT["mouse_help"])
        except curses.error:
            # Handle terminal too small for menu
            logger.debug("Terminal too small to display full menu")
            try:
                # Try to show a condensed menu
                stdscr.addstr(menu_y, 0, "n:new s:seq q:quit")
            except curses.error:
                pass

    def _render_word(self, stdscr: Any, row: WordRow, width: int) -> None:
        """
        Render a single word with proper masking and formatting.

        Args:
            stdscr: Curses window objec
            row: The word row to render
            width: Terminal width
        """
        display_text = f"{row.display_num:2d}. {row.word if row.revealed else self.mask}"

        # Ensure text fits within terminal width
        if len(display_text) >= width:
            display_text = display_text[: width - 1]

        # Highlight revealed word
        if row.revealed:
            stdscr.addstr(row.y_pos, 0, display_text, curses.A_BOLD)
        else:
            stdscr.addstr(row.y_pos, 0, display_text)

    def _get_word_for_position(self, pos: int) -> str:
        """
        Get the word corresponding to the given position.

        Args:
            pos: Position in the wordlist (1-based index)

        Returns:
            str: The word at the given position or an error message
        """
        if 0 <= pos - 1 < len(self.words):
            return self.words[pos - 1]

        # Never log the position value: positions encode the seed
        logger.warning("Invalid word position requested")
        return f"INVALID({pos})"

    def display_words(self, stdscr: Any, positions: List[int], state: DisplayState) -> int:
        """
        Display words with masking in the terminal interface.

        Args:
            stdscr: Curses window objec
            positions: List of word positions to display
            state: Current view state (scroll, cursor, reached_last)

        Returns:
            int: Number of visible words that could fit in the current view
        """
        # Get terminal dimensions
        height, width = stdscr.getmaxyx()
        self._last_height = height
        self._last_width = width

        # Calculate display metrics
        max_display_lines = max(1, height - 7)  # Reserve space for menu and indicators
        viewport = Viewport(
            height=height,
            width=width,
            start=state.scroll,
            end=min(len(positions), state.scroll + max_display_lines // 2),
        )

        logger.debug("Displaying words %s-%s of %s", viewport.start, viewport.end, len(positions))

        # Clear screen for fresh rendering
        stdscr.clear()

        # Display words with proper masking
        self._display_visible_words(stdscr, positions, viewport, state.cursor)

        # Add scroll indicators if needed
        self._add_scroll_indicators(stdscr, viewport, len(positions))

        # Add command menu
        self._add_menu(stdscr, height, state.reached_last)

        # Return number of visible words
        result: int = viewport.end - viewport.start
        return result

    def _display_visible_words(
        self, stdscr: Any, positions: List[int], viewport: Viewport, cursor_pos: Optional[int]
    ) -> None:
        """
        Display the visible words on the screen.

        Args:
            stdscr: Curses window objec
            positions: List of word positions
            viewport: Current terminal viewport
            cursor_pos: Position of cursor (revealed word)
        """
        for i, pos in enumerate(positions[viewport.start : viewport.end], viewport.start):
            try:
                # Get word for the position
                word = self._get_word_for_position(pos)

                # Calculate position and check if it's visible
                y_pos = i * 2 - viewport.start * 2

                # Only render if within displayable area
                if 0 <= y_pos < viewport.height - 6:
                    row = WordRow(
                        word=word, display_num=i + 1, y_pos=y_pos, revealed=cursor_pos == i
                    )
                    self._render_word(stdscr, row, viewport.width)

            except curses.error:
                # Handle rendering errors
                logger.debug("Error displaying word at position %s", i)
            except Exception as e:  # pylint: disable=broad-exception-caught
                # Handle unexpected errors
                logger.error("Unexpected error displaying word at position %s: %s", i, str(e))

    def calculate_visible_range(self, height: int) -> int:
        """
        Calculate number of words that can be displayed.

        Args:
            height: Terminal heigh

        Returns:
            int: Maximum number of words that can be displayed
        """
        # Ensure at least one word is visible
        return max(1, (height - 7) // 2)

    def handle_autoscroll(self, current_pos: Optional[int], scroll_pos: int, height: int) -> int:
        """
        Calculate new scroll position based on current cursor position.
        Implements auto-scrolling to keep the current word visible.

        Args:
            current_pos: Current cursor position
            scroll_pos: Current scroll position
            height: Terminal heigh

        Returns:
            int: New scroll position
        """
        # If no current position, maintain current scroll
        if current_pos is None:
            return scroll_pos

        # Calculate visible range
        max_display_lines = self.calculate_visible_range(height)

        # If cursor is below visible area, scroll down
        if current_pos >= scroll_pos + max_display_lines:
            new_pos = max(0, current_pos - max_display_lines + 1)
            logger.debug("Auto-scrolling down to position %s", new_pos)
            return new_pos

        # If cursor is above visible area, scroll up
        if current_pos < scroll_pos:
            logger.debug("Auto-scrolling up to position %s", current_pos)
            return current_pos

        # Cursor is already visible
        return scroll_pos
