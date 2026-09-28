from unittest.mock import patch, MagicMock
import pytest
from seedshield.main import main, validate_wordlist_path, parse_arguments
from seedshield.ui_manager import UIManager
from seedshield.config import DEFAULT_WORDLIST_FULLPATH

# Set test mode flag to enable test compatibility
main.__TEST_MODE__ = True


def test_main_with_default_arguments():
    """
    Test main() when no arguments are passed (default wordlist).

    Verifies:
    - SecureWordInterface is initialized with default wordlist
    - run() method is called correctly
    - No premature curses cleanup
    """
    with patch("seedshield.main.SecureWordInterface") as MockSecureInterface:
        mock_instance = MockSecureInterface.return_value  # Mock the instance returned
        with patch("sys.argv", ["main.py"]):
            with patch(
                "seedshield.main.validate_wordlist_path", return_value="seedshield/data/english.txt"
            ):
                with patch.object(UIManager, "cleanup") as mock_cleanup:
                    main()

    # Verify SecureWordInterface instantiated with the validated wordlist path
    MockSecureInterface.assert_called_once_with("seedshield/data/english.txt")

    # Verify the run method was called with no input
    mock_instance.run.assert_called_once_with(None)

    # Verify cleanup was not called prematurely
    mock_cleanup.assert_not_called()


def test_main_with_wordlist_argument():
    """
    Test main() when a custom wordlist is provided.

    Verifies:
    - SecureWordInterface is initialized with custom wordlist path
    - run() method is called with correct parameters
    """
    with patch("seedshield.main.SecureWordInterface") as MockSecureInterface:
        mock_instance = MockSecureInterface.return_value
        with patch("sys.argv", ["main.py", "--wordlist", "custom_wordlist.txt"]):
            # Mock validate_wordlist_path to return the custom wordlist path
            with patch(
                "seedshield.main.validate_wordlist_path", return_value="custom_wordlist.txt"
            ):
                with patch("os.path.exists", return_value=True):  # Mock file existence check
                    with patch("os.path.isfile", return_value=True):  # Mock file type check
                        with patch("os.access", return_value=True):  # Mock access permission check
                            with patch.object(UIManager, "cleanup"):
                                with patch("seedshield.ui_manager.UIManager"):
                                    main()

    # Verify SecureWordInterface instantiated with the validated custom wordlist path
    MockSecureInterface.assert_called_once_with("custom_wordlist.txt")
    # Verify run method was called with no input
    mock_instance.run.assert_called_once_with(None)


def test_main_with_input_file_argument():
    """
    Test main() when an input file is provided.

    Verifies:
    - SecureWordInterface is initialized correctly
    - run() method is called with proper input file path
    - Default wordlist is used with custom input file
    """
    with patch("seedshield.main.SecureWordInterface") as MockSecureInterface:
        mock_instance = MockSecureInterface.return_value
        with patch("sys.argv", ["main.py", "--input", "positions.txt"]):
            with patch(
                "seedshield.main.validate_wordlist_path", return_value="seedshield/data/english.txt"
            ):
                with patch("os.path.exists", side_effect=lambda x: x != "positions.txt" or True):
                    with patch.object(UIManager, "cleanup"):
                        with patch("seedshield.ui_manager.UIManager"):
                            main()

    # Verify SecureWordInterface instantiated with the validated wordlist path
    MockSecureInterface.assert_called_once_with("seedshield/data/english.txt")
    # Verify run method was called with the input file
    mock_instance.run.assert_called_once_with("positions.txt")


def test_main_generic_exception():
    """
    Test main() handles an unexpected exception gracefully.

    Verifies:
    - Error message is printed to stderr
    - Program exits with error code 1
    - Exception message is included in error output
    """
    with patch("seedshield.main.SecureWordInterface") as MockSecureInterface:
        mock_instance = MockSecureInterface.return_value
        mock_instance.run.side_effect = Exception("Unexpected error!")
        with patch("sys.argv", ["main.py"]):
            with patch(
                "seedshield.main.validate_wordlist_path", return_value="seedshield/data/english.txt"
            ):
                with patch("sys.stderr", new_callable=MagicMock()) as mock_stderr:
                    with patch("sys.exit") as mock_exit:
                        main()

    # Assert the error message components were written correctly
    mock_stderr.write.assert_any_call("Error: Unexpected error!")
    mock_stderr.write.assert_any_call("\n")

    # Verify the program exits with an error code
    mock_exit.assert_called_once_with(1)


