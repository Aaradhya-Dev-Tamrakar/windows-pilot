"""
Action Chains: Composable, fluent automation pipelines with automatic retry and error handling.
"""

from __future__ import annotations

import time
from collections.abc import Callable
from typing import Any

from winpilot.compose.wait import wait_for_element, wait_until_gone
from winpilot.core.input import Input
from winpilot.core.uia import UIATree, UIElement
from winpilot.core.window import Window


class ActionChain:
    """Fluent action pipeline builder for automating a window."""

    def __init__(self, window_or_hwnd: Window | int):
        self.window = window_or_hwnd if isinstance(window_or_hwnd, Window) else Window(window_or_hwnd)
        self.tree = UIATree(self.window)
        self._actions: list[Callable[[], Any]] = []
        self._last_element: UIElement | None = None

    def focus(self) -> ActionChain:
        def _act():
            self.window.focus()
        self._actions.append(_act)
        return self

    def wait(self, seconds: float) -> ActionChain:
        def _act():
            time.sleep(seconds)
        self._actions.append(_act)
        return self

    def find(self, query_str: str, timeout: float = 5.0) -> ActionChain:
        def _act():
            self._last_element = wait_for_element(self.tree, query_str, timeout=timeout)
        self._actions.append(_act)
        return self

    def click(self, query_str: str | None = None, method: str = "auto", timeout: float = 5.0) -> ActionChain:
        def _act():
            if query_str:
                elem = wait_for_element(self.tree, query_str, timeout=timeout)
                elem.click(method=method)
                self._last_element = elem
            elif self._last_element:
                self._last_element.click(method=method)
            else:
                raise RuntimeError("No target element to click. Call find() first or pass query_str.")
        self._actions.append(_act)
        return self

    def type_text(self, text: str, query_str: str | None = None, delay: float = 0.01) -> ActionChain:
        def _act():
            if query_str:
                elem = wait_for_element(self.tree, query_str)
                elem.click(method="auto")
                time.sleep(0.05)
            Input.type_text(text, delay=delay)
        self._actions.append(_act)
        return self

    def paste(self, text: str, query_str: str | None = None, submit_enter: bool = False) -> ActionChain:
        def _act():
            if query_str:
                elem = wait_for_element(self.tree, query_str)
                elem.click(method="auto")
                time.sleep(0.05)
            Input.paste_text(text, submit_enter=submit_enter)
        self._actions.append(_act)
        return self

    def press(self, key_name: str, count: int = 1) -> ActionChain:
        def _act():
            Input.press(key_name, count=count)
        self._actions.append(_act)
        return self

    def send_combo(self, *keys: str) -> ActionChain:
        def _act():
            Input.send_combo(*keys)
        self._actions.append(_act)
        return self

    def wait_for(self, query_str: str, timeout: float = 5.0) -> ActionChain:
        def _act():
            self._last_element = wait_for_element(self.tree, query_str, timeout=timeout)
        self._actions.append(_act)
        return self

    def wait_until_gone(self, query_str: str, timeout: float = 5.0) -> ActionChain:
        def _act():
            wait_until_gone(self.tree, query_str, timeout=timeout)
        self._actions.append(_act)
        return self

    def screenshot(self, output_path: str | None = None) -> ActionChain:
        """Capture a silent screenshot of the target window."""
        from winpilot.core.screen import Screen

        def _act():
            Screen.capture_to_file(self.window, dest_path=output_path)
        self._actions.append(_act)
        return self

    def custom(self, func: Callable[[], Any]) -> ActionChain:
        self._actions.append(func)
        return self

    def execute(self) -> bool:
        """Executes all queued actions sequentially."""
        try:
            for act in self._actions:
                act()
            return True
        except Exception as e:
            raise e

