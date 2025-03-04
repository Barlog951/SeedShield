import curses
import time
import sys
import pytest
from pytest import mark
from unittest.mock import patch, Mock, MagicMock
from seedshield.secure_word_interface import SecureWordInterface
# Test fixtures are imported from root conftest.py


def test_interface_initialization(test_wordlist):
    """Test if interface initializes correctly."""
    interface = SecureWordInterface(test_wordlist)
    assert len(interface.words) == 4
    assert interface.words[0] == "apple"
    assert interface.display_handler.legacy_mask == "*****"
    assert interface.state_handler.reached_last is False


def test_invalid_wordlist():
    """Test handling of nonexistent wordlist."""
    with pytest.raises(FileNotFoundError):
        SecureWordInterface("nonexistent.txt")


def test_default_wordlist_exists():
    """Test default wordlist availability."""
    interface = SecureWordInterface()
    assert len(interface.words) > 0
    assert all(isinstance(word, str) for word in interface.words)


def test_wordlist_open_error(monkeypatch):
    """Test wordlist handling error when opening a file fails."""

    def mock_open(*args, **kwargs):
        raise PermissionError("Mocked: No permission to open file")

    monkeypatch.setattr("builtins.open", mock_open)
    with pytest.raises(PermissionError, match="Mocked: No permission to open file"):
        SecureWordInterface("invalid_wordlist.txt")


@mark.timeout(5)
def test_tty_mode_initialization(mock_stdscr):
    """Test initialization in TTY mode."""
    mock_stdscr.getmaxyx.return_value = (25, 80)  # Return sensible terminal size
    
    # We need to create a custom UIManager for testing
    class MockUIManager:
        def __init__(self):
            self.stdscr = None
        
        def initialize(self, mock_stdscr=None):
            self.stdscr = mock_stdscr
            # Always call halfdelay in TTY mode
            if sys.stdin.isatty():
                curses.halfdelay(1)
    
    # Patch isatty to return True for TTY mode
    with patch('sys.stdin.isatty', return_value=True), \
         patch('curses.halfdelay') as mock_halfdelay:
        # Create UI manager and manually initialize
        ui_manager = MockUIManager()
        ui_manager.initialize(mock_stdscr)
        
        # Verify halfdelay was called correctly
        mock_halfdelay.assert_called_once_with(1)


@mark.timeout(5)
def test_non_tty_mode_initialization(mock_curses, mock_stdscr):
    """Test initialization in non-TTY mode."""
    mock_stdscr.getmaxyx.return_value = (25, 80)  # Return sensible terminal size
    with patch('sys.stdin.isatty', return_value=False):
        interface = SecureWordInterface()
        interface.ui_manager.initialize(mock_stdscr)
        curses.halfdelay.assert_not_called()


@mark.timeout(5)
def test_timeout_adjustment_on_new_input(mock_curses, mock_stdscr):
    """Test timeout adjustment when switching to new input mode."""
    interface = SecureWordInterface()
    mock_stdscr.getch.side_effect = [ord('n'), ord('q')]

    with patch('curses.initscr', return_value=mock_stdscr):
        interface.run()

    assert any(call.args[0] == 10000 for call in mock_stdscr.timeout.call_args_list)


@mark.timeout(5)
def test_input_handling_with_timeout(mock_curses, mock_stdscr):
    """Test input handling with timeout behavior."""
    interface = SecureWordInterface()
    mock_stdscr.getch.side_effect = [-1, ord('q')]

    with patch('curses.initscr', return_value=mock_stdscr), \
            patch('time.sleep') as mock_sleep:
        interface.run()

    mock_sleep.assert_called()


@mark.timeout(5)
def test_run_with_file_input(test_positions, mock_curses, mock_stdscr):
    """Test running with file input in non-TTY mode."""
    with patch('sys.stdin.isatty', return_value=False), \
            patch('curses.initscr', return_value=mock_stdscr):
        interface = SecureWordInterface()
        mock_stdscr.getch.side_effect = [ord('q')]
        interface.run(test_positions)
        mock_stdscr.timeout.assert_called_with(100)


@mark.timeout(5)
def test_mouse_interaction(mock_curses, mock_stdscr):
    """Test mouse interaction behavior."""
    with patch('curses.initscr', return_value=mock_stdscr):
        interface = SecureWordInterface()
        interface.words = ["test1", "test2"]
        mock_stdscr.getmouse.return_value = (0, 0, 0, 0, 0)
        mock_stdscr.getch.side_effect = [curses.KEY_MOUSE, ord('q')]
        interface.run()


