import pytest
from unittest.mock import patch
from seedshield.display_handler import DisplayHandler
from tests.test_fixtures import mock_stdscr


def test_display_handler_init():
    handler = DisplayHandler(["word1", "word2"])
    assert handler.words == ["word1", "word2"]
    assert handler.legacy_mask == "*****"


def test_calculate_visible_range():
    handler = DisplayHandler(["word1"])
    assert handler.calculate_visible_range(10) == 1
    assert handler.calculate_visible_range(20) == 6


def test_handle_scroll():
    handler = DisplayHandler(["word1"])
    height = 20

    # Test scroll forward
    assert handler.handle_scroll(5, 0, height) == 0
    assert handler.handle_scroll(10, 5, height) == 5

    # Test scroll backward
    assert handler.handle_scroll(3, 5, height) == 3


def test_display_words(mock_stdscr):
    handler = DisplayHandler(["word1", "word2", "word3"])
    positions = [1, 2, 3]
    visible_count = handler.display_words(mock_stdscr, positions, 0, 0, False)
    assert visible_count > 0


def test_scroll_indicators(mock_stdscr):
    handler = DisplayHandler(["word1", "word2", "word3"])
    mock_stdscr.getmaxyx.return_value = (10, 80)

    # Test with scroll up indicator
    handler._add_scroll_indicators(mock_stdscr, 1, 2, [1, 2, 3], 10, 80)
    mock_stdscr.addstr.assert_called()


@pytest.mark.parametrize("is_last_reached", [True, False])
def test_menu_display(mock_stdscr, is_last_reached):
    handler = DisplayHandler(["word1"])
    handler._add_menu(mock_stdscr, 10, is_last_reached)
    assert mock_stdscr.addstr.call_count >= 3


def test_display_words_with_masking(mock_stdscr):
    handler = DisplayHandler(["word1", "word2"])
    positions = [1, 2]

    # Test masked display
    handler.display_words(mock_stdscr, positions, 0, 0, False)

    # Test revealed word
    handler.display_words(mock_stdscr, positions, 0, 0, False)


def test_display_boundaries(mock_stdscr):
    handler = DisplayHandler(["word1", "word2", "word3"])
    mock_stdscr.getmaxyx.return_value = (5, 80)

    # Test with small window
    result = handler.display_words(mock_stdscr, [1, 2, 3], 0, 0, False)
    assert result < 3  # Should show fewer words due to size constraint


def test_scroll_position_limits(mock_stdscr):
    handler = DisplayHandler(["word1", "word2", "word3"])

    # Test scroll boundaries
    assert handler.handle_scroll(0, 0, 10) == 0  # Lower bound
    assert handler.handle_scroll(5, 5, 10) == 5  # Upper bound