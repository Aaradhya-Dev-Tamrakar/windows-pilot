"""
Claude Desktop Application Recipe: Robust UIA + Win32 automation for Claude Desktop instances.
"""

from __future__ import annotations

import re
import time
from typing import Any

from winpilot.core.input import Input
from winpilot.core.uia import UIATree
from winpilot.core.window import Window, list_windows
from winpilot.recipes.base import BaseRecipe


class ClaudeDesktopRecipe(BaseRecipe):
    """Automation recipe for official Claude Desktop on Windows."""

    def __init__(self, window_or_hwnd: Window | str | int = "Claude"):
        super().__init__(window_or_hwnd)
        self.tree = UIATree(self.window)

    def is_app_ready(self) -> bool:
        return self.window.is_valid and self.window.is_visible

    def focus(self) -> bool:
        """Focus the Claude window (handles virtual desktop uncloaking & foreground lock)."""
        return self.window.focus()

    def new_chat(self) -> bool:
        """Triggers a clean new conversation via Ctrl+N."""
        self.focus()
        time.sleep(0.05)
        Input.send_combo("ctrl", "n")
        time.sleep(0.3)
        return True

    def read_current_model(self) -> str:
        """Reads the label of the active model button in the UI (e.g. 'Sonnet 5 Medium')."""
        self.focus()
        elems = self.tree.find_all(control_type="Button")
        for btn in elems:
            name = btn.name.lower()
            if any(k in name for k in ("sonnet", "haiku", "opus", "fable", "medium", "low", "high", "extra")):
                return btn.name
        return "Unknown"

    def open_model_menu(self) -> bool:
        """
        Opens the model selector menu:
        Primary: Dispatches official shortcut Ctrl+Shift+.
        Fallback: Locates and clicks the model selector button in the chat box.
        """
        self.focus()
        time.sleep(0.05)
        # 1. Try official keyboard shortcut (Ctrl+Shift+.)
        Input.send_combo("ctrl", "shift", ".")
        time.sleep(0.3)

        # Check if popover menu rendered
        items = self.tree.find_all(control_type="MenuItem") or self.tree.find_all(control_type="Button")
        if any("effort" in i.name.lower() or "sonnet" in i.name.lower() for i in items):
            return True

        # 2. Fallback: Find and click model button directly
        elems = self.tree.find_all(control_type="Button")
        for btn in elems:
            n = btn.name.lower()
            if any(k in n for k in ("sonnet", "haiku", "opus", "fable", "medium", "low", "high", "extra", "model")):
                btn.click(method="auto")
                time.sleep(0.3)
                return True

        return False

    def toggle_thinking(self) -> dict[str, Any]:
        """
        Toggles extended thinking mode on/off using official shortcut Ctrl+Shift+E.
        """
        self.focus()
        time.sleep(0.05)
        Input.send_combo("ctrl", "shift", "e")
        time.sleep(0.2)
        current = self.read_current_model()
        return {
            "success": True,
            "message": f"Toggled thinking via Ctrl+Shift+E. Current indicator: {current}",
            "active_model_status": current,
        }

    def set_model(self, target_model: str) -> dict[str, Any]:
        """
        Changes active model (e.g. 'Sonnet 5', 'Haiku 4.5', 'Opus 5'):
        1. Opens model menu (Ctrl+Shift+.).
        2. Clicks matching model option in the list.
        """
        self.focus()
        target_clean = target_model.lower().strip()
        if "haiku" in target_clean:
            label_keyword = "haiku"
        elif "opus" in target_clean:
            label_keyword = "opus"
        elif "fable" in target_clean:
            label_keyword = "fable"
        else:
            label_keyword = "sonnet"

        if not self.open_model_menu():
            return {
                "success": False,
                "error": "Could not open model menu (chat view may not be active).",
            }

        # Locate target item in opened menu
        menu_items = self.tree.find_all(control_type="MenuItem") or self.tree.find_all(control_type="Button")
        target_item = None
        for item in menu_items:
            if label_keyword in item.name.lower():
                target_item = item
                break

        if target_item:
            target_item.click(method="auto")
            time.sleep(0.2)
            return {
                "success": True,
                "model_selected": target_item.name,
                "message": f"Successfully selected model: {target_item.name}",
            }
        else:
            Input.press("esc")
            return {
                "success": False,
                "error": f"Model option containing '{label_keyword}' not found in open menu.",
            }

    def set_effort(self, target_effort: str) -> dict[str, Any]:
        """
        Sets response effort level ('low', 'medium', 'high', 'extra', 'max'):
        1. Opens model menu (Ctrl+Shift+.).
        2. Clicks 'Effort' submenu item.
        3. Clicks target effort level.
        """
        self.focus()
        target_clean = target_effort.lower().strip()
        valid_levels = ("low", "medium", "high", "extra", "max")
        if target_clean not in valid_levels:
            return {
                "success": False,
                "error": f"Invalid effort level '{target_effort}'. Must be one of: {valid_levels}",
            }

        if not self.open_model_menu():
            return {"success": False, "error": "Could not open model menu."}

        # Find and click 'Effort' item to open effort submenu
        menu_items = self.tree.find_all(control_type="MenuItem") or self.tree.find_all(control_type="Button")
        effort_btn = None
        for item in menu_items:
            if "effort" in item.name.lower():
                effort_btn = item
                break

        if not effort_btn:
            Input.press("esc")
            return {"success": False, "error": "Effort submenu option not found in model menu."}

        effort_btn.click(method="auto")
        time.sleep(0.3)

        # In submenu, locate target effort level
        sub_items = self.tree.find_all(control_type="MenuItem") or self.tree.find_all(control_type="Button")
        target_level_btn = None
        for item in sub_items:
            if target_clean in item.name.lower():
                target_level_btn = item
                break

        if target_level_btn:
            target_level_btn.click(method="auto")
            time.sleep(0.2)
            return {
                "success": True,
                "effort_selected": target_level_btn.name,
                "message": f"Successfully set effort to: {target_level_btn.name}",
            }
        else:
            Input.press("esc")
            return {
                "success": False,
                "error": f"Effort level '{target_clean}' not found in effort submenu.",
            }

    def send_prompt(self, prompt: str, submit: bool = True) -> bool:
        """
        Dispatches prompt text to the Claude Desktop input area:
        1. Focuses window.
        2. Clicks geometric chat input area (center bottom).
        3. Copies prompt to clipboard and pastes (Ctrl+V).
        4. Presses Enter if submit=True.
        """
        self.focus()
        time.sleep(0.1)

        # Calculate geometric center bottom for the prompt input area
        rect = self.window.rect
        w = rect[2] - rect[0]
        h = rect[3] - rect[1]
        if w > 100 and h > 100:
            cx = rect[0] + w // 2
            cy = rect[1] + int(h * 0.88)
            Input.click(cx, cy)
            time.sleep(0.05)

        return Input.paste_text(prompt, submit_enter=submit, delay_before_enter=0.35)

    def detect_cooldown(self) -> dict[str, Any]:
        """
        Scans Claude Desktop UI for:
        1. 90% message warning banner ('messages remaining until...').
        2. 100% hard limit / cooldown banner ('try again at...', 'reset at...', 'message limit').
        Extracts exact reset timestamp if available.
        """
        self.focus()
        text_elements = self.tree.find_all(control_type="Text")
        res = {
            "in_cooldown": False,
            "warning_90_pct": False,
            "reset_time": None,
            "banner_text": None,
        }
        for t in text_elements:
            content = t.name.strip()
            c_lower = content.lower()
            if "remaining until" in c_lower or "messages remaining" in c_lower:
                res["warning_90_pct"] = True
                res["banner_text"] = content
            if any(k in c_lower for k in ("try again at", "hit the message limit", "usage limit", "limit will reset", "message limit reached")):
                res["in_cooldown"] = True
                res["banner_text"] = content
                match = re.search(r"(?:reset|try again|until)\s+(?:at\s+)?(\d{1,2}:\d{2}(?:\s*[AP]M)?)", content, re.I)
                if match:
                    res["reset_time"] = match.group(1).strip()
                break
        return res


def get_all_claude_instances() -> list[ClaudeDesktopRecipe]:
    """Finds all running Claude Desktop instances and returns their recipe drivers."""
    wins = list_windows(process_name="claude.exe", visible_only=True)
    return [ClaudeDesktopRecipe(w) for w in wins]
