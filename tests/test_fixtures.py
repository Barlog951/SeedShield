import pytest
from unittest.mock import MagicMock, patch
import os
import tempfile
import curses

@pytest.fixture
def mock_curses():
    with patch('curses.initscr'), \
         patch('curses.endwin'), \
         patch('curses.start_color'), \
         patch('curses.mousemask'), \
         patch('curses.noecho'), \
         patch('curses.echo'), \
         patch('curses.cbreak'), \
         patch('curses.nocbreak'), \
         patch('curses.halfdelay'):
        yield

@pytest.fixture
def mock_stdscr():
    stdscr = MagicMock()
    stdscr.getmaxyx.return_value = (24, 80)
    return stdscr

@pytest.fixture
def test_wordlist():
    words = ["apple", "banana", "cherry", "date"]
    with tempfile.NamedTemporaryFile(mode='w', delete=False) as f:
        for word in words:
            f.write(f"{word}\n")
    yield f.name
    os.unlink(f.name)

@pytest.fixture
def test_positions():
    positions = [1, 3]
    with tempfile.NamedTemporaryFile(mode='w', delete=False) as f:
        for pos in positions:
            f.write(f"{pos}\n")
    yield f.name
    os.unlink(f.name)