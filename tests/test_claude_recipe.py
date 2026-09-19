"""Tests for WinPilot ClaudeDesktopRecipe automation."""

from unittest.mock import MagicMock, patch

from winpilot.core.input import VK_MAP, Input
from winpilot.core.window import Window
from winpilot.recipes.claude_desktop import ClaudeDesktopRecipe


def test_vk_map_period_and_punctuation():
    """Verify VK_MAP contains period and punctuation for shortcuts."""
    assert "." in VK_MAP
    assert VK_MAP["."] == 0xBE
    assert "period" in VK_MAP
    assert VK_MAP["period"] == 0xBE


def test_claude_recipe_toggle_thinking():
    """Verify toggle_thinking dispatches Ctrl+Shift+E."""
    mock_win = MagicMock(spec=Window)
    mock_win.hwnd = 12345
    mock_win.focus.return_value = True

    with patch("winpilot.recipes.claude_desktop.UIATree"), \
         patch.object(Input, "send_combo") as mock_combo:
        recipe = ClaudeDesktopRecipe(mock_win)
        res = recipe.toggle_thinking()

        assert res["success"] is True
        mock_combo.assert_called_once_with("ctrl", "shift", "e")


def test_claude_recipe_set_model():
    """Verify set_model opens menu and selects target model item."""
    mock_win = MagicMock(spec=Window)
    mock_win.hwnd = 12345
    mock_win.focus.return_value = True

    mock_sonnet = MagicMock()
    mock_sonnet.name = "Sonnet 5"
    mock_sonnet.click.return_value = True

    with patch("winpilot.recipes.claude_desktop.UIATree") as mock_tree_cls, \
         patch.object(Input, "send_combo"):
        mock_tree = mock_tree_cls.return_value
        mock_tree.find_all.return_value = [mock_sonnet]

        recipe = ClaudeDesktopRecipe(mock_win)
        res = recipe.set_model("sonnet")

        assert res["success"] is True
        assert res["model_selected"] == "Sonnet 5"
        mock_sonnet.click.assert_called_once()


def test_claude_recipe_set_effort():
    """Verify set_effort navigates Effort submenu and selects target effort level."""
    mock_win = MagicMock(spec=Window)
    mock_win.hwnd = 12345
    mock_win.focus.return_value = True

    mock_effort_btn = MagicMock()
    mock_effort_btn.name = "Effort Medium >"
    mock_effort_btn.click.return_value = True

    mock_high_btn = MagicMock()
    mock_high_btn.name = "High"
    mock_high_btn.click.return_value = True

    with patch("winpilot.recipes.claude_desktop.UIATree") as mock_tree_cls, \
         patch.object(Input, "send_combo"):
        mock_tree = mock_tree_cls.return_value
        # 1st call for open_model_menu, 2nd for Effort btn, 3rd for High in submenu
        mock_tree.find_all.side_effect = [
            [mock_effort_btn],  # open_model_menu verification
            [mock_effort_btn],  # locate effort menu item
            [mock_high_btn],    # locate target effort level in submenu
        ]

        recipe = ClaudeDesktopRecipe(mock_win)
        res = recipe.set_effort("high")

        assert res["success"] is True
        assert res["effort_selected"] == "High"
        mock_effort_btn.click.assert_called_once()
        mock_high_btn.click.assert_called_once()


def test_claude_recipe_detect_cooldown():
    """Verify detect_cooldown extracts exact reset timestamp from banner text."""
    mock_win = MagicMock(spec=Window)
    mock_win.hwnd = 12345
    mock_win.focus.return_value = True

    mock_banner = MagicMock()
    mock_banner.name = "You've reached your message limit. Try again at 3:15 PM."

    with patch("winpilot.recipes.claude_desktop.UIATree") as mock_tree_cls:
        mock_tree = mock_tree_cls.return_value
        mock_tree.find_all.return_value = [mock_banner]

        recipe = ClaudeDesktopRecipe(mock_win)
        res = recipe.detect_cooldown()

        assert res["in_cooldown"] is True
        assert res["reset_time"] == "3:15 PM"
