"""
Unit tests for the UIManager class.

This module provides comprehensive tests for the UIManager class methods
to ensure proper terminal UI operations and error handling.
"""

import pytest
from unittest.mock import patch, MagicMock, call
import sys

from seedshield.ui_manager import UIManager


class TestUIManager:
    """Tests for the UIManager class."""

    def test_initialization(self, mock_curses, mock_stdscr):
        """Test UIManager initialization."""
        # Configure the mock to return dimensions
        mock_stdscr.getmaxyx.return_value = (24, 80)
        
        ui = UIManager()
        ui.initialize(mock_stdscr=mock_stdscr)
        
        # Call update_dimensions manually since it's not called when using mock_stdscr
        ui.update_dimensions()
        
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
        
        with patch('sys.stdin.isatty', return_value=True), \
             patch('seedshield.ui_manager.curses.halfdelay', mock_halfdelay):
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
        
        with patch('sys.stdin.isatty', return_value=False), \
             patch('seedshield.ui_manager.curses.halfdelay', mock_halfdelay):
            ui = UIManager()
            ui.initialize(mock_stdscr=mock_stdscr)
            
            # Verify timeout was set for non-TTY mode
            assert mock_stdscr.timeout.called
            assert mock_stdscr.timeout.call_args == call(100)
            assert not mock_halfdelay.called
    
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
        
        with patch('seedshield.ui_manager.logger', mock_logger):
            # The initialize method should raise the original exception
            with pytest.raises(Exception, match="Test error"):
                ui.initialize(mock_stdscr=mock_screen)
            
            # Verify error was logged
            assert mock_logger.error.called
            # Verify cleanup was attempted
            assert ui.cleanup.called
    
    def test_cleanup(self, mock_curses, mock_stdscr):
        """Test proper cleanup."""
        with patch('seedshield.ui_manager.curses', mock_curses):
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
    
    def test_cleanup_error(self, mock_curses):
        """Test error handling during cleanup."""
        mock_stdscr = MagicMock()
        mock_stdscr.keypad.side_effect = Exception("Cleanup error")
        
        with patch('seedshield.ui_manager.logger') as mock_logger:
            ui = UIManager()
            ui.stdscr = mock_stdscr
            ui.cleanup()
            
            # Verify error was logged
            assert mock_logger.error.called
    
    def test_get_input(self, mock_curses, mock_stdscr):
        """Test getting input from user."""
        mock_stdscr.getch.return_value = 65  # 'A' character
        
        ui = UIManager()
        ui.initialize(mock_stdscr=mock_stdscr)
        
        # Test normal input
        result = ui.get_input()
        assert result == 65
        assert not mock_curses.echo.called
        
        # Test with echo
        result = ui.get_input(echo=True)
        assert result == 65
        assert mock_curses.echo.called
        assert mock_curses.noecho.called
    
    def test_get_input_error(self, mock_curses, mock_stdscr):
        """Test handling curses error during input."""
        mock_stdscr.getch.side_effect = mock_curses.error
        
        ui = UIManager()
        ui.initialize(mock_stdscr=mock_stdscr)
        
        result = ui.get_input()
        assert result == -1
    
    def test_get_string(self, mock_curses, mock_stdscr):
        """Test getting string input."""
        mock_stdscr.getstr.return_value = b"test input"
        
        ui = UIManager()
        ui.initialize(mock_stdscr=mock_stdscr)
        
        with patch('seedshield.ui_manager.curses', mock_curses):
            result = ui.get_string(10, 5, "Enter: ")
            
            # Verify prompt was displayed
            mock_stdscr.addstr.assert_called_with(10, 5, "Enter: ")
            assert mock_curses.echo.called
            assert mock_curses.noecho.called
            assert result == "test input"
    
    def test_get_string_error(self, mock_curses, mock_stdscr):
        """Test error handling when getting string input."""
        mock_stdscr.getstr.side_effect = Exception("Input error")
        
        ui = UIManager()
        ui.initialize(mock_stdscr=mock_stdscr)
        
        with patch('seedshield.ui_manager.curses', mock_curses):
            result = ui.get_string(10, 5)
            
            assert result == ""
            assert mock_curses.echo.called
            assert mock_curses.noecho.called
    
    def test_update_dimensions(self, mock_stdscr):
        """Test updating dimensions."""
        ui = UIManager()
        ui.initialize(mock_stdscr=mock_stdscr)
        
        height, width = ui.update_dimensions()
        
        assert height == 24
        assert width == 80
        assert ui.height == 24
        assert ui.width == 80
    
    def test_clear_and_refresh(self, mock_stdscr):
        """Test screen clearing and refreshing."""
        ui = UIManager()
        ui.initialize(mock_stdscr=mock_stdscr)
        
        ui.clear()
        assert mock_stdscr.clear.called
        
        ui.refresh()
        assert mock_stdscr.refresh.called
    
    def test_add_text(self, mock_curses, mock_stdscr):
        """Test adding text to the screen."""
        ui = UIManager()
        ui.initialize(mock_stdscr=mock_stdscr)
        
        # Test normal text
        ui.add_text(10, 5, "Test text")
        mock_stdscr.addstr.assert_called_with(10, 5, "Test text")
        
        # Test highlighted text
        ui.add_text(11, 5, "Highlighted", highlight=True)
        mock_stdscr.addstr.assert_called_with(11, 5, "Highlighted", mock_curses.A_REVERSE)
    
    def test_add_text_error(self, mock_curses, mock_stdscr):
        """Test error handling when adding text."""
        mock_stdscr.addstr.side_effect = mock_curses.error
        
        ui = UIManager()
        ui.initialize(mock_stdscr=mock_stdscr)
        
        # Should not raise an exception
        ui.add_text(10, 5, "Test text")
    
    def test_get_mouse_event(self, mock_curses, mock_stdscr):
        """Test getting mouse events."""
        ui = UIManager()
        ui.initialize(mock_stdscr=mock_stdscr)
        
        with patch('seedshield.ui_manager.curses', mock_curses):
            result = ui.get_mouse_event()
            assert result == (0, 10, 5, 0, 0)
    
    def test_with_ui_context(self, mock_curses, mock_stdscr):
        """Test running a function within UI context."""
        callback = MagicMock(return_value="Test result")
        
        ui = UIManager()
        
        with patch('seedshield.ui_manager.curses', mock_curses):
            with patch.object(ui, 'initialize') as mock_initialize:
                with patch.object(ui, 'cleanup') as mock_cleanup:
                    result = ui.with_ui_context(callback)
                    
                    assert result == "Test result"
                    assert callback.called
                    assert mock_initialize.called
                    assert mock_cleanup.called
    
    def test_with_ui_context_error(self, mock_curses, mock_stdscr):
        """Test error handling within UI context."""
        callback = MagicMock(side_effect=Exception("Context error"))
        
        ui = UIManager()
        
        with patch('seedshield.ui_manager.curses', mock_curses), \
             patch('seedshield.ui_manager.logger') as mock_logger, \
             patch.object(ui, 'initialize') as mock_initialize, \
             patch.object(ui, 'cleanup') as mock_cleanup:
            
            with pytest.raises(Exception, match="Context error"):
                ui.with_ui_context(callback)
            
            # Verify error was logged
            assert mock_logger.error.called
            assert mock_initialize.called
            assert mock_cleanup.called