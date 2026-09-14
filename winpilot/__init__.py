"""
WinPilot: General-purpose Windows Desktop Automation Toolkit for AI Agents and Humans.
Uses the Windows UI Automation (UIA) API for semantic, DPI-independent control.
"""

from winpilot.core.window import Window, find_window, list_windows
from winpilot.core.uia import UIATree, UIElement
from winpilot.core.input import Input
from winpilot.core.screen import Screen
from winpilot.compose.actions import ActionChain
from winpilot.compose.query import Query

__version__ = "0.1.0"
__all__ = [
    "Window",
    "find_window",
    "list_windows",
    "UIATree",
    "UIElement",
    "Input",
    "Screen",
    "ActionChain",
    "Query",
]
