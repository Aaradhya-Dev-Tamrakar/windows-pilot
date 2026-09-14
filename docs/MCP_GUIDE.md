# Model Context Protocol (MCP) Integration Guide

WinPilot includes a native, high-performance MCP server (`winpilot-mcp`) built on FastMCP. This allows LLM agents—including Claude Desktop, Cursor, Antigravity, and custom agentic frameworks—to autonomously explore, inspect, and automate Windows desktop applications without human intervention.

---

## 1. Quick Configuration

### Claude Desktop (`claude_desktop_config.json`)

On Windows, locate your Claude Desktop configuration file at:
`%APPDATA%\Claude\claude_desktop_config.json`

Add the `winpilot` server entry:

```json
{
  "mcpServers": {
    "winpilot": {
      "command": "F:\\Aaradhya-Dev-Tamrakar\\windows-pilot\\.venv\\Scripts\\winpilot.exe",
      "args": ["serve", "--transport", "stdio"]
    }
  }
}
```

> [!TIP]
> Ensure double backslashes (`\\`) are used for paths in Windows JSON configurations.

---

## 2. Available MCP Tools Reference

The WinPilot MCP server registers 8 tools designed around safe, semantic operations:

### 1. `list_desktop_windows`
Enumerate all open, active desktop windows with their HWND, PID, process name, window title, bounding rectangles, and cloaked state.
- **Parameters**:
  - `title_regex` (optional, string): Filter window titles by regular expression.
  - `process_name` (optional, string): Filter by process executable (e.g. `claude.exe`, `notepad.exe`).
  - `visible_only` (optional, boolean, default `true`): Exclude zero-sized or minimized helper windows.
- **Agent Usage**: Call this first to locate the target `HWND` or exact title of the application you need to interact with.

### 2. `focus_window`
Brings a target window safely to the foreground, automatically bypassing Windows foreground locks and uncloaking virtual desktop windows.
- **Parameters**:
  - `hwnd_or_title` (required, string): Window HWND as an integer string or regex title pattern.

### 3. `get_ui_tree`
Walks and dumps the UI Automation accessibility hierarchy starting from the window or a specific subtree.
- **Parameters**:
  - `hwnd_or_title` (required, string): Target window.
  - `max_depth` (optional, integer, default `3`): Maximum depth of traversal to keep token payloads compact.
- **Agent Usage**: Use this to discover accessible names, control types (`Button`, `Edit`, `MenuItem`), and `AutomationId` values before constructing a selector query.

### 4. `click_element`
Finds an element matching a CSS-style query selector and triggers it via the Fallback Ladder (UIA InvokePattern -> Win32 click -> Physical mouse).
- **Parameters**:
  - `hwnd_or_title` (required, string): Target window.
  - `query` (required, string): CSS-like selector (e.g. `Button[Name="Submit"]`, `MenuItem[Name*="Sonnet"]`).
  - `method` (optional, string, default `"auto"`): One of `"auto"`, `"pattern"`, or `"physical"`.

### 5. `paste_text`
Injects text into the active focused element of the target window using atomic Unicode clipboard paste (`Ctrl+V`).
- **Parameters**:
  - `hwnd_or_title` (required, string): Target window.
  - `text` (required, string): Unicode text content to paste.
  - `submit_enter` (optional, boolean, default `false`): If `true`, dispatches an Enter keystroke immediately following the paste.

### 6. `send_keys`
Dispatches hardware keystrokes and key combinations to the target window.
- **Parameters**:
  - `keys_combo` (required, string): Key combination string (e.g. `"ctrl+n"`, `"alt+f4"`, `"esc"`, `"enter"`).

### 7. `capture_screenshot`
Captures a high-resolution screenshot of the target window (or full screen) and returns a base64-encoded PNG image.
- **Parameters**:
  - `hwnd_or_title` (optional, string): Target window. Omit for full desktop screenshot.
- **Agent Usage**: Ideal for multimodal verification, checking visual layout changes, or analyzing applications with sparse accessibility trees.

### 8. `run_recipe`
Executes an established application recipe workflow.
- **Parameters**:
  - `recipe_name` (required, string): Name of recipe (e.g. `"claude_desktop"`).
  - `action` (required, string): Recipe action (e.g. `"set_model"`, `"send_prompt"`).
  - `target` (optional, string, default `"Claude"`): Target window.
  - `params_json` (optional, string): JSON-encoded dictionary of action parameters.

---

## 3. Best Practices for AI Agents

1. **Inspect Before Actuation**: Call `list_desktop_windows` followed by `get_ui_tree` with `max_depth=2` to discover available elements before attempting to click.
2. **Favor CSS Attribute Matching**: Use substring selectors (`Button[Name*="Model"]`) rather than strict equality if button labels change dynamically with version or state.
3. **Handle Modals & Popovers**: When clicking a dropdown or popover, call `get_ui_tree` again or use bounded wait conditions to ensure child popover nodes have mounted in the UIA tree.
4. **Use Clipboard Paste for Prompts**: Avoid typing long multiline messages character-by-character; `paste_text` is instantaneous and preserves whitespace and Unicode emojis.