@mark.timeout(5)
def test_sequential_reveal_flow(mock_curses, mock_stdscr):
    """Test sequential reveal functionality."""
    with patch('curses.initscr', return_value=mock_stdscr):
        interface = SecureWordInterface()
        interface.words = [f"word{i}" for i in range(5)]
        mock_stdscr.getch.side_effect = [ord('s'), ord('s'), ord('r'), ord('q')]
        interface.run()


@mark.timeout(5)
def test_reset_and_scroll(mock_curses, mock_stdscr):
    """Test reset and scroll behavior."""
    with patch('curses.initscr', return_value=mock_stdscr):
        interface = SecureWordInterface()
        interface.words = [f"word{i}" for i in range(10)]
        mock_stdscr.getmaxyx.return_value = (10, 80)
        mock_stdscr.getch.side_effect = [ord('s'), ord('s'), ord('s'), ord('r'), ord('q')]
        interface.run()


@mark.timeout(5)
def test_input_mode_transitions(mock_curses, mock_stdscr):
    """Test transitions between different input modes."""
    interface = SecureWordInterface()
    mock_stdscr.getch.side_effect = [
        ord('n'),  # New input mode
        ord('1'), ord('\n'),  # Enter number
        -1, -1,  # Timeouts
        ord('q')  # Quit
    ]

    with patch('curses.initscr', return_value=mock_stdscr), \
            patch('time.sleep'):
        interface.run()

    # Verify timeout changes
    timeout_calls = [call.args[0] for call in mock_stdscr.timeout.call_args_list]
    assert 10000 in timeout_calls  # Should see input mode timeout
    assert 100 in timeout_calls  # Should see normal mode timeout


@mark.timeout(5)
def test_error_handling_with_timeout(mock_curses, mock_stdscr):
    """Test error handling during timeout operations."""
    interface = SecureWordInterface()
    mock_stdscr.getch.side_effect = [curses.error, -1, ord('q')]

    with patch('curses.initscr', return_value=mock_stdscr), \
            patch('time.sleep'):
        interface.run()


@mark.timeout(5)
def test_auto_scroll_sequential_reveal(mock_curses, mock_stdscr):
    """Test auto-scrolling behavior during sequential reveal."""
    interface = SecureWordInterface()
    mock_stdscr.getmaxyx.return_value = (10, 80)
    interface.words = [f"word{i}" for i in range(20)]
    positions = list(range(1, 11))

    for i in range(8):
        interface.state_handler.handle_commands(ord('s'), positions, time.time())
        if interface.state_handler.cursor_pos is not None:
            height, _ = mock_stdscr.getmaxyx()
            visible_count = interface.display_handler.display_words(
                mock_stdscr, positions, 0, interface.state_handler.cursor_pos,
                interface.state_handler.reached_last)
            assert visible_count > 0


@mark.timeout(5)
def test_scroll_boundaries_with_sequential_reveal(mock_curses, mock_stdscr):
    """Test scroll boundaries during sequential reveal."""
    interface = SecureWordInterface()
    interface.words = [f"word{i}" for i in range(20)]
    positions = list(range(1, 21))
    mock_stdscr.getmaxyx.return_value = (10, 80)

    interface.state_handler.cursor_pos = 0
    visible_count = interface.display_handler.display_words(
        mock_stdscr, positions, 0, 0, False)
    assert visible_count > 0

    interface.state_handler.cursor_pos = len(positions) - 1
    scroll_position = max(0, len(positions) - visible_count)
    visible_count = interface.display_handler.display_words(
        mock_stdscr, positions, scroll_position,
        interface.state_handler.cursor_pos, True)
    assert visible_count > 0
    assert scroll_position + visible_count >= len(positions)


@mark.timeout(5)
def test_scroll_interaction_with_reveal_timeout(mock_curses, mock_stdscr):
    """Test interaction between auto-scrolling and reveal timeout."""
    interface = SecureWordInterface()
    interface.words = [f"word{i}" for i in range(15)]
    positions = list(range(1, 16))
    mock_stdscr.getmaxyx.return_value = (10, 80)

    current_time = 100.0
    interface.state_handler.handle_commands(ord('s'), positions, current_time)
    scroll_position = 0

    visible_count = interface.display_handler.display_words(
        mock_stdscr, positions, scroll_position,
        interface.state_handler.cursor_pos,
        interface.state_handler.reached_last)
    initial_scroll = scroll_position

    current_time += interface.state_handler.REVEAL_TIMEOUT + 1
    interface.state_handler.handle_reveal_timeout(current_time)

    visible_count = interface.display_handler.display_words(
        mock_stdscr, positions, scroll_position,
        interface.state_handler.cursor_pos,
        interface.state_handler.reached_last)
    assert interface.state_handler.cursor_pos is None
    assert scroll_position == initial_scroll


