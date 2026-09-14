"""Tests for WinPilot ActionChain composition layer."""

from unittest.mock import MagicMock, patch

from winpilot.compose.actions import ActionChain
from winpilot.core.window import Window


def test_action_chain_initialization():
    mock_win = MagicMock(spec=Window)
    mock_win.hwnd = 12345
    with patch("winpilot.compose.actions.UIATree"):
        chain = ActionChain(mock_win)
        assert len(chain._actions) == 0
        assert chain.window == mock_win


def test_action_chain_fluent_builder():
    mock_win = MagicMock(spec=Window)
    mock_win.hwnd = 12345
    with patch("winpilot.compose.actions.UIATree"):
        chain = ActionChain(mock_win)
        chain.focus().wait(0.1).find("Button[Name='Ok']").press("enter")
        assert len(chain._actions) == 4


def test_action_chain_execution_flow():
    mock_win = MagicMock(spec=Window)
    mock_win.hwnd = 12345
    mock_win.focus = MagicMock()

    executed = []

    def custom_act():
        executed.append("done")

    with patch("winpilot.compose.actions.UIATree"):
        chain = ActionChain(mock_win)
        chain.focus().custom(custom_act)
        assert chain.execute() is True

    mock_win.focus.assert_called_once()
    assert executed == ["done"]
