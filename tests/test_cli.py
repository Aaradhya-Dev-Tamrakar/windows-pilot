"""Tests for Window and CLI commands."""

from unittest.mock import MagicMock, patch

from typer.testing import CliRunner

from winpilot.cli import app
from winpilot.core.window import Window

runner = CliRunner()


def test_cli_help():
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "Windows Desktop Automation Toolkit" in result.output


def test_cli_list():
    mock_win = MagicMock()
    mock_win.hwnd = 12345
    mock_win.pid = 6789
    mock_win.process_name = "test.exe"
    mock_win.title = "Test Window"
    mock_win.is_cloaked = False
    mock_win.is_minimized = False
    mock_win.rect = (0, 0, 800, 600)

    with patch("winpilot.cli.list_windows", return_value=[mock_win]):
        result = runner.invoke(app, ["list"])
        assert result.exit_code == 0
        assert "Test Window" in result.output
        assert "12345" in result.output


def test_window_geometry_math():
    w = Window(0)
    with patch.object(Window, "is_valid", False):
        assert w.width == 0
        assert w.height == 0


def test_cli_screenshot():
    from pathlib import Path

    from winpilot.core.screen import CaptureMetadata

    meta = CaptureMetadata(
        target_type="desktop",
        target_name="Full Desktop (All Screens)",
        hwnd=None,
        pid=None,
        process_name=None,
        bounds=(0, 0, 1920, 1080),
        dimensions=(1920, 1080),
        engine="Win32 GDI BitBlt",
        timestamp="2026-09-14 12:00:00",
        file_path=Path("dummy_shot.png"),
    )

    with patch("winpilot.core.screen.Screen.capture_to_file", return_value=(Path("dummy_shot.png"), meta)):
        result = runner.invoke(app, ["screenshot"])
        assert result.exit_code == 0
        assert "Direct Silent Screenshot" in result.output
        assert "dummy_shot.png" in result.output

