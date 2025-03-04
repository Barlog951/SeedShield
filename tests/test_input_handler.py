import os
import pytest
import pyperclip
from unittest.mock import patch, MagicMock
from seedshield.input_handler import InputHandler


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


@patch('pyperclip.paste')
@patch('seedshield.secure_memory.secure_clipboard_clear')
def test_process_clipboard_with_pyperclip_exception(mock_clear, mock_paste, mock_stdscr):
    """Test error handling when pyperclip raises an exception."""
    handler = InputHandler(10)
    mock_paste.side_effect = pyperclip.PyperclipException("Clipboard access error")
    mock_clear.return_value = True
    
    result = handler.process_clipboard_input(mock_stdscr)
    assert result is None
    mock_stdscr.addstr.assert_called_with(6, 0, "Error processing clipboard data")


@patch('pyperclip.paste')
@patch('seedshield.secure_memory.secure_clipboard_clear')
def test_process_clipboard_with_general_exception(mock_clear, mock_paste, mock_stdscr):
    """Test error handling when an unexpected exception occurs."""
    handler = InputHandler(10)
    mock_paste.side_effect = Exception("Unexpected error")
    mock_clear.return_value = True
    
    result = handler.process_clipboard_input(mock_stdscr)
    assert result is None
    mock_stdscr.addstr.assert_called_with(6, 0, "Unexpected error with clipboard")


def test_validate_number_input():
    """Test number input validation."""
    handler = InputHandler(10)
    assert handler.validate_number_input("5") == [5]
    assert handler.validate_number_input("11") is None
    assert handler.validate_number_input("invalid") is None


def test_load_positions_file_not_found(tmp_path):
    """Test handling when file path doesn't exist."""
    handler = InputHandler(10)
    non_existent_file = tmp_path / "nonexistent.txt"
    
    result = handler.load_positions_from_file(str(non_existent_file))
    assert result is None


def test_load_positions_not_a_file(tmp_path):
    """Test handling when path exists but is not a file."""
    handler = InputHandler(10)
    directory_path = tmp_path / "directory"
    directory_path.mkdir()
    
    result = handler.load_positions_from_file(str(directory_path))
    assert result is None


@patch('os.access')
def test_load_positions_no_read_permission(mock_access, tmp_path):
    """Test handling when file exists but has no read permission."""
    handler = InputHandler(10)
    test_file = tmp_path / "no_read_perm.txt"
    test_file.touch()
    mock_access.return_value = False
    
    result = handler.load_positions_from_file(str(test_file))
    assert result is None


def test_load_positions_with_invalid_content(tmp_path):
    """Test handling of invalid content in the positions file."""
    handler = InputHandler(10)
    test_file = tmp_path / "positions.txt"
    
    with open(test_file, 'w') as f:
        f.write("1\ntext\n3\n\n")
    
    result = handler.load_positions_from_file(str(test_file))
    assert result == [1, 3]  # Only valid numbers get returned


def test_load_positions_with_out_of_range_numbers(tmp_path):
    """Test handling of out-of-range numbers in the positions file."""
    handler = InputHandler(10)
    test_file = tmp_path / "positions.txt"
    
    with open(test_file, 'w') as f:
        f.write("1\n15\n3\n0\n")
    
    result = handler.load_positions_from_file(str(test_file))
    assert result == [1, 3]  # Only in-range numbers are returned


def test_load_positions_empty_result(tmp_path):
    """Test handling when no valid positions are found in file."""
    handler = InputHandler(10)
    test_file = tmp_path / "empty_positions.txt"
    
    with open(test_file, 'w') as f:
        f.write("text\n15\n0\n")  # All invalid
    
    result = handler.load_positions_from_file(str(test_file))
    assert result == []


@patch('builtins.open')
def test_load_positions_io_error(mock_open, tmp_path):
    """Test handling of IOError when reading positions file."""
    handler = InputHandler(10)
    test_file = tmp_path / "positions.txt"
    test_file.touch()
    mock_open.side_effect = IOError("Failed to read file")
    
    result = handler.load_positions_from_file(str(test_file))
    assert result is None


@patch('seedshield.input_handler.os.path.exists')
@patch('seedshield.input_handler.os.path.isfile')
@patch('seedshield.input_handler.os.access')
@patch('builtins.open')
def test_load_positions_unexpected_error(mock_open, mock_access, mock_isfile, mock_exists):
    """Test handling of unexpected exceptions when reading positions file."""
    handler = InputHandler(10)
    
    mock_exists.return_value = True
    mock_isfile.return_value = True
    mock_access.return_value = True
    mock_open.side_effect = Exception("Unexpected error")
    
    result = handler.load_positions_from_file("test_file.txt")
    assert result is None


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


@patch('curses.echo')
@patch('curses.noecho')
@patch('seedshield.input_handler.InputHandler.process_clipboard_input')
def test_get_input_clipboard_numbers(mock_process_clipboard, mock_noecho, mock_echo, mock_stdscr):
    """Test successful clipboard number return from get_input."""
    handler = InputHandler(10)
    mock_stdscr.getstr.return_value = b"v"
    mock_process_clipboard.return_value = [1, 3, 5]
    
    result = handler.get_input(mock_stdscr)
    assert result == [1, 3, 5]
    mock_process_clipboard.assert_called_once_with(mock_stdscr)


@patch('curses.echo')
@patch('curses.noecho')
def test_get_input_unicode_decode_error(mock_noecho, mock_echo, mock_stdscr):
    """Test handling of UnicodeDecodeError in get_input."""
    handler = InputHandler(10)
    mock_stdscr.getstr.side_effect = [UnicodeDecodeError('utf-8', b'\x80', 0, 1, 'invalid start byte'), b"q"]
    
    result = handler.get_input(mock_stdscr)
    mock_stdscr.addstr.assert_any_call(6, 0, "Invalid character input")
    assert result is None


@patch('curses.echo')
@patch('curses.noecho')
def test_get_input_value_error(mock_noecho, mock_echo, mock_stdscr):
    """Test handling of ValueError in get_input."""
    handler = InputHandler(10)
    # Set up get_input to first cause ValueError, then return 'q' to exit the loop
    mock_stdscr.getstr.side_effect = [ValueError("Invalid conversion"), b"q"]
    
    result = handler.get_input(mock_stdscr)
    mock_stdscr.addstr.assert_any_call(6, 0, "Invalid input format")
    assert result is None


@patch('curses.echo')
@patch('curses.noecho')
def test_get_input_general_exception(mock_noecho, mock_echo, mock_stdscr):
    """Test handling of general exceptions in get_input."""
    handler = InputHandler(10)
    # Set up get_input to first cause Exception, then return 'q' to exit the loop
    mock_stdscr.getstr.side_effect = [Exception("Unexpected error"), b"q"]
    
    result = handler.get_input(mock_stdscr)
    mock_stdscr.addstr.assert_any_call(6, 0, "Error processing input")
    assert result is None