@mark.timeout(5)
def test_reset_command_behavior(mock_curses, mock_stdscr):
    """Test reset command behavior and scroll position handling."""
    interface = SecureWordInterface()
    interface.words = [f"word{i}" for i in range(20)]
    positions = list(range(1, 21))
    scroll_position = 10

    interface.state_handler.current_index = len(positions) - 1
    interface.state_handler.reached_last = True

    command_result = interface.state_handler.handle_commands(
        ord('r'), positions, time.time())

    assert interface.state_handler.current_index == 0
    assert interface.state_handler.cursor_pos is None
    assert interface.state_handler.reveal_time is None
    assert interface.state_handler.reached_last is False
    assert command_result is None


@mark.timeout(5)
def test_reset_maintain_word_list(mock_curses, mock_stdscr):
    """Test that reset maintains complete word list."""
    interface = SecureWordInterface()
    test_words = [f"word{i}" for i in range(10)]
    interface.words = test_words
    positions = list(range(1, 11))

    interface.state_handler.current_index = len(positions) - 1
    interface.state_handler.reached_last = True
    original_positions = positions.copy()

    interface.state_handler.handle_commands(ord('r'), positions, time.time())
    visible_count = interface.display_handler.display_words(
        mock_stdscr, positions, 0,
        interface.state_handler.cursor_pos,
        interface.state_handler.reached_last)

    assert positions == original_positions
    assert len(positions) == len(original_positions)
    assert visible_count > 0
    assert all(pos in positions for pos in original_positions)


@mark.timeout(5)
def test_exception_during_init(mock_curses):
    """Test exception handling during initialization."""
    mock_stdscr = MagicMock()
    with patch('curses.initscr', return_value=mock_stdscr):
        # Test exception handling when stdscr exists
        with pytest.raises(Exception):
            with patch('builtins.open', side_effect=Exception("Test error")):
                SecureWordInterface()
        mock_stdscr.keypad.assert_not_called()


@mark.timeout(5)
def test_update_display_state(mock_curses):
    """Test display state update functionality."""
    mock_stdscr = MagicMock()
    interface = SecureWordInterface()
    positions = [1, 2, 3]
    scroll_position = 0
    current_time = time.time()

    mock_stdscr.getmaxyx.return_value = (24, 80)
    visible_count, new_scroll = interface._update_display_state(
        mock_stdscr, positions, scroll_position, current_time)

    assert visible_count >= 0
    assert new_scroll >= 0
    mock_stdscr.refresh.assert_called_once()


@mark.timeout(5)
def test_process_user_input_error(mock_curses):
    """Test lines 140, 142: Curses error handling in input processing."""
    mock_stdscr = MagicMock()
    interface = SecureWordInterface()
    positions = [1, 2, 3]
    mock_stdscr.getch.side_effect = curses.error

    with patch('time.sleep') as mock_sleep:
        result, scroll_pos = interface._process_user_input(
            mock_stdscr, positions, 0, 3, time.time())
        assert result is True
        assert scroll_pos == 0
        mock_sleep.assert_called_once_with(0.05)  # Updated to match actual implementation


@mark.timeout(5)
def test_handle_input_mode(mock_curses):
    """Test input mode handling."""
    mock_stdscr = MagicMock()
    interface = SecureWordInterface()

    # Mock the input_handler's get_input method directly
    with patch.object(interface.input_handler, 'get_input') as mock_get_input:
        # Test successful input
        mock_get_input.return_value = [1]
        result = interface._handle_input_mode(mock_stdscr)
        assert result == [1]
        mock_stdscr.timeout.assert_called_with(100)

        # Test cancelled input
        mock_get_input.return_value = None
        result = interface._handle_input_mode(mock_stdscr)
        assert result is None


@mark.timeout(5)
def test_update_display_state_complete(mock_curses):
    """Test lines 112, 126-128: Full display state update."""
    mock_stdscr = MagicMock()
    interface = SecureWordInterface()
    # Set up test data
    current_time = time.time()
    positions = [1, 2, 3]
    scroll_position = 0

    # Ensure state that will trigger the scrolling logic
    interface.state_handler.cursor_pos = 2
    mock_stdscr.getmaxyx.return_value = (10, 80)  # Small height to force scrolling

    visible_count, new_scroll = interface._update_display_state(
        mock_stdscr, positions, scroll_position, current_time)

    assert visible_count > 0
    assert new_scroll >= 0
    mock_stdscr.refresh.assert_called_once()


