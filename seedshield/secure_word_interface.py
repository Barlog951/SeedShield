"""
SecureWordInterface: Core module for the SeedShield application.

This module implements the main interface for securely viewing BIP39 seed words
with masking, timed reveals, and memory safety features.
"""

import time
import curses
from dataclasses import dataclass
from typing import List, Optional, Tuple

from .input_handler import InputHandler
from .display_handler import DisplayHandler, DisplayState
from .state_handler import StateHandler
from .ui_manager import UIManager
from .secure_memory import secure_clear_list
from .config import logger, DEFAULT_WORDLIST_FULLPATH, ROW_SPACING

# Mouse events that reveal a word: left press/click, or hover (motion)
REVEAL_MOUSE_EVENTS = (
    curses.BUTTON1_PRESSED | curses.BUTTON1_CLICKED | curses.REPORT_MOUSE_POSITION
)


@dataclass(frozen=True)
class ViewContext:
    """View state for one pass of the display loop."""

    scroll: int
    visible_count: int
    now: float


class SecureWordInterface:  # pylint: disable=too-few-public-methods
    """
    Main controller class for the secure word viewing interface.

    This class coordinates the input, display, and state handlers to provide
    a secure interface for viewing sensitive seed phrases. It is a facade:
    run() is deliberately its only public entry point.
    """

    def __init__(
        self, wordlist_path: str = DEFAULT_WORDLIST_FULLPATH, ui_manager: Optional[UIManager] = None
    ):
        """
        Initialize the secure word interface with handlers and configuration.

        Args:
            wordlist_path: Path to the wordlist file
            ui_manager: Optional UI manager for terminal handling
        """
        self.ui_manager = ui_manager if ui_manager is not None else UIManager()
        self.words: List[str] = []

        # Load wordlist with proper validation
        self._load_wordlist(wordlist_path)

        # Initialize handlers
        self.input_handler = InputHandler(len(self.words))
        self.display_handler = DisplayHandler(self.words)
        self.state_handler = StateHandler()

        logger.debug("SecureWordInterface initialized")

    def _load_wordlist(self, wordlist_path: str) -> None:
        """
        Load and validate the wordlist file.

        Args:
            wordlist_path: Path to the wordlist file

        Raises:
            FileNotFoundError: If the wordlist file cannot be found
            IOError: If there's an error reading the wordlist file
            ValueError: If the wordlist content is invalid
        """
        logger.debug("Loading wordlist from %s", wordlist_path)

        try:
            with open(wordlist_path, "r", encoding="utf-8") as f:
                lines = f.read().splitlines()
        except FileNotFoundError:
            logger.error("Wordlist file not found: %s", wordlist_path)
            raise
        except (OSError, UnicodeDecodeError) as e:
            logger.error("Error reading wordlist file: %s", str(e))
            raise

        self.words = self._validate_wordlist(lines)
        logger.debug("Loaded %s words from wordlist", len(self.words))

    @staticmethod
    def _validate_wordlist(lines: List[str]) -> List[str]:
        """
        Validate wordlist lines; a gap or duplicate would shift every position.

        Args:
            lines: Raw lines of the wordlist file

        Returns:
            List[str]: The words, one per position

        Raises:
            ValueError: If the wordlist is empty or has blank/duplicate entries
        """
        words = [line.strip() for line in lines]
        while words and not words[-1]:
            words.pop()

        if not words:
            raise ValueError("Wordlist is empty")
        if "" in words:
            raise ValueError(f"Wordlist has a blank line at line {words.index('') + 1}")
        if len(set(words)) != len(words):
            raise ValueError("Wordlist contains duplicate words")

        return words

    def _handle_input_mode(self, stdscr: "curses.window") -> Optional[List[int]]:
        """
        Handle the input mode for entering word positions.

        Args:
            stdscr: Curses window objec

        Returns:
            Optional[List[int]]: List of positions or None if user quits
        """
        logger.debug("Entering input mode")
        # No mouse while typing: getstr() beeps on every mouse event
        self.ui_manager.set_mouse_enabled(False)
        try:
            new_positions = self.input_handler.get_input(stdscr)
        finally:
            self.ui_manager.set_mouse_enabled(True)

        if new_positions is not None:
            logger.debug("Received %s positions from input mode", len(new_positions))
            self.state_handler.reset_positions()
            stdscr.timeout(100)
        else:
            logger.debug("User opted to quit from input mode")

        return new_positions

    def _update_display_state(
        self,
        stdscr: "curses.window",
        positions: List[int],
        scroll_position: int,
        current_time: float,
    ) -> Tuple[int, int]:
        """
        Update the display based on current state.

        Args:
            stdscr: Curses window objec
            positions: List of word positions
            scroll_position: Current scroll position
            current_time: Current timestamp

        Returns:
            Tuple[int, int]: Number of visible words and new scroll position
        """
        # Handle any timed auto-hiding of revealed words
        self.state_handler.handle_reveal_timeout(current_time)

        # Get current display state
        cursor_pos, reached_last = self.state_handler.get_display_state()

        # Get terminal dimensions
        height, width = stdscr.getmaxyx()

        # Check for terminal resize
        if self.state_handler.check_terminal_resize(height, width):
            logger.debug("Terminal resize detected, refreshing display")

        # Display words with current state
        visible_count = self.display_handler.display_words(
            stdscr, positions, DisplayState(scroll_position, cursor_pos, reached_last)
        )

        # Handle any autoscrolling needed to keep the cursor in view
        scroll_position = self.display_handler.handle_autoscroll(
            cursor_pos, scroll_position, height
        )

        # Refresh the display
        stdscr.refresh()

        return visible_count, scroll_position

    def _process_user_input(
        self, stdscr: "curses.window", positions: List[int], view: ViewContext
    ) -> Tuple[bool, int]:
        """
        Process user input and update state accordingly.

        Args:
            stdscr: Curses window objec
            positions: List of word positions
            view: Current view state

        Returns:
            Tuple[bool, int]: Whether to continue and new scroll position
        """
        scroll_position = view.scroll
        try:
            # Get user input with timeout
            c = stdscr.getch()

            # Process input if available
            if c != -1:
                should_quit, should_reinit, new_scroll, new_positions = self._handle_user_input(
                    c, positions, view
                )

                if should_reinit:
                    # Clear positions to force entering input mode on next loop
                    positions.clear()

                # Handle quit command
                if should_quit:
                    logger.debug("User requested to quit")
                    return False, scroll_position

                # Update positions if needed
                if new_positions:
                    logger.debug("Updating positions list with %s positions", len(new_positions))
                    positions[:] = new_positions

                # Update scroll position
                scroll_position = new_scroll

        except KeyboardInterrupt:
            logger.debug("Keyboard interrupt detected")
            return False, scroll_position
        except curses.error:
            # Ignore curses errors (like terminal resize)
            pass

        return True, scroll_position

    def _handle_quit_command(self) -> Tuple[bool, bool, int, List[int]]:
        """Handle the quit command."""
        logger.debug("Quit command received")
        return True, False, 0, []

    def _handle_navigation(self, key: int, positions: List[int], view: ViewContext) -> int:
        """
        Handle navigation key inputs.

        Args:
            key: Input key code
            positions: List of positions
            view: Current view state

        Returns:
            int: New scroll position
        """
        logger.debug("Navigation key received: %s", "UP" if key == curses.KEY_UP else "DOWN")
        return self.state_handler.handle_navigation(key, positions, view.scroll, view.visible_count)

    def _handle_command_keys(
        self, key: int, positions: List[int], view: ViewContext
    ) -> Tuple[bool, int, List[int]]:
        """
        Handle command keys (n, s, r).

        Args:
            key: Input key code
            positions: List of positions
            view: Current view state

        Returns:
            Tuple[bool, int, List[int]]: Reinitialize flag, new scroll position, new positions
        """
        should_reinit = False
        new_scroll = view.scroll
        new_positions: List[int] = []

        logger.debug("Command key received: '%s'", chr(key))
        command_result = self.state_handler.handle_commands(key, positions, view.now)

        if command_result is not None:
            new_positions = command_result

        # Handle specific commands
        if key == ord("r"):
            new_scroll = 0
        elif key == ord("n"):
            should_reinit = True

        return should_reinit, new_scroll, new_positions

    def _handle_mouse_event(self, positions: List[int], view: ViewContext) -> None:
        """
        Handle mouse events for word revealing.

        Only a left press/click or hover over a word row that is actually drawn
        reveals anything; the menu, empty rows, releases and wheel are ignored.

        Args:
            positions: List of positions
            view: Current view state
        """
        try:
            _, _, my, _, bstate = curses.getmouse()
        except curses.error as e:
            logger.debug("Error handling mouse event: %s", str(e))
            return

        if not bstate & REVEAL_MOUSE_EVENTS:
            return

        row = my // ROW_SPACING
        if not 0 <= row < view.visible_count:
            return

        visible_index = row + view.scroll
        if visible_index < len(positions):
            logger.debug("Mouse reveal at index %s", visible_index)
            self.state_handler.handle_mouse_reveal(visible_index, view.now)

    def _handle_user_input(
        self, c: int, positions: List[int], view: ViewContext
    ) -> Tuple[bool, bool, int, List[int]]:
        """
        Process a single user input and determine actions.

        Args:
            c: Input character code
            positions: List of word positions
            view: Current view state

        Returns:
            Tuple[bool, bool, int, List[int]]:
                Whether to quit, whether to reinitialize input mode,
                new scroll position, and new positions (if any)
        """
        # Initialize default return values
        should_quit = False
        should_reinit = False
        new_scroll = view.scroll
        new_positions: List[int] = []

        # Handle different input types
        if c in (ord("q"), ord("Q")):
            should_quit, should_reinit, new_scroll, new_positions = self._handle_quit_command()

        elif c in (curses.KEY_UP, curses.KEY_DOWN):
            new_scroll = self._handle_navigation(c, positions, view)

        elif c in (ord("n"), ord("s"), ord("r")):
            should_reinit, new_scroll, new_positions = self._handle_command_keys(c, positions, view)

        elif c == curses.KEY_MOUSE:
            self._handle_mouse_event(positions, view)

        # Return all state changes
        return should_quit, should_reinit, new_scroll, new_positions

    def _load_positions_file(self, file_path: str) -> List[int]:
        """
        Load word positions from a file.

        Args:
            file_path: Path to the file containing positions

        Returns:
            List[int]: Loaded positions

        Raises:
            ValueError: If the file is unreadable or has no/invalid positions
        """
        logger.debug("Loading positions from file")
        file_positions = self.input_handler.load_positions_from_file(file_path)

        if not file_positions:
            raise ValueError(
                "Invalid input file: expected a readable UTF-8 text file with only "
                f"positions 1-{len(self.words)} separated by spaces, commas or newlines"
            )

        return file_positions

    def _main_display_loop(self, stdscr: "curses.window", positions: List[int]) -> None:
        """
        Run the main display loop for showing words and handling interaction.

        Args:
            stdscr: Curses window objec
            positions: List of positions to display
        """
        scroll_position = 0

        while True:
            # Check if we need to enter input mode
            if not positions:
                new_positions = self._handle_input_mode(stdscr)
                if new_positions is None:
                    break
                positions[:] = new_positions
                continue

            # Display mode - show words and handle interaction
            current_time = time.time()

            # Update display and process input
            visible_count, scroll_position = self._update_display_state(
                stdscr, positions, scroll_position, current_time
            )

            should_continue, scroll_position = self._process_user_input(
                stdscr, positions, ViewContext(scroll_position, visible_count, current_time)
            )

            if not should_continue:
                break

    def run(self, positions_file: Optional[str] = None) -> None:
        """
        Run the secure word interface main loop.

        Args:
            positions_file: Optional file with word positions to load

        Raises:
            Exception: If there's an error during execution
        """
        positions: List[int] = []

        def run_interface() -> None:
            """Inner function to run with UI context."""
            self._main_display_loop(self.ui_manager.stdscr, positions)

        try:
            # Validate the file before touching the terminal so errors are
            # reported cleanly on stderr
            if positions_file:
                positions = self._load_positions_file(positions_file)

            logger.debug("Starting secure word interface")
            self.ui_manager.with_ui_context(run_interface)
        finally:
            # Securely clear sensitive data on every exit path
            logger.debug("Securely clearing sensitive data")
            secure_clear_list(self.words)
            secure_clear_list(positions)
