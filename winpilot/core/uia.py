"""
Windows UI Automation (UIA) Module: Accessibility tree traversal, element inspection, and pattern invocation.
"""

from __future__ import annotations

import re
import sys
import time
from typing import Any

from winpilot.core.input import Input
from winpilot.core.window import Window, attach_default_desktop

if sys.platform == "win32":
    from pywinauto.controls.uiawrapper import UIAWrapper
    from pywinauto.uia_element_info import UIAElementInfo


class UIElement:
    """Standardized wrapper around a Windows UI Automation element."""

    def __init__(self, wrapper_or_info: Any):
        if isinstance(wrapper_or_info, UIAWrapper):
            self._wrapper = wrapper_or_info
            self._info = wrapper_or_info.element_info
        elif isinstance(wrapper_or_info, UIAElementInfo):
            self._info = wrapper_or_info
            self._wrapper = None
        else:
            raise ValueError(f"Unsupported UIA element type: {type(wrapper_or_info)}")

    @property
    def name(self) -> str:
        try:
            return self._info.name or ""
        except Exception:
            return ""

    @property
    def control_type(self) -> str:
        try:
            return self._info.control_type or ""
        except Exception:
            return ""

    @property
    def automation_id(self) -> str:
        try:
            return self._info.automation_id or ""
        except Exception:
            return ""

    @property
    def class_name(self) -> str:
        try:
            return self._info.class_name or ""
        except Exception:
            return ""

    @property
    def handle(self) -> int:
        try:
            return self._info.handle or 0
        except Exception:
            return 0

    @property
    def rect(self) -> tuple[int, int, int, int]:
        """Returns (left, top, right, bottom) bounding rectangle."""
        try:
            r = self._info.rectangle
            return (r.left, r.top, r.right, r.bottom)
        except Exception:
            return (0, 0, 0, 0)

    @property
    def center(self) -> tuple[int, int]:
        l, t, r, b = self.rect
        return (l + (r - l) // 2, t + (b - t) // 2)

    @property
    def is_visible(self) -> bool:
        try:
            return bool(self._info.visible)
        except Exception:
            return False

    @property
    def is_enabled(self) -> bool:
        try:
            return bool(self._info.enabled)
        except Exception:
            return False

    def _get_wrapper(self) -> UIAWrapper:
        if self._wrapper is None:
            self._wrapper = UIAWrapper(self._info)
        return self._wrapper

    def click(self, method: str = "auto") -> bool:
        """
        Clicks the element.
        method:
          - "auto": Tries programmatic InvokePattern first, falls back to hardware click.
          - "invoke": Only uses UIA InvokePattern / TogglePattern / SelectionItemPattern.
          - "hardware": Clicks the center coordinates using Windows mouse_event.
        """
        attach_default_desktop()
        if method in ("auto", "invoke"):
            try:
                wrap = self._get_wrapper()
                # Check for InvokePattern
                if hasattr(wrap, "invoke"):
                    wrap.invoke()
                    return True
                # Check for TogglePattern
                if hasattr(wrap, "toggle"):
                    wrap.toggle()
                    return True
                # Check for SelectionItemPattern
                if hasattr(wrap, "select"):
                    wrap.select()
                    return True
            except Exception:
                if method == "invoke":
                    return False

        # Hardware click fallback
        cx, cy = self.center
        if cx > 0 and cy > 0:
            Input.click(cx, cy)
            return True
        return False

    def set_text(self, text: str) -> bool:
        """Sets text using ValuePattern or clipboard paste."""
        attach_default_desktop()
        try:
            wrap = self._get_wrapper()
            if hasattr(wrap, "set_text"):
                wrap.set_text(text)
                return True
        except Exception:
            pass

        # Fallback: click center and paste
        self.click(method="hardware")
        time.sleep(0.05)
        return Input.paste_text(text)

    def children(self) -> list[UIElement]:
        """Get direct child elements."""
        try:
            return [UIElement(c) for c in self._info.children()]
        except Exception:
            return []

    def descendants(self, depth: int = 10) -> list[UIElement]:
        """Get all descendant elements up to depth."""
        try:
            return [UIElement(d) for d in self._info.descendants(depth=depth)]
        except Exception:
            return []

    def to_dict(self, include_children: bool = False, max_depth: int = 2) -> dict[str, Any]:
        """Converts element info into a clean dictionary for MCP and CLI outputs."""
        data = {
            "name": self.name,
            "control_type": self.control_type,
            "automation_id": self.automation_id,
            "class_name": self.class_name,
            "rect": self.rect,
            "center": self.center,
            "visible": self.is_visible,
            "enabled": self.is_enabled,
        }
        if include_children and max_depth > 0:
            data["children"] = [
                c.to_dict(include_children=True, max_depth=max_depth - 1)
                for c in self.children()
            ]
        return data

    def __repr__(self) -> str:
        return f"<UIElement type={self.control_type!r} name={self.name!r} id={self.automation_id!r}>"


class UIATree:
    """UI Automation Tree explorer for a specific Window or root element."""

    def __init__(self, root: Window | int | UIElement):
        attach_default_desktop()
        if isinstance(root, Window):
            self.hwnd = root.hwnd
            self.root_element = UIElement(UIAElementInfo(root.hwnd))
        elif isinstance(root, int):
            self.hwnd = root
            self.root_element = UIElement(UIAElementInfo(root))
        elif isinstance(root, UIElement):
            self.hwnd = root.handle
            self.root_element = root
        else:
            raise ValueError(f"Invalid root: {root}")

    def dump_tree(self, max_depth: int = 3, visible_only: bool = True) -> dict[str, Any]:
        """Dumps a hierarchical representation of the UIA tree."""
        attach_default_desktop()

        def _traverse(elem: UIElement, depth: int) -> dict[str, Any] | None:
            if visible_only and not elem.is_visible:
                # If root, still show
                if depth > 0:
                    return None
            node = {
                "name": elem.name,
                "type": elem.control_type,
                "id": elem.automation_id,
                "rect": elem.rect,
            }
            if depth < max_depth:
                children_nodes = []
                for c in elem.children():
                    child_dict = _traverse(c, depth + 1)
                    if child_dict:
                        children_nodes.append(child_dict)
                if children_nodes:
                    node["children"] = children_nodes
            return node

        return _traverse(self.root_element, 0) or {}

    def find_all(
        self,
        name: str | None = None,
        name_regex: str | None = None,
        control_type: str | None = None,
        automation_id: str | None = None,
        max_depth: int = 8,
        visible_only: bool = False,
    ) -> list[UIElement]:
        """Finds all descendant elements matching the criteria."""
        attach_default_desktop()
        results: list[UIElement] = []
        name_pattern = re.compile(name_regex, re.IGNORECASE) if name_regex else None
        target_name = name.lower() if name else None
        target_type = control_type.lower() if control_type else None
        target_id = automation_id.lower() if automation_id else None

        for elem in self.root_element.descendants(depth=max_depth):
            if visible_only and not elem.is_visible:
                continue
            if target_name and target_name not in elem.name.lower():
                continue
            if name_pattern and not name_pattern.search(elem.name):
                continue
            if target_type and target_type != elem.control_type.lower():
                continue
            if target_id and target_id != elem.automation_id.lower():
                continue
            results.append(elem)

        return results

    def find_one(
        self,
        name: str | None = None,
        name_regex: str | None = None,
        control_type: str | None = None,
        automation_id: str | None = None,
        max_depth: int = 8,
        visible_only: bool = False,
    ) -> UIElement | None:
        """Finds the first matching element."""
        elems = self.find_all(
            name=name,
            name_regex=name_regex,
            control_type=control_type,
            automation_id=automation_id,
            max_depth=max_depth,
            visible_only=visible_only,
        )
        return elems[0] if elems else None