def test_parse_arguments_default():
    """Test parse_arguments with default arguments."""
    with patch("sys.argv", ["main.py"]):
        args = parse_arguments()

        assert args.wordlist is None
        assert args.input is None
        assert not args.verbose


def test_parse_arguments_wordlist():
    """Test parse_arguments with custom wordlist."""
    with patch("sys.argv", ["main.py", "--wordlist", "custom_wordlist.txt"]):
        args = parse_arguments()

        assert args.wordlist == "custom_wordlist.txt"
        assert args.input is None
        assert not args.verbose


def test_parse_arguments_input():
    """Test parse_arguments with input file."""
    with patch("sys.argv", ["main.py", "--input", "positions.txt"]):
        args = parse_arguments()

        assert args.wordlist is None
        assert args.input == "positions.txt"
        assert not args.verbose


def test_parse_arguments_verbose():
    """Test parse_arguments with verbose flag."""
    with patch("sys.argv", ["main.py", "--verbose"]):
        args = parse_arguments()

        assert args.wordlist is None
        assert args.input is None
        assert args.verbose


def test_parse_arguments_version():
    """Test parse_arguments with version flag."""
    with patch("sys.argv", ["main.py", "--version"]):
        with pytest.raises(SystemExit) as e:
            parse_arguments()

        assert e.value.code == 0


def test_validate_wordlist_path_default():
    """No -w argument selects the bundled wordlist."""
    assert validate_wordlist_path(None) == DEFAULT_WORDLIST_FULLPATH


def test_validate_wordlist_path_explicit_english_txt_is_a_real_path(tmp_path, monkeypatch):
    """Regression: '-w english.txt' silently used the bundled list, not the local file."""
    monkeypatch.chdir(tmp_path)
    assert validate_wordlist_path("english.txt") is None  # no such local file

    (tmp_path / "english.txt").write_text("a\nb\n")
    assert validate_wordlist_path("english.txt") == "english.txt"


def test_validate_wordlist_path_custom_valid():
    """Test validate_wordlist_path with valid custom path."""
    with (
        patch("os.path.exists", return_value=True),
        patch("os.path.isfile", return_value=True),
        patch("os.access", return_value=True),
    ):
        path = validate_wordlist_path("custom_wordlist.txt")

        assert path == "custom_wordlist.txt"


def test_validate_wordlist_path_nonexistent():
    """Test validate_wordlist_path with nonexistent file."""
    with (
        patch("os.path.exists", return_value=False),
        patch("seedshield.main.logger") as mock_logger,
    ):
        path = validate_wordlist_path("nonexistent.txt")

        assert path is None
        mock_logger.error.assert_called_once_with("Wordlist file not found: %s", "nonexistent.txt")


def test_validate_wordlist_path_not_a_file():
    """Test validate_wordlist_path with path that is not a file."""
    with (
        patch("os.path.exists", return_value=True),
        patch("os.path.isfile", return_value=False),
        patch("seedshield.main.logger") as mock_logger,
    ):
        path = validate_wordlist_path("directory/")

        assert path is None
        mock_logger.error.assert_called_once_with("Wordlist path is not a file: %s", "directory/")


def test_validate_wordlist_path_not_readable():
    """Test validate_wordlist_path with file that is not readable."""
    with (
        patch("os.path.exists", return_value=True),
        patch("os.path.isfile", return_value=True),
        patch("os.access", return_value=False),
        patch("seedshield.main.logger") as mock_logger,
    ):
        path = validate_wordlist_path("unreadable.txt")

        assert path is None
        mock_logger.error.assert_called_once_with(
            "No read permission for wordlist file: %s", "unreadable.txt"
        )


