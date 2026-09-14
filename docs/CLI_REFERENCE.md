# WinPilot CLI Command Reference

WinPilot provides a rich, terminal-first interface for inspecting, querying, and driving Windows desktop automation tasks.

---

## Global Options

```powershell
winpilot --help
```

---

## Commands

### `winpilot list` (Alias: `winpilot list-windows`)
Enumerate and display active desktop windows in a formatted Rich table.

```powershell
# Default: List non-cloaked, visible windows
winpilot list

# List all windows including cloaked / background virtual desktop windows
winpilot list --all

# Filter by regular expression on window title
winpilot list --filter "(?i)claude|cursor"

# Filter by process executable name
winpilot list --process "code.exe"
```

**Output Columns**:
- `HWND`: Decimal handle of the window.
- `PID`: Process identifier.
- `Process`: Executable name (e.g. `chrome.exe`).
- `Title`: Accessible title bar text.
- `Bounds`: `(left, top, right, bottom)` coordinate bounding rectangle.
- `Status`: Indicates whether the window is cloaked, minimized, or active.

---

### `winpilot inspect`
Inspect and print the live UI Automation accessibility hierarchy tree for a given application.

```powershell
# Inspect Claude Desktop tree up to depth 3
winpilot inspect "Claude" --depth 3

# Inspect by decimal HWND
winpilot inspect 198422 --depth 2

# Output raw JSON representation for script parsing
winpilot inspect "Claude" --depth 2 --json
```

---

### `winpilot focus`
Bring a window to the front, bypass the Windows foreground lockout, and uncloak if located on another virtual desktop.

```powershell
winpilot focus "Claude"
winpilot focus 198422
```

---

### `winpilot click`
Find an element matching a CSS-like selector query and click it.

```powershell
# Click a button with accessible name "Submit"
winpilot click "MyApp" "Button[Name='Submit']"

# Click a menu item matching a substring
winpilot click "Claude" "MenuItem[Name*='Sonnet']"

# Force physical mouse simulation instead of UIA InvokePattern
winpilot click "Paint" "Button[Name='Brush']" --physical
```

---

### `winpilot paste`
Bring the target window to the foreground and inject Unicode text via clipboard paste (`Ctrl+V`).

```powershell
# Paste text without submitting
winpilot paste "Notepad" "Hello from WinPilot CLI!"

# Paste text and immediately trigger Enter key
winpilot paste "Claude" "Explain how quantum entanglement works" --submit
```

---

### `winpilot screenshot`
Capture a screenshot of a specific window or the entire desktop display.

```powershell
# Screenshot specific application window
winpilot screenshot --window "Claude" --output "claude_screen.png"

# Screenshot entire virtual screen
winpilot screenshot --output "full_desktop.png"
```

---

### `winpilot recipe`
Run domain-specific application recipes.

```powershell
# Select a model in Claude Desktop
winpilot recipe claude-model --model "haiku"
winpilot recipe claude-model --model "sonnet"

# Send a prompt to Claude Desktop
winpilot recipe claude-prompt "Analyze repository structure"

# Send prompt without automatically pressing Enter
winpilot recipe claude-prompt "Hold on, do not submit yet" --no-submit
```

---

### `winpilot serve`
Launch the WinPilot FastMCP server for AI agent integration.

```powershell
# Standard I/O transport (for Claude Desktop, Cursor, and IDE extensions)
winpilot serve --transport stdio

# SSE / HTTP transport (for network agent calls)
winpilot serve --transport sse --port 8000
```
