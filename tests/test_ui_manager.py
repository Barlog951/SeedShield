"""
Unit tests for the UIManager class.

This module provides comprehensive tests for the UIManager class methods
to ensure proper terminal lifecycle handling and error recovery.
"""

import pytest
from unittest.mock import patch, MagicMock, call

from seedshield.ui_manager import UIManager


class TestUIManager:
    """Tests for the UIManager class."""

    def test_initialization(self, mock_curses, mock_stdscr):
        """Test UIManager initialization."""
        # Configure the mock to return dimensions
        mock_stdscr.getmaxyx.return_value = (24, 80)

        ui = UIManager()
        ui.initialize(mock_stdscr=mock_stdscr)

        assert ui.stdscr == mock_stdscr
        assert ui.height == 24
        assert ui.width == 80

        # Verify terminal setup
        assert mock_stdscr.keypad.called

    def test_initialization_with_mock(self):
        """Test initialization with a provided mock screen."""
        mock_screen = MagicMock()
        # Need to configure the mock to return dimensions
        mock_screen.getmaxyx.return_value = (24, 80)

        ui = UIManager()
        ui.initialize(mock_stdscr=mock_screen)

        assert ui.stdscr == mock_screen
        assert ui.height == 24
        assert ui.width == 80

    def test_initialization_tty_mode(self, mock_curses, mock_stdscr):
        """Test initialization in TTY mode."""
        mock_stdscr.getmaxyx.return_value = (24, 80)

        # Using our own custom mocks to make sure the test works
        mock_halfdelay = MagicMock()

        with (
            patch("sys.stdin.isatty", return_value=True),
            patch("seedshield.ui_manager.curses.halfdelay", mock_halfdelay),
        ):
            ui = UIManager()
            ui.initialize(mock_stdscr=mock_stdscr)

            # Verify halfdelay was called for TTY mode
            assert mock_halfdelay.called
            assert mock_halfdelay.call_args == call(1)
            assert not mock_stdscr.timeout.called

    def test_initialization_non_tty_mode(self, mock_curses, mock_stdscr):
        """Test initialization in non-TTY mode."""
        mock_stdscr.getmaxyx.return_value = (24, 80)
        mock_stdscr.timeout = MagicMock()
        mock_halfdelay = MagicMock()

        with (
            patch("sys.stdin.isatty", return_value=False),
            patch("seedshield.ui_manager.curses.halfdelay", mock_halfdelay),
        ):
            ui = UIManager()
            ui.initialize(mock_stdscr=mock_stdscr)

            # Verify timeout was set for non-TTY mode
            assert mock_stdscr.timeout.called
            assert mock_stdscr.timeout.call_args == call(100)
            assert not mock_halfdelay.called

    def test_initialization_sets_locale(self, mock_stdscr):
        """The locale must be configured before initscr for UTF-8 rendering."""
        mock_stdscr.getmaxyx.return_value = (24, 80)
        manager = MagicMock()

        with (
            patch("seedshield.ui_manager.locale.setlocale") as mock_setlocale,
            patch("seedshield.ui_manager.curses.initscr", return_value=mock_stdscr) as mock_init,
            patch("seedshield.ui_manager.curses.mousemask"),
            patch("seedshield.ui_manager.curses.noecho"),
            patch("seedshield.ui_manager.curses.cbreak"),
            patch("seedshield.ui_manager.curses.halfdelay"),
            patch("sys.stdin.isatty", return_value=True),
        ):
            manager.attach_mock(mock_setlocale, "setlocale")
            manager.attach_mock(mock_init, "initscr")

            ui = UIManager()
            ui.initialize()

            assert mock_setlocale.called
            # setlocale must run before initscr
            names = [c[0] for c in manager.mock_calls]
            assert names.index("setlocale") < names.index("initscr")

    def test_initialization_error(self):
        """Test error handling during initialization."""
        # Create a mock screen that raises an exception when keypad is called
        mock_screen = MagicMock()
        mock_screen.keypad.side_effect = Exception("Test error")

        # Mock the logger to check for error logging
        mock_logger = MagicMock()

        # Create a patched UIManager with a custom cleanup method to verify
        # that cleanup was called during error handling
        ui = UIManager()
        ui.cleanup = MagicMock()  # Replace cleanup with a mock

        with patch("seedshield.ui_manager.logger", mock_logger):
            # The initialize method should raise the original exception
            with pytest.raises(Exception, match="Test error"):
                ui.initialize(mock_stdscr=mock_screen)

            # Verify error was logged
            assert mock_logger.error.called
            # Verify cleanup was attempted
            assert ui.cleanup.called

    def test_cleanup(self, mock_curses, mock_stdscr):
        """Test proper cleanup."""
        with patch("seedshield.ui_manager.curses", mock_curses):
            ui = UIManager()
            ui.initialize(mock_stdscr=mock_stdscr)

            # Reset the mock calls to clearly see cleanup actions
            mock_stdscr.keypad.reset_mock()

            ui.cleanup()

            # Verify terminal restoration
            assert mock_curses.nocbreak.called
            assert mock_stdscr.keypad.called
            assert mock_stdscr.keypad.call_args == call(False)
            assert mock_curses.echo.called
            assert mock_curses.endwin.called

    def test_cleanup_wipes_screen_first(self, mock_curses, mock_stdscr):
        """Revealed words must not survive in scrollback after exit."""
        with patch("seedshield.ui_manager.curses", mock_curses):
            ui = UIManager()
            ui.initialize(mock_stdscr=mock_stdscr)

            manager = MagicMock()
            manager.attach_mock(mock_stdscr.erase, "erase")
            manager.attach_mock(mock_curses.endwin, "endwin")

            ui.cleanup()

            assert mock_stdscr.erase.called
            names = [c[0] for c in manager.mock_calls]
            assert names.index("erase") < names.index("endwin")

    def test_cleanup_is_idempotent(self, mock_curses, mock_stdscr):
        """A second cleanup must be a no-op instead of re-touching curses."""
        with patch("seedshield.ui_manager.curses", mock_curses):
            ui = UIManager()
            ui.initialize(mock_stdscr=mock_stdscr)

            ui.cleanup()
            assert ui.stdscr is None

            mock_curses.endwin.reset_mock()
            ui.cleanup()
            assert not mock_curses.endwin.called

    def test_cleanup_error(self, mock_curses):
        """Test error handling during cleanup."""
        mock_stdscr = MagicMock()
        mock_stdscr.keypad.side_effect = Exception("Cleanup error")

        with patch("seedshield.ui_manager.logger") as mock_logger:
            ui = UIManager()
            ui.stdscr = mock_stdscr
            ui.cleanup()

            # Verify error was logged
            assert mock_logger.error.called

    def test_update_dimensions(self, mock_stdscr):
        """Test updating dimensions."""
        ui = UIManager()
        ui.initialize(mock_stdscr=mock_stdscr)

        height, width = ui.update_dimensions()

        assert height == 24
        assert width == 80
        assert ui.height == 24
        assert ui.width == 80

    def test_with_ui_context(self, mock_curses, mock_stdscr):
        """Test running a function within UI context."""
        callback = MagicMock(return_value="Test result")

        ui = UIManager()

        with patch("seedshield.ui_manager.curses", mock_curses):
            with patch.object(ui, "initialize") as mock_initialize:
                with patch.object(ui, "cleanup") as mock_cleanup:
                    result = ui.with_ui_context(callback)

                    assert result == "Test result"
                    assert callback.called
                    assert mock_initialize.called
                    assert mock_cleanup.called

    def test_with_ui_context_error(self, mock_curses, mock_stdscr):
        """Test error handling within UI context."""
        callback = MagicMock(side_effect=Exception("Context error"))

        ui = UIManager()

        with (
            patch("seedshield.ui_manager.curses", mock_curses),
            patch("seedshield.ui_manager.logger") as mock_logger,
            patch.object(ui, "initialize") as mock_initialize,
            patch.object(ui, "cleanup") as mock_cleanup,
        ):

            with pytest.raises(Exception, match="Context error"):
                ui.with_ui_context(callback)

            # Verify error was logged
            assert mock_logger.error.called
            assert mock_initialize.called
            assert mock_cleanup.called