def test_main_invalid_wordlist():
    """Test main() with invalid wordlist path."""
    with (
        patch("seedshield.main.parse_arguments") as mock_parse_args,
        patch("seedshield.main.validate_wordlist_path", return_value=None),
        patch("sys.stderr", new_callable=MagicMock()) as mock_stderr,
        patch("sys.exit", side_effect=SystemExit()) as mock_exit,
    ):

        # Configure the mock arguments
        mock_args = MagicMock()
        mock_args.wordlist = "invalid_wordlist.txt"
        mock_args.input = None
        mock_args.verbose = False
        mock_parse_args.return_value = mock_args

        with patch("seedshield.main.SecureWordInterface") as MockSecureInterface:
            # This should exit before creating the SecureWordInterface
            with pytest.raises(SystemExit):
                main()

            # Verify error message and exit
            mock_stderr.write.assert_any_call("Error: Invalid wordlist file: invalid_wordlist.txt")
            mock_exit.assert_called_with(1)
            assert not MockSecureInterface.called


def test_main_invalid_input_file():
    """Test main() with invalid input file."""
    with (
        patch("seedshield.main.parse_arguments") as mock_parse_args,
        patch("seedshield.main.validate_wordlist_path", return_value="valid_wordlist.txt"),
        patch("os.path.exists", return_value=False),
        patch("sys.stderr", new_callable=MagicMock()) as mock_stderr,
        patch("sys.exit", side_effect=SystemExit()) as mock_exit,
    ):

        # Configure the mock arguments
        mock_args = MagicMock()
        mock_args.wordlist = "valid_wordlist.txt"
        mock_args.input = "invalid_input.txt"
        mock_args.verbose = False
        mock_parse_args.return_value = mock_args

        with patch("seedshield.main.SecureWordInterface") as MockSecureInterface:
            # This should exit before using the SecureWordInterface
            with pytest.raises(SystemExit):
                main()

            # Verify error message and exit
            mock_stderr.write.assert_any_call("Error: Input file not found: invalid_input.txt")
            mock_exit.assert_called_with(1)
            assert not MockSecureInterface.called


def test_main_keyboard_interrupt():
    """Test main() handles keyboard interrupt."""
    with (
        patch("seedshield.main.SecureWordInterface") as MockSecureInterface,
        patch("seedshield.main.validate_wordlist_path", return_value="valid_wordlist.txt"),
        patch("sys.exit") as mock_exit,
        patch("seedshield.main.logger") as mock_logger,
    ):

        mock_instance = MockSecureInterface.return_value
        mock_instance.run.side_effect = KeyboardInterrupt()

        with patch("sys.argv", ["main.py"]):
            main()

        # Verify logging and exit
        mock_logger.info.assert_any_call("Received keyboard interrupt, exiting cleanly")
        mock_exit.assert_called_once_with(0)


def test_main_verbose_reports_log_path(tmp_path, monkeypatch, capsys):
    """--verbose tells the user where the log was written."""
    monkeypatch.chdir(tmp_path)
    with (
        patch("sys.argv", ["main.py", "--verbose"]),
        patch("seedshield.main.setup_logging"),
        patch("seedshield.main.SecureWordInterface"),
    ):
        main()

    assert "Verbose log written to" in capsys.readouterr().err


def test_main_invalid_positions_file_exits_with_message(tmp_path, capsys):
    """A rejected -i file exits 1 with a readable error instead of an empty prompt."""
    bad = tmp_path / "positions.txt"
    bad.write_text("1 two 3\n")
    with (
        patch("sys.argv", ["main.py", "-i", str(bad)]),
        patch("seedshield.main.setup_logging"),
        pytest.raises(SystemExit) as exit_info,
    ):
        main()

    assert exit_info.value.code == 1
    assert "Invalid input file" in capsys.readouterr().err


def test_termination_signal_raises_system_exit():
    """SIGTERM/SIGHUP become SystemExit so finally-block cleanup runs."""
    from seedshield.main import _exit_on_signal

    with pytest.raises(SystemExit) as exit_info:
        _exit_on_signal(15, None)
    assert exit_info.value.code == 143


def test_install_signal_handlers_registers_available_signals():
    """Handlers are installed for the termination signals this platform has."""
    import signal as signal_module

    from seedshield.main import _exit_on_signal, install_signal_handlers

    with patch("seedshield.main.signal.signal") as mock_signal:
        install_signal_handlers()

    registered = {c.args[0] for c in mock_signal.call_args_list}
    assert signal_module.SIGTERM in registered
    assert all(c.args[1] is _exit_on_signal for c in mock_signal.call_args_list)
