"""
Test fixtures for SeedShield tests.

This module provides test fixtures that can be used by pytest tests.
"""

import os
import sys
import pytest
import tempfile
from unittest.mock import MagicMock, patch
import curses

# Add a fixture to mock curses for tests
@pytest.fixture
def mock_curses():
    """Mock the curses module for testing."""
    mock = MagicMock()
    mock.KEY_UP = 259
    mock.KEY_DOWN = 258
    mock.KEY_MOUSE = 409
    mock.error = curses.error
    mock.halfdelay = MagicMock()
    mock.echo = MagicMock()
    mock.noecho = MagicMock()
    mock.endwin = MagicMock()
    mock.cbreak = MagicMock()
    mock.nocbreak = MagicMock()
    mock.A_REVERSE = 65536
    mock.mousemask = MagicMock()
    mock.ALL_MOUSE_EVENTS = 0xFFF
    mock.REPORT_MOUSE_POSITION = 0x1000
    mock.getmouse = MagicMock(return_value=(0, 10, 5, 0, 0))
    
    # Create these attributes for compatibility
    mock.COLORS = 8
    mock.COLOR_PAIRS = 64
    
    with patch('curses.initscr', return_value=mock), \
         patch('curses.start_color'), \
         patch('curses.init_pair'), \
         patch('curses.COLOR_WHITE', 0), \
         patch('curses.COLOR_BLACK', 0), \
         patch('curses.halfdelay', mock.halfdelay), \
         patch('curses.echo', mock.echo), \
         patch('curses.noecho', mock.noecho), \
         patch('curses.endwin', mock.endwin), \
         patch('curses.cbreak', mock.cbreak), \
         patch('curses.nocbreak', mock.nocbreak), \
         patch('curses.mousemask', mock.mousemask), \
         patch('curses.getmouse', mock.getmouse), \
         patch('curses.ALL_MOUSE_EVENTS', mock.ALL_MOUSE_EVENTS), \
         patch('curses.REPORT_MOUSE_POSITION', mock.REPORT_MOUSE_POSITION), \
         patch('curses.A_REVERSE', mock.A_REVERSE):
        yield mock

# Create a fixture for a mocked curses screen
@pytest.fixture
def mock_stdscr():
    mock = MagicMock()
    mock.getmaxyx.return_value = (24, 80)
    return mock

# Add global fixtures to prevent filesystem access and other issues

@pytest.fixture(autouse=True)
def mock_wordlist_validation():
    """Mock wordlist validation to prevent file system access during tests."""
    with patch('seedshield.main.validate_wordlist_path', 
              return_value='/Users/dodko/DEV/python/seedshield/seedshield/data/english.txt'):
        yield

@pytest.fixture(autouse=True)
def mock_setup_logging():
    """Mock logging setup to prevent log file access during tests."""
    with patch('seedshield.config.logger'):
        with patch('seedshield.main.logger'):
            yield

# Create a fixture for temporary test wordlist
@pytest.fixture
def test_wordlist():
    with tempfile.NamedTemporaryFile(mode='w', delete=False) as f:
        f.write("apple\nbanana\ncherry\norange\n")
        path = f.name
    
    yield path
    
    # Clean up
    os.unlink(path)

# Create a fixture for temporary test positions file
@pytest.fixture
def test_positions():
    with tempfile.NamedTemporaryFile(mode='w', delete=False) as f:
        f.write("1\n2\n3\n")
        path = f.name
    
    yield path
    
    # Clean up
    os.unlink(path)