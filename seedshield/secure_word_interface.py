import curses
import time
import os
import sys
from typing import List, Optional, Tuple

from .input_handler import InputHandler
from .display_handler import DisplayHandler
from .state_handler import StateHandler

DEFAULT_WORDLIST_PATH = "english.txt"


class SecureWordInterface:
    """Secure interface for viewing and interacting with BIP39 words."""

    def __init__(self, wordlist_path: str = DEFAULT_WORDLIST_PATH):
        if wordlist_path == DEFAULT_WORDLIST_PATH:
            wordlist_path = os.path.join(os.path.dirname(__file__), "data",
                                         DEFAULT_WORDLIST_PATH)

        try:
            with open(wordlist_path, 'r') as f:
                self.words = [word.strip() for word in f.readlines()]
        except Exception as e:
            if 'stdscr' in locals():
                curses.endwin()
            raise e

        self.input_handler = InputHandler(len(self.words))
        self.display_handler = DisplayHandler(self.words)
        self.state_handler = StateHandler()

    def _initialize_curses(self):
        """Initialize curses settings and return screen object."""
        stdscr = curses.initscr()
        curses.start_color()
        curses.mousemask(curses.ALL_MOUSE_EVENTS | curses.REPORT_MOUSE_POSITION)
        curses.noecho()
        curses.cbreak()
        stdscr.keypad(True)

        if sys.stdin.isatty():
            curses.halfdelay(1)
        else:
            stdscr.timeout(100)
        return stdscr

    def _cleanup_curses(self, stdscr):
        """Clean up curses settings."""
        curses.nocbreak()
        stdscr.keypad(False)
        curses.echo()
        curses.endwin()

    def _handle_input_mode(self, stdscr) -> Optional[List[int]]:
        """Handle input mode for getting new positions."""
        new_positions = self.input_handler.get_input(stdscr)
        if new_positions is not None:
            self.state_handler.reset_positions()
            stdscr.timeout(100)
        return new_positions

    def _update_display_state(self, stdscr, positions: List[int], scroll_position: int,
                              current_time: float) -> Tuple[int, int]:
        """Update display state and return visible count."""
        self.state_handler.handle_reveal_timeout(current_time)
        cursor_pos, reached_last = self.state_handler.get_display_state()

        height, _ = stdscr.getmaxyx()
        scroll_position = self._handle_autoscroll(cursor_pos, scroll_position, height)

        visible_count = self.display_handler.display_words(
            stdscr, positions, scroll_position, cursor_pos, reached_last)
        stdscr.refresh()

        return visible_count, scroll_position

    def _process_user_input(self, stdscr, positions: List[int], scroll_position: int,
                            visible_count: int, current_time: float) -> bool:
        """Process user input and return whether to continue running."""
        try:
            c = stdscr.getch()
            if c != -1:  # -1 means "no input" in timeout mode
                should_quit, should_reinit, new_scroll, new_positions = self._handle_user_input(
                    c, positions, scroll_position, visible_count, current_time)

                if should_reinit:
                    stdscr.timeout(10000)
                if should_quit:
                    return False

                positions[:] = new_positions  # Update positions in-place
                scroll_position = new_scroll
        except curses.error:
            pass

        time.sleep(0.1)  # Prevent CPU hogging
        return True

    def _handle_user_input(self, c: int, positions: List[int], scroll_position: int,
                           visible_count: int, current_time: float
                           ) -> Tuple[bool, bool, int, List[int]]:
        """Handle user input and return updated state."""
        should_quit = False
        should_reinit = False

        if c == ord('q'):
            should_quit = True

        elif c in (curses.KEY_UP, curses.KEY_DOWN):
            scroll_position = self.state_handler.handle_navigation(
                c, positions, scroll_position, visible_count)

        elif c in (ord('n'), ord('s'), ord('r')):
            command_result = self.state_handler.handle_commands(c, positions, current_time)
            if command_result is not None:
                positions = command_result
            if c == ord('r'):
                scroll_position = 0
            if c == ord('n'):
                should_reinit = True

        elif c == curses.KEY_MOUSE:
            _, _, my, mx, _ = curses.getmouse()
            visible_index = my // 2 + scroll_position
            if 0 <= visible_index < len(positions):
                self.state_handler.handle_mouse_reveal(visible_index, current_time)

        return should_quit, should_reinit, scroll_position, positions

    def _handle_autoscroll(self, cursor_pos: Optional[int], scroll_position: int,
                           height: int) -> int:
        """Adjust scroll position if cursor or revealed item goes out of view."""
        if cursor_pos is None:
            return scroll_position

        max_display_lines = (height - 7) // 2
        if cursor_pos >= scroll_position + max_display_lines:
            return cursor_pos - max_display_lines + 1
        elif cursor_pos < scroll_position:
            return cursor_pos
        return scroll_position

    def _load_positions_from_file(self, positions_file: str) -> List[int]:
        """Load positions from file."""
        with open(positions_file, 'r') as f:
            return [int(line.strip()) for line in f if line.strip().isdigit()]

    def run(self, positions_file: Optional[str] = None) -> None:
        """Run the secure interface."""
        positions: List[int] = []
        scroll_position = 0

        if positions_file:
            positions = self._load_positions_from_file(positions_file)

        stdscr = self._initialize_curses()

        try:
            while True:
                if not positions:
                    new_positions = self._handle_input_mode(stdscr)
                    if new_positions is None:
                        break
                    positions = new_positions
                    continue

                current_time = time.time()
                visible_count, scroll_position = self._update_display_state(
                    stdscr, positions, scroll_position, current_time)

                if not self._process_user_input(
                        stdscr, positions, scroll_position, visible_count, current_time):
                    break

        except Exception as e:
            self._cleanup_curses(stdscr)
            raise e
        finally:
            self._cleanup_curses(stdscr)