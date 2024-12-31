import curses
import time
import pytest
from unittest.mock import patch
from seedshield.state_handler import StateHandler
from tests.test_fixtures import mock_stdscr


def test_state_handler_init():
    handler = StateHandler()
    assert handler.cursor_pos is None
    assert handler.reveal_time is None
    assert handler.current_index == 0
    assert handler.reached_last is False


def test_reset_positions():
    handler = StateHandler()
    handler.cursor_pos = 1
    handler.reveal_time = 100
    handler.current_index = 5
    handler.reached_last = True

    handler.reset_positions()

    assert handler.cursor_pos is None
    assert handler.reveal_time is None
    assert handler.current_index == 0
    assert handler.reached_last is False


def test_handle_reveal_timeout():
    handler = StateHandler()
    handler.cursor_pos = 1
    handler.reveal_time = 100.0

    # Test before timeout
    handler.handle_reveal_timeout(101.0)
    assert handler.cursor_pos == 1

    # Test after timeout
    handler.handle_reveal_timeout(104.0)
    assert handler.cursor_pos is None
    assert handler.reveal_time is None


def test_handle_navigation():
    handler = StateHandler()
    positions = list(range(1, 11))

    # Test scroll up
    result = handler.handle_navigation(curses.KEY_UP, positions, 5, 3)
    assert result == 4

    # Test scroll down
    result = handler.handle_navigation(curses.KEY_DOWN, positions, 5, 3)
    assert result == 6


def test_handle_commands():
    handler = StateHandler()
    positions = list(range(1, 5))
    current_time = time.time()

    # Test new input
    result = handler.handle_commands(ord('n'), positions, current_time)
    assert result == []
    assert handler.current_index == 0

    # Test sequential reveal
    handler.handle_commands(ord('s'), positions, current_time)
    assert handler.cursor_pos == 0
    assert handler.reveal_time is not None

    # Test reset
    handler.reached_last = True
    handler.handle_commands(ord('r'), positions, current_time)
    assert handler.current_index == 0
    assert handler.reached_last is False


def test_handle_mouse_reveal():
    handler = StateHandler()
    current_time = time.time()

    handler.handle_mouse_reveal(2, current_time)
    assert handler.cursor_pos == 2
    assert handler.reveal_time == current_time


def test_sequential_reveal():
    handler = StateHandler()
    positions = list(range(1, 4))
    current_time = time.time()

    # First reveal
    handler.handle_commands(ord('s'), positions, current_time)
    assert handler.cursor_pos == 0
    assert not handler.reached_last

    # Last reveal
    handler.current_index = len(positions) - 1
    handler.handle_commands(ord('s'), positions, current_time)
    assert handler.reached_last


def test_get_display_state():
    handler = StateHandler()
    handler.cursor_pos = 1
    handler.reached_last = True

    cursor_pos, reached_last = handler.get_display_state()
    assert cursor_pos == 1
    assert reached_last is True


def test_state_handler_handle_commands_reset():
    handler = StateHandler()
    positions = [1, 2, 3]
    current_time = time.time()

    # Test reset without reaching last
    handler.reached_last = False
    result = handler.handle_commands(ord('r'), positions, current_time)
    assert result is None

    # Test reset after reaching last
    handler.reached_last = True
    handler.handle_commands(ord('r'), positions, current_time)
    assert handler.current_index == 0


def test_state_handler_navigation_boundary():
    handler = StateHandler()
    positions = [1, 2]

    # Test navigation at end of list
    scroll = handler.handle_navigation(curses.KEY_DOWN, positions, 1, 1)
    assert scroll == 1