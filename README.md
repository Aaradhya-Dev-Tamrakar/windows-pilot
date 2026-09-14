# WinPilot (windows-pilot)

[![CI](https://github.com/AaradhyaDT/windows-pilot/actions/workflows/ci.yml/badge.svg)](https://github.com/AaradhyaDT/windows-pilot/actions/workflows/ci.yml)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![MCP Compatible](https://img.shields.io/badge/MCP-1.0-green.svg)](https://modelcontextprotocol.io/)
[![Safety Standard](https://img.shields.io/badge/Safety-Mission--Critical%20Directives-critical.svg)](docs/SAFETY_DIRECTIVES.md)

**WinPilot** is a mission-critical Windows desktop automation toolkit engineered for both **autonomous AI / coding agents** (via Model Context Protocol - MCP) and **human operators** (via CLI and Python SDK).

Instead of relying on fragile pixel coordinates or screen resolutions, WinPilot leverages the native **Microsoft Windows UI Automation (UIA) COM subsystem** and the **Win32 API** to locate and manipulate desktop applications semantically—independent of display resolution, multi-monitor topology, or DPI scaling.

---

## 📑 Documentation Index

- **[Mission-Critical Safety Directives](docs/SAFETY_DIRECTIVES.md)**: Fault management tenets, bounded execution, invariant verification, and fallback ladders.
- **[System Architecture](docs/ARCHITECTURE.md)**: Technical spec of the 4-layer engine, Win32 subsystem focus lock bypass, and DWM cloaking mechanics.
- **[MCP Agent Integration Guide](docs/MCP_GUIDE.md)**: Connecting WinPilot with Claude Desktop, Cursor, and Antigravity with complete tool schemas.
- **[CLI Command Reference](docs/CLI_REFERENCE.md)**: Terminal manual for `list`, `inspect`, `focus`, `click`, `paste`, `screenshot`, and `recipe`.
- **[Application Recipes](docs/RECIPES.md)**: Guide to authoring and using pre-packaged application workflows (including Claude Desktop).
- **[Contributor Guide](CONTRIBUTING.md)**: Development setup, environment instructions, and code standards.
- **[Agent Operating Instructions](AGENTS.md)**: Conventions and gates for autonomous agent contributors.

---

## Key Features

- **Semantic UI Automation (UIA)**: Locates buttons, menus, edit fields, and tabs by accessible names, control types, and IDs (`Button[Name="Submit"]`, `MenuItem[Name*="Haiku"]`).
- **Foreground Lock & Thread Input Bypass**: Safely brings background windows to the foreground without flashing orange taskbar buttons using Windows `AllowSetForegroundWindow` and `AttachThreadInput`.
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

For complete technical specifications, see [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) and [`docs/ACTION_PLAN.md`](docs/ACTION_PLAN.md).

---

## Installation

Requires **Windows 10/11** and **Python 3.10+**.

```powershell
# Clone the repository
git clone https://github.com/AaradhyaDT/windows-pilot.git
cd windows-pilot

# Install via uv (recommended) or standard pip
uv venv
.\.venv\Scripts\activate
uv pip install -e ".[dev]"
```

---

## Quickstart

### 1. CLI Usage

```powershell
# List all visible desktop windows
winpilot list

# Inspect the UI accessibility tree of an application
winpilot inspect "Claude" --depth 3

# Focus a window
winpilot focus "Claude"

# Click an element using CSS-style selector
winpilot click "Claude" "Button[Name*='Model']"

# Paste text safely using Unicode clipboard injection
winpilot paste "Claude" "Explain how quantum entanglement works" --submit

# Take a direct silent screenshot (Win+PrtScn style, zero popups)
winpilot screenshot
winpilot screenshot --window "Claude" --output "claude.png"

# Record screen or target window video with live telemetry
winpilot record --window "Claude" --duration 5 --output "claude_demo.mp4"

# Run Claude Desktop model switcher recipe
winpilot recipe claude-model --model "haiku"
```


For the complete CLI manual, see [`docs/CLI_REFERENCE.md`](docs/CLI_REFERENCE.md).

---

### 2. MCP Server Configuration (for AI Agents)

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

For full setup and tool schemas, see [`docs/MCP_GUIDE.md`](docs/MCP_GUIDE.md).

---

### 3. Python SDK

```python
from winpilot import find_window, ActionChain
from winpilot.recipes.claude_desktop import ClaudeDesktopRecipe

# 1. Automate Claude Desktop with pre-built recipe
claude = ClaudeDesktopRecipe("Claude")
claude.set_model("Haiku 4.5")
claude.send_prompt("Hello from WinPilot!", submit=True)

# 2. Fluent ActionChain on any target window
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

MIT License. Copyright (c) 2026 Aaradhya Dev Tamrakar.
