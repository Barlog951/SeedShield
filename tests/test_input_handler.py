import pytest
from unittest.mock import patch, MagicMock
from seedshield.input_handler import InputHandler
from tests.test_fixtures import mock_stdscr, test_wordlist, test_positions


def test_input_handler_init():
    """Test InputHandler initialization."""
    handler = InputHandler(10)
    assert handler.word_count == 10


@patch('pyperclip.copy')
def test_clear_clipboard(mock_copy):
    """Test clipboard clearing."""
    handler = InputHandler(10)
    handler._clear_clipboard()
    mock_copy.assert_called_once_with('')


@patch('pyperclip.paste')
@patch('pyperclip.copy')
def test_process_clipboard_valid_input(mock_copy, mock_paste, mock_stdscr):
    """Test processing valid clipboard input."""
    handler = InputHandler(10)
    mock_paste.return_value = "1\n3\n5"

    result = handler.process_clipboard_input(mock_stdscr)
    assert result == [1, 3, 5]
    mock_copy.assert_called_with('')


@patch('pyperclip.paste')
@patch('pyperclip.copy')
def test_process_clipboard_invalid_input(mock_copy, mock_paste, mock_stdscr):
    """Test processing invalid clipboard input."""
    handler = InputHandler(10)
    mock_paste.return_value = "invalid\n3\ntext\n5"

    result = handler.process_clipboard_input(mock_stdscr)
    assert result == [3, 5]
    mock_copy.assert_called_with('')


def test_validate_number_input():
    """Test number input validation."""
    handler = InputHandler(10)
    assert handler.validate_number_input("5") == [5]
    assert handler.validate_number_input("11") is None
    assert handler.validate_number_input("invalid") is None


@patch('curses.echo')
@patch('curses.noecho')
def test_get_input(mock_noecho, mock_echo, mock_stdscr):
    """Test input handling."""
    handler = InputHandler(10)

    # Test valid number input
    mock_stdscr.getstr.return_value = b"5"
    result = handler.get_input(mock_stdscr)
    assert result == [5]

    # Test quit command
    mock_stdscr.getstr.return_value = b"q"
    result = handler.get_input(mock_stdscr)
    assert result is None


@patch('pyperclip.paste')
@patch('curses.echo')
@patch('curses.noecho')
def test_empty_clipboard_input(mock_noecho, mock_echo, mock_paste, mock_stdscr):
    """Test empty clipboard handling."""
    handler = InputHandler(10)
    mock_paste.return_value = ""
    mock_stdscr.getstr.side_effect = [b"v", b"q"]

    result = handler.get_input(mock_stdscr)
    assert result is None
    assert mock_echo.call_count >= 1
    assert mock_noecho.call_count >= 1