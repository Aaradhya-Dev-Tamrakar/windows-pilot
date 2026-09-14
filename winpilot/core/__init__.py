"""Core low-level primitives: Window management, UI Automation, Input, and Screen capture."""

from winpilot.core.window import Window, find_window, list_windows
from winpilot.core.uia import UIATree, UIElement
from winpilot.core.input import Input
from winpilot.core.screen import Screen

__all__ = ["Window", "find_window", "list_windows", "UIATree", "UIElement", "Input", "Screen"]
