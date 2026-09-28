import pyperclip
from unittest.mock import patch
from seedshield.input_handler import InputHandler


def test_input_handler_init():
    """Test InputHandler initialization."""
    handler = InputHandler(10)
    assert handler.word_count == 10


def test_validate_number_input_multiple():
    """Multiple positions separated by spaces and/or commas are accepted."""
    handler = InputHandler(10)
    assert handler.validate_number_input("5 7 9") == [5, 7, 9]
    assert handler.validate_number_input("5,7,9") == [5, 7, 9]
    assert handler.validate_number_input("5, 7  9") == [5, 7, 9]


def test_validate_number_input_multiple_rejects_any_invalid():
    """One bad value rejects the whole entry; nothing is partially accepted."""
    handler = InputHandler(10)
    assert handler.validate_number_input("5 invalid 9") is None
    assert handler.validate_number_input("5 11") is None
    assert handler.validate_number_input("0 5") is None


@patch("pyperclip.paste")
@patch("pyperclip.copy")
def test_process_clipboard_valid_input(mock_copy, mock_paste):
    """Clipboard positions may be separated by newlines, spaces or commas."""
    handler = InputHandler(10)
    mock_paste.return_value = "1\n3\n5"
    assert handler.process_clipboard_input() == ([1, 3, 5], None)
    mock_copy.assert_called_with("")


@patch("pyperclip.paste")
@patch("pyperclip.copy")
def test_process_clipboard_accepts_multi_position_line(mock_copy, mock_paste):
    """Regression: '5 12 19' on one line was rejected from the clipboard."""
    handler = InputHandler(20)
    mock_paste.return_value = "5 12 19"
    assert handler.process_clipboard_input() == ([5, 12, 19], None)

    mock_paste.return_value = "5,12,19"
    assert handler.process_clipboard_input() == ([5, 12, 19], None)


@patch("pyperclip.paste")
@patch("pyperclip.copy")
def test_process_clipboard_invalid_input_rejected_entirely(mock_copy, mock_paste):
    """Regression: invalid clipboard entries were silently dropped."""
    handler = InputHandler(10)
    mock_paste.return_value = "invalid\n3\ntext\n5"

    numbers, message = handler.process_clipboard_input()
    assert numbers is None
    assert message == "Clipboard must contain only positions 1-10"
    # Cleared even when the content is rejected
    mock_copy.assert_called_with("")


@patch("pyperclip.paste")
def test_process_clipboard_with_pyperclip_exception(mock_paste):
    """No copy/paste mechanism (e.g. Docker) is reported as unavailable."""
    handler = InputHandler(10)
    mock_paste.side_effect = pyperclip.PyperclipException("Clipboard access error")

    assert handler.process_clipboard_input() == (
        None,
        "Clipboard is not available on this system",
    )


@patch("pyperclip.paste")
def test_process_clipboard_with_general_exception(mock_paste):
    """Unexpected clipboard errors are reported as unavailable, never raised."""
    handler = InputHandler(10)
    mock_paste.side_effect = Exception("Unexpected error")

    numbers, _ = handler.process_clipboard_input()
    assert numbers is None


@patch("pyperclip.paste")
@patch("seedshield.input_handler.secure_clipboard_clear", return_value=False)
def test_read_clipboard_clear_failure_still_returns_content(mock_clear, mock_paste):
    """A failed clipboard clear is logged but does not lose the input."""
    mock_paste.return_value = "1 2"
    assert InputHandler.read_clipboard() == "1 2"
    assert mock_clear.called


def test_validate_number_input_rejects_non_ascii_digit_forms():
    """int() accepts '1_2', '+5' and non-ASCII digits; positions must not."""
    handler = InputHandler(20)
    for text in ("1_2", "+5", "\u0663", "\u00b2", "-1"):
        assert handler.validate_number_input(text) is None


def test_validate_number_input_newlines():
    """Newline-separated input (clipboard/file) is parsed like spaces."""
    handler = InputHandler(10)
    assert handler.validate_number_input("1\n2\r\n3\n\n") == [1, 2, 3]


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


