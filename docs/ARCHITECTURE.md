# WinPilot Architecture Specification

WinPilot is engineered as a decoupled, multi-layered desktop automation framework designed for dual consumption by autonomous **AI / coding agents** (via Model Context Protocol and Python SDK) and **human operators** (via CLI and future GUI builders).

---

## High-Level Topology

```
┌─────────────────────────────────────────────────────────────┐
│                      CONSUMER INTERFACES                    │
│   ┌──────────────┐   ┌──────────────┐   ┌───────────────┐   │
│   │  FastMCP     │   │  Rich CLI    │   │  Python SDK   │   │
│   │  Server      │   │  winpilot    │   │  import       │   │
│   │  (stdio/SSE) │   │  command     │   │  winpilot     │   │
│   └──────┬───────┘   └──────┬───────┘   └───────┬───────┘   │
├──────────┴──────────────────┴───────────────────┴───────────┤
│                      COMPOSITION LAYER                      │
│   - CSS-like Element Query DSL (Query.find_one, Selector)   │
│   - Synchronization & Polling Primitives (wait_for_*)       │
│   - Fluent Action Chains (ActionChain builder)              │
├─────────────────────────────────────────────────────────────┤
│                      APPLICATION RECIPES                    │
│   - BaseRecipe lifecycle & post-condition verification      │
│   - ClaudeDesktopRecipe (model selector, chat, prompt)      │
│   - Common Dialogs & Window Framing                         │
├─────────────────────────────────────────────────────────────┤
│                         CORE ENGINE                         │
│   ┌──────────────┐   ┌──────────────┐   ┌───────────────┐   │
│   │ Window HWND  │   │ UIA Tree &   │   │ Input &       │   │
│   │ Manager      │   │ Elements     │   │ Clipboard     │   │
│   │ (Win32/DWM)  │   │ (COM/UIA)    │   │ (SendInput)   │   │
│   └──────────────┘   └──────────────┘   └───────────────┘   │
│   ┌─────────────────────────────────────────────────────┐   │
│   │ Screen Capture (GDI / base64 image serialization)   │   │
│   └─────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

---

## 1. Core Engine (`winpilot/core/`)

The Core Engine provides direct, low-level abstractions over Windows OS subsystems without intermediate UI automation wrappers.

### `window.py` — Win32 Window & Focus Management
- **Desktop Enumeration**: Uses `EnumDesktopWindows` over `WinSta0\Default`. Avoids `ERROR_BUSY (170)` typically encountered with naive `EnumWindows` calls when background services or lock screens are active.
- **Foreground Lockout Bypass**: Windows prevents background processes from calling `SetForegroundWindow` without active user focus (often resulting in flashing orange taskbar buttons). WinPilot overcomes this restriction by:
  1. Retrieving the thread ID of the current foreground window (`GetWindowThreadProcessId`).
  2. Attaching the current thread to the target thread via `AttachThreadInput(cur_tid, target_tid, True)`.
  3. Granting foreground activation permissions via `AllowSetForegroundWindow(ASFW_ANY)`.
  4. Detaching input threads in a guaranteed `finally` block.
- **DWM Cloaking & Virtual Desktop Awareness**: Windows on secondary virtual desktops or suspended UWP states are marked by the Desktop Window Manager with `DWMWA_CLOAKED = 14`. WinPilot checks `DwmGetWindowAttribute` to detect cloaked windows, alerting callers or triggering uncloaking sequences before attempting interaction.

### `uia.py` — UI Automation Tree & Pattern Walker
- Interacts with the Microsoft UI Automation COM subsystem (leveraging `pywinauto.uia_element_info.UIAElementInfo`).
- Wraps raw COM objects inside a clean, typed `UIElement` abstraction.
- **Pattern Execution Hierarchy**: Inspects element capabilities dynamically:
  - `InvokePattern`: Direct trigger for buttons, links, and items.
  - `TogglePattern`: State manipulation for checkboxes and toggles.
  - `SelectionItemPattern`: Selection for tabs, tree items, and dropdown choices.
  - Fallback to bounding box center calculation and physical click simulation if pattern execution is unavailable.

### `input.py` — Hardware Input & Unicode Clipboard Injection
- **Physical Keystrokes**: Synthesizes key down/up events using Win32 `SendInput` with virtual key codes (`VK_*`).
- **Unicode Clipboard Injection (`paste_text`)**: Direct typing of multi-kilobyte strings via keystroke simulation is notoriously slow and susceptible to character dropping or modifier key leakage. WinPilot instead:
  1. Backs up the current clipboard state.
  2. Places Unicode text onto the Windows clipboard (`CF_UNICODETEXT`).
  3. Dispatches a hardware `Ctrl+V` key combination.
  4. Optionally dispatches `VK_RETURN` to submit.

### `screen.py` — Visual Multimodal Capture
- Captures pixel buffers from window bounding rectangles (`PrintWindow` or GDI screen DC copy via `BitBlt`).
- Encodes visual output to PNG buffers and base64 strings, tailored for ingestion by multimodal AI models (Claude 3.7 Sonnet, GPT-4o, Gemini 2.0).

---

## 2. Composition Layer (`winpilot/compose/`)

The Composition layer orchestrates individual core primitives into high-level workflows.

### `query.py` — CSS-Style UIA Query DSL
Provides a human-readable selector syntax for UI elements:
```css
Button[Name="Submit"]
MenuItem[Name*="Haiku" i]#menu-item-1.menu-btn
Edit[AutomationId="PromptInput"]
```
- **Control Types**: Matches against standard UIA control types (`Button`, `Edit`, `MenuItem`, `Tab`, `Window`, `Text`).
- **Attribute Matching**:
  - `=` Exact match
  - `*=` Substring contains
  - `^=` Starts with
  - `$=` Ends with
- **Identifiers**: `#automation_id` matches `AutomationId`, `.class_name` matches `ClassName`.

### `wait.py` — Bounded Polling Primitives
Adheres to Directive 1 of the Safety Directives:
- `wait_for_window(title_regex, timeout=5.0, poll_interval=0.25)`
- `wait_for_element(window, query, timeout=5.0, poll_interval=0.25)`
- `wait_until_gone(window, query, timeout=5.0)`

### `actions.py` — Fluent `ActionChain` Builder
Chains complex user journeys into readable, self-documenting scripts:
```python
ActionChain(window)
    .focus()
    .wait_for("Edit[AutomationId='chat-input']")
    .click("Edit[AutomationId='chat-input']")
    .paste("Refactor this module", submit_enter=True)
    .execute()
```

---

## 3. Application Recipes (`winpilot/recipes/`)

Application Recipes encode pre-configured domain workflows for specific desktop applications.

- `base.py`: Defines the `BaseRecipe` interface, mandating window resolution, health checks, and execution status objects.
- `claude_desktop.py`: Provides automated navigation for the Claude Desktop client:
  - Switching active models (`haiku`, `sonnet`, `opus`).
  - Triggering new chats (`Ctrl+N`).
  - Injecting prompts and detecting rate-limit cooldown notices.

---

## 4. Consumer Interfaces

1. **MCP Server (`winpilot/mcp_server.py`)**: Built on FastMCP, exposing 8 tools via standard I/O for AI coding agents.
2. **CLI (`winpilot/cli.py`)**: Rich-formatted command line interface for interactive inspection and automation.
3. **Python SDK**: Native `import winpilot` for developers embedding desktop automation in custom tools.
