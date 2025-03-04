from unittest.mock import patch, MagicMock
import pytest
import sys
import curses
from seedshield.main import main
from seedshield.ui_manager import UIManager

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
    with patch('seedshield.main.SecureWordInterface') as MockSecureInterface:
        mock_instance = MockSecureInterface.return_value  # Mock the instance returned
        with patch('sys.argv', ['main.py']):
            with patch('seedshield.main.validate_wordlist_path', return_value='seedshield/data/english.txt'):
                with patch.object(UIManager, 'cleanup') as mock_cleanup:
                    main()

    # Verify SecureWordInterface instantiated with the validated wordlist path
    MockSecureInterface.assert_called_once_with('seedshield/data/english.txt')
    
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
    with patch('seedshield.main.SecureWordInterface') as MockSecureInterface:
        mock_instance = MockSecureInterface.return_value
        with patch('sys.argv', ['main.py', '--wordlist', 'custom_wordlist.txt']):
            # Mock validate_wordlist_path to return the custom wordlist path
            with patch('seedshield.main.validate_wordlist_path', return_value='custom_wordlist.txt'):
                with patch('os.path.exists', return_value=True):  # Mock file existence check
                    with patch('os.path.isfile', return_value=True):  # Mock file type check
                        with patch('os.access', return_value=True):  # Mock access permission check
                            with patch.object(UIManager, 'cleanup') as mock_cleanup:
                                with patch('seedshield.ui_manager.UIManager') as MockUIManager:
                                    mock_ui_instance = MockUIManager.return_value
                                    main()

    # Verify SecureWordInterface instantiated with the validated custom wordlist path
    MockSecureInterface.assert_called_once_with('custom_wordlist.txt')
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
    with patch('seedshield.main.SecureWordInterface') as MockSecureInterface:
        mock_instance = MockSecureInterface.return_value
        with patch('sys.argv', ['main.py', '--input', 'positions.txt']):
            with patch('seedshield.main.validate_wordlist_path', return_value='seedshield/data/english.txt'):
                with patch('os.path.exists', side_effect=lambda x: x != 'positions.txt' or True):
                    with patch.object(UIManager, 'cleanup') as mock_cleanup:
                        with patch('seedshield.ui_manager.UIManager') as MockUIManager:
                            mock_ui_instance = MockUIManager.return_value
                            main()

    # Verify SecureWordInterface instantiated with the validated wordlist path
    MockSecureInterface.assert_called_once_with('seedshield/data/english.txt')
    # Verify run method was called with the input file
    mock_instance.run.assert_called_once_with('positions.txt')


def test_main_generic_exception():
    """
    Test main() handles an unexpected exception gracefully.

    Verifies:
    - Error message is printed to stderr
    - Program exits with error code 1
    - Exception message is included in error output
    """
    with patch('seedshield.main.SecureWordInterface') as MockSecureInterface:
        mock_instance = MockSecureInterface.return_value
        mock_instance.run.side_effect = Exception("Unexpected error!")
        with patch('sys.argv', ['main.py']):
            with patch('seedshield.main.validate_wordlist_path', return_value='seedshield/data/english.txt'):
                with patch('sys.stderr', new_callable=MagicMock()) as mock_stderr:
                    with patch('sys.exit') as mock_exit:
                        main()

    # Assert the error message components were written correctly
    mock_stderr.write.assert_any_call("Error: Unexpected error!")
    mock_stderr.write.assert_any_call("\n")

    # Verify the program exits with an error code
    mock_exit.assert_called_once_with(1)