@patch("os.access")
def test_load_positions_no_read_permission(mock_access, tmp_path):
    """Test handling when file exists but has no read permission."""
    handler = InputHandler(10)
    test_file = tmp_path / "no_read_perm.txt"
    test_file.touch()
    mock_access.return_value = False

    result = handler.load_positions_from_file(str(test_file))
    assert result is None


def test_load_positions_with_invalid_content(tmp_path):
    """Regression: a file with any invalid value is rejected, never partially used."""
    handler = InputHandler(10)
    test_file = tmp_path / "positions.txt"
    test_file.write_text("1\ntext\n3\n\n")

    assert handler.load_positions_from_file(str(test_file)) is None


def test_load_positions_with_out_of_range_numbers(tmp_path):
    """Out-of-range values reject the whole file."""
    handler = InputHandler(10)
    test_file = tmp_path / "positions.txt"
    test_file.write_text("1\n15\n3\n0\n")

    assert handler.load_positions_from_file(str(test_file)) is None


def test_load_positions_multi_position_lines(tmp_path):
    """Regression: '5 12 19' / '5,12,19' lines were skipped in -i files."""
    handler = InputHandler(20)
    test_file = tmp_path / "positions.txt"
    test_file.write_text("5 12 19\n1,2\n\n3\n")

    assert handler.load_positions_from_file(str(test_file)) == [5, 12, 19, 1, 2, 3]


def test_load_positions_unicode_digit(tmp_path):
    """Regression: '²' passed isdigit() but crashed int()."""
    handler = InputHandler(10)
    test_file = tmp_path / "positions.txt"
    test_file.write_text("1\n\u00b2\n", encoding="utf-8")

    assert handler.load_positions_from_file(str(test_file)) is None


def test_load_positions_empty_result(tmp_path):
    """A file without positions yields None."""
    handler = InputHandler(10)
    test_file = tmp_path / "empty_positions.txt"
    test_file.write_text("\n\n")

    assert handler.load_positions_from_file(str(test_file)) is None


def test_load_positions_too_large(tmp_path):
    """Oversized files are rejected without being parsed."""
    handler = InputHandler(10)
    test_file = tmp_path / "big.txt"
    test_file.write_text("1 " * 40000)

    assert handler.load_positions_from_file(str(test_file)) is None


def test_load_positions_not_utf8(tmp_path):
    """Undecodable files are rejected."""
    handler = InputHandler(10)
    test_file = tmp_path / "bin.txt"
    test_file.write_bytes(b"\xff\xfe\x00")

    assert handler.load_positions_from_file(str(test_file)) is None


@patch("builtins.open")
def test_load_positions_io_error(mock_open, tmp_path):
    """Test handling of IOError when reading positions file."""
    handler = InputHandler(10)
    test_file = tmp_path / "positions.txt"
    test_file.touch()
    mock_open.side_effect = IOError("Failed to read file")

    result = handler.load_positions_from_file(str(test_file))
    assert result is None


@patch("curses.echo")
@patch("curses.noecho")
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


@patch("pyperclip.paste")
@patch("curses.echo")
@patch("curses.noecho")
def test_empty_clipboard_input(mock_noecho, mock_echo, mock_paste, mock_stdscr):
    """Test empty clipboard handling."""
    handler = InputHandler(10)
    mock_paste.return_value = ""
    mock_stdscr.getstr.side_effect = [b"v", b"q"]

    result = handler.get_input(mock_stdscr)
    assert result is None
    assert mock_echo.call_count >= 1
    assert mock_noecho.call_count >= 1


@patch("curses.echo")
@patch("curses.noecho")
@patch("seedshield.input_handler.InputHandler.process_clipboard_input")
def test_get_input_clipboard_numbers(mock_process_clipboard, mock_noecho, mock_echo, mock_stdscr):
    """Test successful clipboard number return from get_input."""
    handler = InputHandler(10)
    mock_stdscr.getstr.return_value = b"v"
    mock_process_clipboard.return_value = ([1, 3, 5], None)

    result = handler.get_input(mock_stdscr)
    assert result == [1, 3, 5]
    mock_process_clipboard.assert_called_once_with()


