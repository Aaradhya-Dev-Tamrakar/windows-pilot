"""
WinPilot Model Context Protocol (MCP) Server.
Exposes rich Windows UI automation, window management, and recipe tools to AI agents.
"""

from __future__ import annotations

import asyncio
import json
from typing import Any, Dict, List, Optional
import sys

from mcp.server.fastmcp import FastMCP

from winpilot.compose.query import Query
from winpilot.core.input import Input
from winpilot.core.screen import Screen
from winpilot.core.uia import UIATree
from winpilot.core.window import Window, find_window, list_windows
from winpilot.recipes.claude_desktop import ClaudeDesktopRecipe, get_all_claude_instances

mcp = FastMCP("winpilot")


@mcp.tool()
def list_desktop_windows(
    title_regex: Optional[str] = None,
    process_name: Optional[str] = None,
    visible_only: bool = True,
) -> str:
    """List open Windows top-level windows matching title or process filters."""
    wins = list_windows(title_regex=title_regex, process_name=process_name, visible_only=visible_only)
    data = [
        {
            "hwnd": w.hwnd,
            "title": w.title,
            "process_name": w.process_name,
            "pid": w.pid,
            "rect": w.rect,
            "is_visible": w.is_visible,
            "is_cloaked": w.is_cloaked,
        }
        for w in wins
    ]
    return json.dumps(data, indent=2)


@mcp.tool()
def focus_window(hwnd_or_title: str) -> str:
    """Bring a window to the foreground. Automatically uncloaks virtual desktops and bypasses focus lock."""
    if hwnd_or_title.isdigit():
        w = Window(int(hwnd_or_title))
    else:
        w = find_window(title_regex=hwnd_or_title)
    if not w or not w.is_valid:
        return f"Error: Window '{hwnd_or_title}' not found."
    ok = w.focus()
    return f"Window '{w.title}' (HWND={w.hwnd}) focused: {ok}"


@mcp.tool()
def get_ui_tree(hwnd_or_title: str, max_depth: int = 3, visible_only: bool = True) -> str:
    """Dump the UI Automation (UIA) accessibility tree for a window."""
    if hwnd_or_title.isdigit():
        w = Window(int(hwnd_or_title))
    else:
        w = find_window(title_regex=hwnd_or_title)
    if not w or not w.is_valid:
        return f"Error: Window '{hwnd_or_title}' not found."
    tree = UIATree(w)
    data = tree.dump_tree(max_depth=max_depth, visible_only=visible_only)
    return json.dumps(data, indent=2)


@mcp.tool()
def click_element(hwnd_or_title: str, query: str, method: str = "auto") -> str:
    """Click a UI element matching a selector query (e.g. Button[Name='Submit'] or MenuItem[Name*='Haiku'])."""
    if hwnd_or_title.isdigit():
        w = Window(int(hwnd_or_title))
    else:
        w = find_window(title_regex=hwnd_or_title)
    if not w or not w.is_valid:
        return f"Error: Window '{hwnd_or_title}' not found."
    w.focus()
    tree = UIATree(w)
    elem = Query.find_one(tree, query)
    if not elem:
        return f"Error: UI element matching {query!r} not found."
    ok = elem.click(method=method)
    return f"Clicked element {elem.name!r} ({elem.control_type}): {ok}"


@mcp.tool()
def paste_text(hwnd_or_title: str, text: str, submit_enter: bool = False) -> str:
    """Paste text into target window via clipboard and optionally send Enter."""
    if hwnd_or_title.isdigit():
        w = Window(int(hwnd_or_title))
    else:
        w = find_window(title_regex=hwnd_or_title)
    if not w or not w.is_valid:
        return f"Error: Window '{hwnd_or_title}' not found."
    w.focus()
    ok = Input.paste_text(text, submit_enter=submit_enter)
    return f"Pasted {len(text)} characters into '{w.title}': {ok}"


@mcp.tool()
def send_keys(keys_combo: str) -> str:
    """Send key combination (e.g. 'ctrl+n', 'enter', 'esc', 'alt+tab')."""
    keys = [k.strip() for k in keys_combo.split("+")]
    Input.send_combo(*keys)
    return f"Sent key combination: {keys_combo}"


@mcp.tool()
def capture_screenshot(hwnd_or_title: Optional[str] = None) -> str:
    """Capture a screenshot of a window or full desktop and return base64 encoded PNG."""
    if hwnd_or_title:
        if hwnd_or_title.isdigit():
            w = Window(int(hwnd_or_title))
        else:
            w = find_window(title_regex=hwnd_or_title)
        if not w or not w.is_valid:
            return f"Error: Window '{hwnd_or_title}' not found."
        img = Screen.capture_window(w)
    else:
        img = Screen.capture_desktop()

    if not img:
        return "Error: Failed to capture screenshot."
    return Screen.to_base64(img)


@mcp.tool()
def run_recipe(recipe_name: str, action: str, target: str = "Claude", params_json: str = "{}") -> str:
    """
    Execute an application recipe action.
    Supported recipes: 'claude'
    Actions for 'claude': 'set_model', 'send_prompt', 'new_chat', 'read_model', 'detect_cooldown'
    """
    params = json.loads(params_json) if params_json else {}

    if recipe_name.lower() in ("claude", "claude_desktop"):
        recipe = ClaudeDesktopRecipe(target)
        if action == "set_model":
            res = recipe.set_model(params.get("model", "haiku"))
            return json.dumps(res, indent=2)
        elif action == "send_prompt":
            ok = recipe.send_prompt(params.get("prompt", ""), submit=params.get("submit", True))
            return f"Prompt sent: {ok}"
        elif action == "new_chat":
            ok = recipe.new_chat()
            return f"New chat started: {ok}"
        elif action == "read_model":
            m = recipe.read_current_model()
            return f"Active model: {m}"
        elif action == "detect_cooldown":
            cd = recipe.detect_cooldown()
            return f"Cooldown detected: {cd}"
        else:
            return f"Unknown action: {action}"

    return f"Unknown recipe: {recipe_name}"


def main():
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
