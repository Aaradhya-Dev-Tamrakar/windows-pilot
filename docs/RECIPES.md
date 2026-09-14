# Application Recipes Guide

WinPilot Application Recipes package end-to-end automation workflows for specific desktop software. Recipes eliminate boilerplate element traversal, coordinate math, and retry logic by providing clean, high-level Python methods.

---

## 1. Anatomy of a Recipe

All recipes inherit from `BaseRecipe` located in [`winpilot/recipes/base.py`](../winpilot/recipes/base.py):

```python
from winpilot.core.window import Window, find_window
from winpilot.recipes.base import BaseRecipe

class CustomAppRecipe(BaseRecipe):
    name = "custom_app"
    description = "Automation workflows for CustomApp"

    def __init__(self, target: str = "CustomApp"):
        super().__init__(target)

    def is_running(self) -> bool:
        """Check whether target application window exists."""
        w = self._resolve_window()
        return w is not None and w.is_valid
```

### Safety Principles in Recipes
1. **Window Resolution**: Always resolve the target window lazily or refresh the `HWND` before executing multi-step chains.
2. **State Verification**: Confirm that prerequisite UI elements (e.g. popovers, dialogs, inputs) are visible before dispatching input.
3. **Structured Returns**: Methods return a status dictionary with `{"success": bool, "message": str}` or `{"success": False, "error": str}`.

---

## 2. Built-In: Claude Desktop Recipe

Located in [`winpilot/recipes/claude_desktop.py`](../winpilot/recipes/claude_desktop.py), `ClaudeDesktopRecipe` enables full autonomous control over the official Anthropic Claude Desktop client on Windows.

### Python SDK Usage

```python
from winpilot.recipes.claude_desktop import ClaudeDesktopRecipe

recipe = ClaudeDesktopRecipe("Claude")

# 1. Switch active reasoning / generation model
res = recipe.set_model("Haiku 4.5")
if res["success"]:
    print(f"Model updated: {res['message']}")

# 2. Trigger new conversation
recipe.new_chat()

# 3. Inject prompt text and submit
recipe.send_prompt(
    prompt="Explain the difference between preemptive and cooperative multitasking.",
    submit=True
)

# 4. Check for active 5-hour rate limits
cooldown = recipe.detect_cooldown()
if cooldown["in_cooldown"]:
    print(f"Claude rate limit active: {cooldown['reason']}")
```

### Recipe Capabilities

| Method | Parameters | Action |
|---|---|---|
| `set_model(model_name)` | `model_name`: `"haiku"`, `"sonnet"`, `"opus"` | Opens model selector dropdown, iterates choices, and clicks matching model |
| `send_prompt(prompt, submit)` | `prompt`: string, `submit`: bool | Focuses prompt field, writes Unicode text via clipboard injection, optionally sends Enter |
| `new_chat()` | None | Dispatches `Ctrl+N` shortcut to start a fresh chat thread |
| `detect_cooldown()` | None | Inspects text elements for hourly rate-limiting warnings |

---

## 3. Creating a New Recipe

To contribute a new application recipe to WinPilot:

1. Create a new module under `winpilot/recipes/<app_name>.py`.
2. Subclass `BaseRecipe` and define the relevant actions.
3. Use the CSS query DSL (`Query.find_one`) and bounded waits (`wait_for_element`) to navigate the application UI.
4. Expose the recipe in `winpilot/recipes/__init__.py`.
5. Register corresponding CLI shortcuts in `winpilot/cli.py` under the `recipe` group.
