# WinPilot (windows-pilot)

**WinPilot** is a general-purpose Windows desktop automation toolkit engineered for both **AI / coding agents** (via Model Context Protocol - MCP) and **humans** (via CLI, GUI, and Python SDK).

Instead of relying on fragile pixel coordinates, WinPilot harnesses the **Microsoft Windows UI Automation (UIA) API** and native **Win32 subsystem** to locate and control desktop applications semantically—independent of resolution, DPI scaling, or window positioning.

---

## Key Features

- **Semantic UI Automation (UIA)**: Locates buttons, menus, edit fields, and tabs by accessible names, control types, and IDs (`Button[Name="Submit"]`, `MenuItem[Name*="Haiku"]`).
- **Foreground Lock & Thread Input Bypass**: Safely brings background windows to the foreground without flashing orange taskbars using Windows `AllowSetForegroundWindow` and `AttachThreadInput`.
- **Virtual Desktop Awareness & DWM Uncloaking**: Automatically detects if windows are hidden on secondary virtual desktops (`DWMWA_CLOAKED = 14`) and uncloaks them before interaction.
- **Hardware-Level Input & Unicode Clipboard**: High-speed Unicode clipboard injection (`Ctrl+V`) for multi-kilobyte text without dropped keystrokes.
- **Visual Capture**: Fast window and full-screen screenshots with base64 serialization for multimodal LLMs.
- **Application Recipes**: Pre-configured workflows for complex applications (e.g. Claude Desktop model switching, new chat, and prompt injection).
- **Dual Consumer Interfaces**:
  - **MCP Server (`winpilot-mcp`)**: Native tools for AI agents in Claude Desktop, Cursor, and Antigravity.
  - **Terminal CLI (`winpilot`)**: Colorized Rich terminal inspection, window listing, and manual automation.
  - **Python SDK (`import winpilot`)**: Fluent `ActionChain` builder for custom Python automation scripts.

---

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    CONSUMERS                            │
│   ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌───────┐   │
│   │ MCP      │  │ CLI      │  │ GUI      │  │ Python│   │
│   │ Server   │  │ (winpilot│  │ Builder  │  │ SDK   │   │
│   │ (stdio)  │  │  cli)    │  │ (Phase 2)│  │ import│   │
│   └────┬─────┘  └────┬─────┘  └────┬─────┘  └───┬───┘   │
├────────┴─────────────┴─────────────┴─────────────┴───────┤
│                   Composition Layer                     │
│    - CSS-like Query DSL (Query.find_one)                │
│    - Action Chains (ActionChain(window).click().paste())│
│    - Polling & Synchronization (wait_for_element)       │
├─────────────────────────────────────────────────────────┤
│                     Core Engine                         │
│    - UIATree (Accessibility hierarchy walker)           │
│    - Window (HWND manager, uncloaking, positioning)     │
│    - Input (Hardware keyboard, mouse, clipboard)        │
│    - Screen (Desktop & window visual capture)           │
├─────────────────────────────────────────────────────────┤
│                 Application Recipes                     │
│    - ClaudeDesktopRecipe (model switch, prompt, chat)   │
│    - File Dialogs & Common Windows Controls             │
└─────────────────────────────────────────────────────────┘
```

---

## Installation

Requires Windows 10/11 and Python 3.10+.

```powershell
# Clone the repository
git clone https://github.com/AaradhyaDT/windows-pilot.git
cd windows-pilot

# Install via uv (recommended) or pip
uv venv
.\.venv\Scripts\activate
uv pip install -e .
```

---

## CLI Usage

### 1. List Open Windows
```powershell
winpilot list
# Include cloaked / virtual desktop windows
winpilot list --all
# Filter by process or title
winpilot list --process claude.exe
```

### 2. Inspect Accessibility Tree
Dump the live UI Automation hierarchy for any application:
```powershell
winpilot inspect "Claude" --depth 3
# Or output raw JSON for processing
winpilot inspect "Claude" --depth 2 --json
```

### 3. Window Management & Input
```powershell
# Bring window to front
winpilot focus "Claude"

# Click a button matching a selector query
winpilot click "Claude" "Button[Name*='Model']"

# Paste text directly into a window
winpilot paste "Claude" "Explain quantum entanglement" --submit

# Take a window screenshot
winpilot screenshot --window "Claude" --output "claude.png"
```

### 4. Application Recipes
```powershell
# Select model in Claude Desktop
winpilot recipe claude-model --model haiku
winpilot recipe claude-model --model sonnet

# Dispatch prompt directly to Claude
winpilot recipe claude-prompt "Summarize recent findings"
```

---

## AI Agent / MCP Server Configuration

To connect WinPilot directly to Claude Desktop, Cursor, or your local AI agent framework:

Add WinPilot to your `claude_desktop_config.json` or `team-mcp.json`:

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

### Available MCP Tools

| Tool | Parameters | Description |
|---|---|---|
| `list_desktop_windows` | `title_regex`, `process_name`, `visible_only` | Enumerate open windows with HWND, state, bounds |
| `focus_window` | `hwnd_or_title` | Bring window to front (uncloaks + breaks focus lock) |
| `get_ui_tree` | `hwnd_or_title`, `max_depth` | Dump the UIA tree for agent inspection |
| `click_element` | `hwnd_or_title`, `query`, `method` | Click UI element matching selector query |
| `paste_text` | `hwnd_or_title`, `text`, `submit_enter` | Clipboard paste + optional Enter keypress |
| `send_keys` | `keys_combo` | Press keystrokes (e.g. `ctrl+n`, `esc`) |
| `capture_screenshot` | `hwnd_or_title` | Capture screenshot and return base64 PNG |
| `run_recipe` | `recipe_name`, `action`, `target`, `params_json` | Execute pre-built recipes (`claude_desktop`) |

---

## Python SDK Example

```python
from winpilot import find_window, ActionChain
from winpilot.recipes.claude_desktop import ClaudeDesktopRecipe

# 1. Automate Claude Desktop
claude = ClaudeDesktopRecipe("Claude")
claude.set_model("Haiku 4.5")
claude.send_prompt("Hello from WinPilot!", submit=True)

# 2. Fluent ActionChain on any window
win = find_window(title_regex="Notepad")
if win:
    (
        ActionChain(win)
        .focus()
        .paste("Automated text insertion\n", submit_enter=True)
        .send_combo("ctrl", "s")
        .execute()
    )
```

---

## License

MIT License. Developed by Aaradhya Dev Tamrakar.