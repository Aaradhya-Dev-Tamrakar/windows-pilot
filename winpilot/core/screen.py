"""
Screen Capture Module: Window & desktop screenshot utilities with base64 export.
"""

from __future__ import annotations

import base64
import io
from pathlib import Path
import sys
from typing import Optional, Tuple, Union

from PIL import Image, ImageGrab

from winpilot.core.window import Window, attach_default_desktop


class Screen:
    """Provides screenshot and visual capture utilities."""

    @staticmethod
    def capture_desktop(bbox: Optional[Tuple[int, int, int, int]] = None) -> Image.Image:
        """Capture the full desktop or a specific bounding box (left, top, right, bottom)."""
        attach_default_desktop()
        return ImageGrab.grab(bbox=bbox, all_screens=True)

    @staticmethod
    def capture_window(window_or_hwnd: Union[Window, int]) -> Optional[Image.Image]:
        """Capture the visual rectangle of a specific window."""
        attach_default_desktop()
        w = window_or_hwnd if isinstance(window_or_hwnd, Window) else Window(window_or_hwnd)
        if not w.is_valid or not w.is_visible:
            return None
        rect = w.rect
        # If window is offscreen or collapsed, return None
        if rect[2] <= rect[0] or rect[3] <= rect[1]:
            return None
        return ImageGrab.grab(bbox=rect, all_screens=True)

    @staticmethod
    def save(
        image: Image.Image,
        dest_path: Union[str, Path],
        format: str = "PNG",
    ) -> Path:
        """Save a PIL Image to disk."""
        p = Path(dest_path).resolve()
        p.parent.mkdir(parents=True, exist_ok=True)
        image.save(str(p), format=format)
        return p

    @staticmethod
    def to_base64(image: Image.Image, format: str = "PNG") -> str:
        """Convert a PIL Image to a base64 encoded string (useful for MCP vision tools)."""
        buffered = io.BytesIO()
        image.save(buffered, format=format)
        return base64.b64encode(buffered.getvalue()).decode("utf-8")
