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
        curses.nocbreak()
        stdscr.keypad(False)
        curses.echo()
        curses.endwin()

    def _handle_input_mode(self, stdscr) -> Optional[List[int]]:
        new_positions = self.input_handler.get_input(stdscr)
        if new_positions is not None:
            self.state_handler.reset_positions()
            stdscr.timeout(100)
        return new_positions

    def _update_display_state(self, stdscr, positions: List[int], scroll_position: int,
                              current_time: float) -> Tuple[int, int]:
        self.state_handler.handle_reveal_timeout(current_time)
        cursor_pos, reached_last = self.state_handler.get_display_state()
        height, _ = stdscr.getmaxyx()

        visible_count = self.display_handler.display_words(
            stdscr, positions, scroll_position, cursor_pos, reached_last)

        scroll_position = self._handle_autoscroll(cursor_pos, scroll_position, height)
        stdscr.refresh()

        return visible_count, scroll_position

    def _process_user_input(self, stdscr, positions: List[int], scroll_position: int,
                            visible_count: int, current_time: float) -> Tuple[bool, int]:
        try:
            c = stdscr.getch()
            if c != -1:
                should_quit, should_reinit, new_scroll, new_positions = self._handle_user_input(
                    c, positions, scroll_position, visible_count, current_time)

                if should_reinit:
                    stdscr.timeout(10000)
                if should_quit:
                    return False, scroll_position

                if new_positions:
                    positions[:] = new_positions

                scroll_position = new_scroll

        except curses.error:
            pass

        time.sleep(0.1)
        return True, scroll_position

    def _handle_navigation(self, key: int, scroll_position: int, positions: List[int],
                          visible_count: int) -> int:
        if key == curses.KEY_UP and scroll_position > 0:
            return scroll_position - 1
        elif key == curses.KEY_DOWN and scroll_position < len(positions) - visible_count:
            return scroll_position + 1
        return scroll_position

    def _handle_commands(self, key: int, positions: List[int], current_time: float,
                       scroll_position: int) -> Tuple[bool, List[int], int]:
        should_reinit = False
        new_scroll = scroll_position
        new_positions = []

        command_result = self.state_handler.handle_commands(key, positions, current_time)
        if command_result is not None:
            new_positions = command_result
        if key == ord('r'):
            new_scroll = 0
        if key == ord('n'):
            should_reinit = True

        return should_reinit, new_positions, new_scroll

    def _handle_user_input(self, c: int, positions: List[int], scroll_position: int,
                           visible_count: int, current_time: float
                           ) -> Tuple[bool, bool, int, List[int]]:
        should_quit = False
        should_reinit = False
        new_scroll = scroll_position
        new_positions = []

        if c == ord('q'):
            should_quit = True
        elif c in (curses.KEY_UP, curses.KEY_DOWN):
            new_scroll = self._handle_navigation(c, scroll_position, positions, visible_count)
        elif c in (ord('n'), ord('s'), ord('r')):
            should_reinit, new_positions, new_scroll = self._handle_commands(c, positions, current_time, scroll_position)
        elif c == curses.KEY_MOUSE:
            _, _, my, mx, _ = curses.getmouse()
            visible_index = my // 2 + scroll_position
            if 0 <= visible_index < len(positions):
                self.state_handler.handle_mouse_reveal(visible_index, current_time)

        return should_quit, should_reinit, new_scroll, new_positions

    def _handle_autoscroll(self, cursor_pos: Optional[int], scroll_position: int,
                           height: int) -> int:
        if cursor_pos is None:
            return scroll_position

        max_display_lines = (height - 7) // 2
        if cursor_pos >= scroll_position + max_display_lines:
            return cursor_pos - max_display_lines + 1
        elif cursor_pos < scroll_position:
            return cursor_pos
        return scroll_position

    def _load_positions_from_file(self, positions_file: str) -> List[int]:
        with open(positions_file, 'r') as f:
            return [int(line.strip()) for line in f if line.strip().isdigit()]

    def run(self, positions_file: Optional[str] = None) -> None:
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

                should_continue, scroll_position = self._process_user_input(
                    stdscr, positions, scroll_position, visible_count, current_time)
                if not should_continue:
                    break

        except Exception as e:
            self._cleanup_curses(stdscr)
            raise e
        finally:
            self._cleanup_curses(stdscr)