@patch("curses.echo")
@patch("curses.noecho")
def test_get_input_unicode_decode_error(mock_noecho, mock_echo, mock_stdscr):
    """Test handling of UnicodeDecodeError in get_input."""
    handler = InputHandler(10)
    mock_stdscr.getstr.side_effect = [
        UnicodeDecodeError("utf-8", b"\x80", 0, 1, "invalid start byte"),
        b"q",
    ]

    result = handler.get_input(mock_stdscr)
    mock_stdscr.addstr.assert_any_call(6, 0, "Invalid character input")
    assert result is None


@patch("curses.echo")
@patch("curses.noecho")
def test_get_input_value_error(mock_noecho, mock_echo, mock_stdscr):
    """Test handling of ValueError in get_input."""
    handler = InputHandler(10)
    # Set up get_input to first cause ValueError, then return 'q' to exit the loop
    mock_stdscr.getstr.side_effect = [ValueError("Invalid conversion"), b"q"]

    result = handler.get_input(mock_stdscr)
    mock_stdscr.addstr.assert_any_call(6, 0, "Invalid input format")
    assert result is None


@patch("curses.echo")
@patch("curses.noecho")
def test_get_input_general_exception(mock_noecho, mock_echo, mock_stdscr):
    """Test handling of general exceptions in get_input."""
    handler = InputHandler(10)
    # Set up get_input to first cause Exception, then return 'q' to exit the loop
    mock_stdscr.getstr.side_effect = [Exception("Unexpected error"), b"q"]

    result = handler.get_input(mock_stdscr)
    mock_stdscr.addstr.assert_any_call(6, 0, "Error processing input")
    assert result is None


@patch("curses.echo")
@patch("curses.noecho")
def test_get_input_multiple_numbers(mock_noecho, mock_echo, mock_stdscr):
    """Typing several positions at once returns them all."""
    handler = InputHandler(10)
    mock_stdscr.getstr.return_value = b"3 6 9"

    result = handler.get_input(mock_stdscr)
    assert result == [3, 6, 9]


@patch("curses.echo")
@patch("curses.noecho")
def test_get_input_blocks_while_typing(mock_noecho, mock_echo, mock_stdscr):
    """Input mode must use blocking reads so slow typing is never aborted."""
    handler = InputHandler(10)
    mock_stdscr.getstr.return_value = b"q"

    handler.get_input(mock_stdscr)
    mock_stdscr.timeout.assert_called_once_with(-1)


@patch("curses.echo")
@patch("curses.noecho")
def test_get_input_shows_feedback_on_next_prompt(mock_noecho, mock_echo, mock_stdscr):
    """Invalid input feedback persists on the redrawn prompt (no UI freeze)."""
    handler = InputHandler(10)
    mock_stdscr.getstr.side_effect = [b"99", b"q"]

    result = handler.get_input(mock_stdscr)
    assert result is None
    mock_stdscr.addstr.assert_any_call(6, 0, "Invalid input. Enter numbers between 1-10")


@patch("pyperclip.paste", side_effect=pyperclip.PyperclipException("no clipboard"))
@patch("curses.echo")
@patch("curses.noecho")
def test_get_input_clipboard_unavailable_message(mock_noecho, mock_echo, mock_paste, mock_stdscr):
    """The prompt says the clipboard is unavailable instead of 'no numbers'."""
    handler = InputHandler(10)
    mock_stdscr.getstr.side_effect = [b"v", b"q"]

    assert handler.get_input(mock_stdscr) is None
    mock_stdscr.addstr.assert_any_call(6, 0, "Clipboard is not available on this system")


@patch("curses.echo")
@patch("curses.noecho")
def test_get_input_wipes_typed_positions(mock_noecho, mock_echo, mock_stdscr):
    """Typed positions are wiped (best effort) after they are parsed."""
    handler = InputHandler(20)
    mock_stdscr.getstr.return_value = b"5 12"

    with patch("seedshield.input_handler.secure_clear_string") as mock_clear:
        assert handler.get_input(mock_stdscr) == [5, 12]
    mock_clear.assert_called_once_with("5 12")
