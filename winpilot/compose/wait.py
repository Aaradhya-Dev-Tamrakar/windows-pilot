"""
Wait Conditions: Polling and synchronization primitives for UI element state transitions.
"""

from __future__ import annotations

import time

from winpilot.compose.query import Query
from winpilot.core.uia import UIATree, UIElement
from winpilot.core.window import Window, find_window


def wait_for_window(
    title_regex: str | None = None,
    process_name: str | None = None,
    timeout: float = 10.0,
    poll_interval: float = 0.3,
) -> Window:
    """Polls until a matching window is discovered or timeout occurs."""
    start = time.time()
    while time.time() - start < timeout:
        w = find_window(title_regex=title_regex, process_name=process_name)
        if w and w.is_valid and w.is_visible:
            return w
        time.sleep(poll_interval)
    raise TimeoutError(f"Window matching (title={title_regex}, process={process_name}) not found within {timeout}s")


def wait_for_element(
    tree_or_window: UIATree | Window | UIElement,
    query_str: str,
    timeout: float = 5.0,
    poll_interval: float = 0.2,
    visible_only: bool = True,
) -> UIElement:
    """Polls until an element matching the query is found or timeout occurs."""
    tree = tree_or_window if isinstance(tree_or_window, UIATree) else UIATree(tree_or_window)
    start = time.time()
    while time.time() - start < timeout:
        elem = Query.find_one(tree, query_str)
        if elem and (not visible_only or elem.is_visible):
            return elem
        time.sleep(poll_interval)
    raise TimeoutError(f"UI element matching {query_str!r} not found within {timeout}s")


def wait_until_gone(
    tree_or_window: UIATree | Window | UIElement,
    query_str: str,
    timeout: float = 5.0,
    poll_interval: float = 0.2,
) -> bool:
    """Polls until an element matching the query is no longer present or visible."""
    tree = tree_or_window if isinstance(tree_or_window, UIATree) else UIATree(tree_or_window)
    start = time.time()
    while time.time() - start < timeout:
        elem = Query.find_one(tree, query_str)
        if not elem or not elem.is_visible:
            return True
        time.sleep(poll_interval)
    return False
