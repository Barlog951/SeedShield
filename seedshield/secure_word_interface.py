"""
SecureWordInterface: Core module for the SeedShield application.

This module implements the main interface for securely viewing BIP39 seed words
with masking, timed reveals, and memory safety features.
"""

import time
import curses
from typing import List, Optional, Tuple, Any, Callable

from .input_handler import InputHandler
from .display_handler import DisplayHandler
from .state_handler import StateHandler
from .ui_manager import UIManager
from .secure_memory import secure_clear_list
from .config import logger, DEFAULT_WORDLIST_FULLPATH


class SecureWordInterface:
    """
    Main controller class for the secure word viewing interface.

    This class coordinates the input, display, and state handlers to provide
    a secure interface for viewing sensitive seed phrases.
    """

    def __init__(self, wordlist_path: str = DEFAULT_WORDLIST_FULLPATH,
                 ui_manager: Optional[UIManager] = None):
        """
        Initialize the secure word interface with handlers and configuration.

        Args:
            wordlist_path: Path to the wordlist file
            ui_manager: Optional UI manager for terminal handling
        """
        # For backward compatibility with tests that don't pass the ui_manager
        self.ui_manager = ui_manager if ui_manager is not None else UIManager()
        self.words: List[str] = []

        # Load wordlist with proper validation
        self._load_wordlist(wordlist_path)

        # Initialize handlers
        self.input_handler = InputHandler(len(self.words), self.ui_manager)
        self.display_handler = DisplayHandler(self.words, self.ui_manager)
        self.state_handler = StateHandler()

        # For backward compatibility with tests
        self._initialize_curses = self.ui_manager.initialize
        self._cleanup_curses = self.ui_manager.cleanup

        # Extract complex lambda expressions to improve readability
        self._handle_autoscroll = self._get_handle_autoscroll_func()
        self._handle_commands = self._backwards_compat_handle_commands
        self._load_positions_from_file = self._get_load_positions_func()

        logger.debug("SecureWordInterface initialized")

    def _load_wordlist(self, wordlist_path: str) -> None:
        """
        Load and validate the wordlist file.

        Args:
            wordlist_path: Path to the wordlist file

        Raises:
            FileNotFoundError: If the wordlist file cannot be found
            IOError: If there's an error reading the wordlist file
        """
        logger.debug("Loading wordlist from %s", wordlist_path)

        try:
            with open(wordlist_path, 'r', encoding='utf-8') as f:
                self.words = [word.strip() for word in f.readlines()]

            if not self.words:
                raise ValueError("Wordlist is empty")

            logger.debug("Loaded %s words from wordlist", len(self.words))

        except FileNotFoundError:
            logger.error("Wordlist file not found: %s", wordlist_path)
            raise
        except IOError as e:
            logger.error("Error reading wordlist file: %s", str(e))
            raise
        except Exception as e:
            logger.error("Unexpected error loading wordlist: %s", str(e))
            raise

    def _handle_input_mode(self, stdscr: Any) -> Optional[List[int]]:
        """
        Handle the input mode for entering word positions.

        Args:
            stdscr: Curses window objec

        Returns:
            Optional[List[int]]: List of positions or None if user quits
        """
        logger.debug("Entering input mode")
        new_positions = self.input_handler.get_input(stdscr)

        if new_positions is not None:
            logger.debug("Received %s positions from input mode", len(new_positions))
            self.state_handler.reset_positions()
            stdscr.timeout(100)
        else:
            logger.debug("User opted to quit from input mode")

        return new_positions

    def _update_display_state(self, stdscr: Any, positions: List[int], scroll_position: int,
                             current_time: float) -> Tuple[int, int]:
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
            stdscr, positions, scroll_position, cursor_pos, reached_last)

        # Handle any autoscrolling needed to keep the cursor in view
        scroll_position = self.display_handler.handle_autoscroll(
            cursor_pos, scroll_position, height)

        # Refresh the display
        stdscr.refresh()

        return visible_count, scroll_position

    def _backwards_compat_handle_commands(self, key: int, positions: List[int], current_time: float,
                           scroll_position: int) -> Tuple[bool, List[int], int]:
        """
        Backward compatibility method for tests.

        Args:
            key: Key code
            positions: List of positions
            current_time: Current time
            scroll_position: Current scroll position

        Returns:
            Tuple[bool, List[int], int]: Whether to reinit, new positions, new scroll
        """
        should_reinit = False
        new_scroll = scroll_position
        new_positions: List[int] = []

        command_result = self.state_handler.handle_commands(key, positions, current_time)
        if command_result is not None:
            new_positions = command_result
        if key == ord('r'):
            new_scroll = 0
        if key == ord('n'):
            should_reinit = True

        return should_reinit, new_positions, new_scroll

    def _process_user_input(self, stdscr: Any, positions: List[int], scroll_position: int,
                          visible_count: int, current_time: float) -> Tuple[bool, int]:
        """
        Process user input and update state accordingly.

        Args:
            stdscr: Curses window objec
            positions: List of word positions
            scroll_position: Current scroll position
            visible_count: Number of visible words
            current_time: Current timestamp

        Returns:
            Tuple[bool, int]: Whether to continue and new scroll position
        """
        try:
            # Get user input with timeout
            c = stdscr.getch()

            # Process input if available
            if c != -1:
                should_quit, should_reinit, new_scroll, new_positions = self._handle_user_input(
                    c, positions, scroll_position, visible_count, current_time)

                # Handle timeout adjustment for input mode
                if should_reinit:
                    stdscr.timeout(10000)

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

        # Small sleep to avoid CPU spinning
        time.sleep(0.05)
        return True, scroll_position

    def _handle_quit_command(self) -> Tuple[bool, bool, int, List[int]]:
        """Handle the quit command."""
        logger.debug("Quit command received")
        return True, False, 0, []

    def _handle_navigation(self, key: int, positions: List[int],
                           scroll_position: int, visible_count: int) -> int:
        """
        Handle navigation key inputs.

        Args:
            key: Input key code
            positions: List of positions
            scroll_position: Current scroll position
            visible_count: Number of visible positions

        Returns:
            int: New scroll position
        """
        logger.debug("Navigation key received: %s",
                   'UP' if key == curses.KEY_UP else 'DOWN')
        return self.state_handler.handle_navigation(
            key, positions, scroll_position, visible_count)

    def _handle_command_keys(self, key: int, positions: List[int],
                            current_time: float, scroll_position: int
                            ) -> Tuple[bool, int, List[int]]:
        """
        Handle command keys (n, s, r).

        Args:
            key: Input key code
            positions: List of positions
            current_time: Current timestamp
            scroll_position: Current scroll position

        Returns:
            Tuple[bool, int, List[int]]: Reinitialize flag, new scroll position, new positions
        """
        should_reinit = False
        new_scroll = scroll_position
        new_positions: List[int] = []

        logger.debug("Command key received: '%s'", chr(key))
        command_result = self.state_handler.handle_commands(key, positions, current_time)

        if command_result is not None:
            new_positions = command_result

        # Handle specific commands
        if key == ord('r'):
            new_scroll = 0
        elif key == ord('n'):
            should_reinit = True

        return should_reinit, new_scroll, new_positions

    def _handle_mouse_event(self, positions: List[int],
                           scroll_position: int, current_time: float) -> None:
        """
        Handle mouse events for word revealing.

        Args:
            positions: List of positions
            scroll_position: Current scroll position
            current_time: Current timestamp
        """
        try:
            mouse_event = curses.getmouse()
            _, _, my, _, _ = mouse_event
            visible_index = my // 2 + scroll_position

            if 0 <= visible_index < len(positions):
                logger.debug("Mouse reveal at index %s", visible_index)
                self.state_handler.handle_mouse_reveal(visible_index, current_time)
        except Exception as e:
            logger.debug("Error handling mouse event: %s", str(e))

    def _handle_user_input(self, c: int, positions: List[int], scroll_position: int,
                         visible_count: int, current_time: float
                         ) -> Tuple[bool, bool, int, List[int]]:
        """
        Process a single user input and determine actions.

        Args:
            c: Input character code
            positions: List of word positions
            scroll_position: Current scroll position
            visible_count: Number of visible words
            current_time: Current timestamp

        Returns:
            Tuple[bool, bool, int, List[int]]:
                Whether to quit, whether to reinitialize input mode,
                new scroll position, and new positions (if any)
        """
        # Initialize default return values
        should_quit = False
        should_reinit = False
        new_scroll = scroll_position
        new_positions: List[int] = []

        # Handle different input types
        if c == ord('q'):
            should_quit, should_reinit, new_scroll, new_positions = self._handle_quit_command()

        elif c in (curses.KEY_UP, curses.KEY_DOWN):
            new_scroll = self._handle_navigation(c, positions, scroll_position, visible_count)

        elif c in (ord('n'), ord('s'), ord('r')):
            should_reinit, new_scroll, new_positions = self._handle_command_keys(
                c, positions, current_time, scroll_position)

        elif c == curses.KEY_MOUSE:
            self._handle_mouse_event(positions, scroll_position, current_time)

        # Return all state changes
        return should_quit, should_reinit, new_scroll, new_positions

    def _get_load_positions_func(self) -> Callable[[str], Optional[List[int]]]:
        """Return a function that loads positions from a file."""
        return self.input_handler.load_positions_from_file
        
    def _get_handle_autoscroll_func(self) -> Callable[[Optional[int], int, int], int]:
        """Return a function that handles autoscrolling."""
        return self.display_handler.handle_autoscroll
        
    def _load_positions_file(self, file_path: str) -> List[int]:
        """
        Load word positions from a file.

        Args:
            file_path: Path to the file containing positions

        Returns:
            List[int]: Loaded positions or empty list if no valid positions

        Raises:
            FileNotFoundError: If the file doesn't exist
            IOError: If there's an I/O error with the file
            ValueError: If the file contains invalid data
        """
        try:
            logger.debug("Loading positions from file: %s", file_path)
            file_positions = self.input_handler.load_positions_from_file(file_path)

            if not file_positions:
                logger.warning("No valid positions found in input file")
                return []

            return file_positions
        except (FileNotFoundError, IOError, ValueError) as e:
            logger.error("Error loading positions file: %s", str(e))
            raise
        except Exception as e:
            logger.error("Unexpected error loading positions file: %s", str(e))
            raise ValueError(f"Error processing positions file: {str(e)}") from e

    def _main_display_loop(self, stdscr: Any, positions: List[int]) -> None:
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
                stdscr, positions, scroll_position, current_time)

            should_continue, scroll_position = self._process_user_input(
                stdscr, positions, scroll_position, visible_count, current_time)

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
        def run_interface() -> None:
            """Inner function to run with UI context."""
            positions: List[int] = []

            # Load positions from file if provided
            if positions_file:
                positions = self._load_positions_file(positions_file)

            try:
                # Run the main application loop
                self._main_display_loop(self.ui_manager.stdscr, positions)
            finally:
                # Securely clear sensitive data
                logger.debug("Securely clearing sensitive data")
                secure_clear_list(self.words)
                secure_clear_list(positions)

        # Run the interface with proper UI context management
        logger.debug("Starting secure word interface")
        self.ui_manager.with_ui_context(run_interface)