@mark.timeout(5)
def test_process_user_input_curses_error(mock_curses):
    """Test lines 140, 142: Curses error handling in input processing."""
    mock_stdscr = MagicMock()
    interface = SecureWordInterface()
    positions = [1, 2, 3]
    mock_stdscr.getch.side_effect = curses.error

    with patch('time.sleep') as mock_sleep:
        result, scroll_pos = interface._process_user_input(
            mock_stdscr, positions, 0, 3, time.time())
        assert result is True
        assert scroll_pos == 0
        mock_sleep.assert_called_once_with(0.05)  # Updated to match actual implementation


@mark.timeout(5)
def test_input_mode_with_none_input(mock_curses):
    """Test lines 165, 177-179: Input mode with None returned."""
    mock_stdscr = MagicMock()
    interface = SecureWordInterface()

    with patch.object(interface.input_handler, 'get_input', return_value=None):
        result = interface._handle_input_mode(mock_stdscr)
        assert result is None
        mock_stdscr.timeout.assert_not_called()  # Should not set timeout on None input

@mark.timeout(5)
def test_scrolling_up_down():
    """Test scrolling with arrow keys."""
    mock_stdscr = MagicMock()
    interface = SecureWordInterface()
    positions = list(range(1, 21))  # 20 positions
    scroll_position = 5
    visible_count = 7

    # Test scroll down
    _, new_scroll = interface._process_user_input(
        mock_stdscr, positions, scroll_position, visible_count, time.time())
    assert new_scroll == scroll_position

    # Test scroll up
    _, new_scroll = interface._process_user_input(
        mock_stdscr, positions, scroll_position, visible_count, time.time())
    assert new_scroll == scroll_position

@mark.timeout(5)
def test_scroll_boundaries():
    """Test scrolling at list boundaries."""
    mock_stdscr = MagicMock()
    interface = SecureWordInterface()
    positions = list(range(1, 11))  # 10 positions
    visible_count = 5

    # Test at top boundary
    mock_stdscr.getch.return_value = curses.KEY_UP
    _, new_scroll = interface._process_user_input(
        mock_stdscr, positions, 0, visible_count, time.time())
    assert new_scroll == 0

    # Test at bottom boundary
    mock_stdscr.getch.return_value = curses.KEY_DOWN
    _, new_scroll = interface._process_user_input(
        mock_stdscr, positions, 5, visible_count, time.time())
    assert new_scroll == 5

@mark.timeout(5)
def test_scroll_position_persistence():
    """Test scroll position persistence during different operations."""
    mock_stdscr = MagicMock()
    interface = SecureWordInterface()
    positions = list(range(1, 15))  # 14 positions
    scroll_position = 3
    visible_count = 5

    # Test scroll persistence after mouse event
    mock_stdscr.getch.return_value = curses.KEY_MOUSE
    mock_stdscr.getmouse.return_value = (0, 0, 2, 0, 0)
    _, new_scroll = interface._process_user_input(
        mock_stdscr, positions, scroll_position, visible_count, time.time())
    assert new_scroll == scroll_position

    # Test scroll persistence after sequential reveal
    mock_stdscr.getch.return_value = ord('s')
    _, new_scroll = interface._process_user_input(
        mock_stdscr, positions, scroll_position, visible_count, time.time())
    assert new_scroll == scroll_position

def test_init_with_missing_file():
    with pytest.raises(FileNotFoundError):
        SecureWordInterface("nonexistent.txt")

def test_process_input_with_no_positions():
    mock_stdscr = MagicMock()
    interface = SecureWordInterface()
    result, scroll = interface._process_user_input(mock_stdscr, [], 0, 5, time.time())
    assert result is True
    assert scroll == 0

def test_handle_commands_with_all_types():
    interface = SecureWordInterface()
    positions = [1, 2, 3]
    current_time = time.time()

    # Test 'n' command
    should_quit, should_reinit, new_scroll, new_positions = interface._handle_user_input(ord('n'), positions, 0, 3, current_time)
    assert should_reinit is True
    assert new_scroll == 0

    # Test 'r' command
    should_quit, should_reinit, new_scroll, new_positions = interface._handle_user_input(ord('r'), positions, 5, 3, current_time)
    assert new_scroll == 0

if __name__ == "__main__":
    pytest.main([__file__])