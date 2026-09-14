"""
Claude Desktop Application Recipe: Robust UIA + Win32 automation for Claude Desktop instances.
"""

from __future__ import annotations

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
        """Reads the label of the active model button in the UI."""
        self.focus()
        # Find model button
        elems = self.tree.find_all(control_type="Button")
        for btn in elems:
            name = btn.name.lower()
            if "sonnet" in name or "haiku" in name or "opus" in name or "model" in name:
                return btn.name
        return "Unknown"

    def set_model(self, target_model: str) -> dict[str, Any]:
        """
        Attempts to change the model using UI Automation accessibility tree traversal:
        1. Finds model selector button.
        2. Clicks to open dropdown popover.
        3. Selects matching model option (e.g. 'Sonnet 5', 'Haiku 4.5').
        """
        self.focus()
        target_clean = target_model.lower().strip()
        if "haiku" in target_clean:
            label_keyword = "haiku"
        elif "opus" in target_clean:
            label_keyword = "opus"
        else:
            label_keyword = "sonnet"

        # 1. Locate model dropdown button
        model_btn = None
        for btn in self.tree.find_all(control_type="Button"):
            n = btn.name.lower()
            if "model" in n or "sonnet" in n or "haiku" in n or "opus" in n:
                model_btn = btn
                break

        if not model_btn:
            return {
                "success": False,
                "error": "Could not locate model selector button in UI. (Ensure chat view is active/new).",
            }

        # 2. Open popover menu
        model_btn.click(method="auto")
        time.sleep(0.3)

        # 3. Locate target menuitem in opened popup
        # Re-query elements after popup opens
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
            # Dismiss dropdown with Escape
            Input.press("esc")
            return {
                "success": False,
                "error": f"Model option containing '{label_keyword}' not found in open menu.",
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

    def detect_cooldown(self) -> bool:
        """Checks for rate limit or 5-hour cooldown banner in the UI."""
        self.focus()
        text_elements = self.tree.find_all(control_type="Text")
        for t in text_elements:
            content = t.name.lower()
            if "try again at" in content or "hit the message limit" in content or "usage limit" in content:
                return True
        return False


def get_all_claude_instances() -> list[ClaudeDesktopRecipe]:
    """Finds all running Claude Desktop instances and returns their recipe drivers."""
    wins = list_windows(process_name="claude.exe", visible_only=True)
    return [ClaudeDesktopRecipe(w) for w in wins]
