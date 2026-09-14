"""
Base Application Recipe: Abstract template for app-specific automation workflows.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional, Union

from winpilot.core.window import Window, find_window


class BaseRecipe(ABC):
    """Abstract base class for application recipes."""

    def __init__(self, window_or_title: Union[Window, str, int]):
        if isinstance(window_or_title, Window):
            self.window = window_or_title
        elif isinstance(window_or_title, int):
            self.window = Window(window_or_title)
        else:
            w = find_window(title_regex=window_or_title)
            if not w:
                raise ValueError(f"Could not find window matching {window_or_title!r}")
            self.window = w

    @abstractmethod
    def is_app_ready(self) -> bool:
        """Check if application window is loaded and ready."""
        pass
