import curses
from typing import List


class DisplayHandler:
    """
    Handles display and UI rendering for the secure word interface.
    """

    MASK = "*****"  # Fixed mask for consistent word hiding

    def __init__(self, words: List[str]):
        """
        Initialize the display handler.

        Args:
            words: List of words to manage for display
        """
        self.words = words

    def _add_scroll_indicators(self, stdscr, visible_start: int, visible_end: int,
                               positions: List[int], height: int, width: int) -> None:
        """
        Add scroll indicators to the display if needed.

        Args:
            stdscr: Curses window object
            visible_start: Index of first visible word
            visible_end: Index of last visible word
            positions: List of word positions
            height: Terminal height
            width: Terminal width
        """
        if visible_start > 0:
            try:
                stdscr.addstr(0, width - 10, "↑ More ↑")
            except curses.error:
                pass
        if visible_end < len(positions):
            try:
                stdscr.addstr(height - 7, width - 10, "↓ More ↓")
            except curses.error:
                pass

    def _add_menu(self, stdscr, height: int, is_last_reached: bool) -> None:
        """
        Add command menu to the display.

        Args:
            stdscr: Curses window object
            height: Terminal height
            is_last_reached: Whether the last word has been reached
        """
        menu_y = height - 5
        try:
            stdscr.addstr(menu_y, 0, "Commands:")
            menu_text = "'n' - new input, 's' - show one by one"
            if is_last_reached:
                menu_text += ", 'r' - reset to start"
            stdscr.addstr(menu_y + 1, 0, menu_text)
            stdscr.addstr(menu_y + 2, 0, "'q' - quit, ↑↓ - scroll")
            stdscr.addstr(menu_y + 3, 0, "Mouse over to reveal word")
        except curses.error:
            pass

    def display_words(self, stdscr, positions: List[int], scroll_position: int,
                      cursor_pos: int, is_last_reached: bool) -> int:
        """
        Display words with masking in the terminal interface.

        Args:
            stdscr: Curses window object
            positions: List of word positions to display
            scroll_position: Current scroll position
            cursor_pos: Position of cursor (revealed word)
            is_last_reached: Whether last word has been reached

        Returns:
            int: Number of visible words that could fit in the current view
        """
        height, width = stdscr.getmaxyx()
        max_display_lines = height - 7

        visible_start = scroll_position
        visible_end = min(len(positions), scroll_position + max_display_lines // 2)

        stdscr.clear()

        # Display words
        for i, pos in enumerate(positions[visible_start:visible_end], visible_start):
            word = self.words[pos - 1]
            display_num = i + 1
            display_text = f"{display_num}. {word if cursor_pos == i else self.MASK}"
            try:
                stdscr.addstr(i * 2 - scroll_position * 2, 0, display_text[:width - 1])
            except curses.error:
                pass

        # Add scroll indicators if needed
        self._add_scroll_indicators(stdscr, visible_start, visible_end, positions,
                                    height, width)

        # Add command menu
        self._add_menu(stdscr, height, is_last_reached)

        return visible_end - visible_start

    def calculate_visible_range(self, height: int) -> int:
        """
        Calculate number of words that can be displayed.

        Args:
            height: Terminal height

        Returns:
            int: Maximum number of words that can be displayed
        """
        return (height - 7) // 2

    def handle_scroll(self, current_pos: int, scroll_pos: int, height: int) -> int:
        """
        Calculate new scroll position based on current cursor position.

        Args:
            current_pos: Current cursor position
            scroll_pos: Current scroll position
            height: Terminal height

        Returns:
            int: New scroll position
        """
        max_display_lines = self.calculate_visible_range(height)
        if current_pos >= scroll_pos + max_display_lines:
            return max(0, current_pos - max_display_lines + 1)
        elif current_pos < scroll_pos:
            return current_pos
        return scroll_pos