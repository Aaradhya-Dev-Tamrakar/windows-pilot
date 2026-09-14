# The WinPilot Safety & Reliability Directives
## Mission-Critical Desktop Automation Architecture

Desktop automation operates directly on live operating system state—synthesizing physical mouse movements, injecting hardware keystrokes, capturing screen buffers, and manipulating Win32 handles. Unlike isolated web or sandbox environments, unconstrained OS automation can cause runaway focus stealing, data corruption, or phantom keystrokes.

WinPilot adopts a **Mission-Critical / Fault-Tolerant Automation Architecture** adapted from Aerospace Fault Management (FM), industrial RPA safety frameworks (IEC 61508 / ISO 10218 adapted for software agents), and high-reliability systems engineering.

---

## The 10 Core Directives

### 1. The Bounded Execution Invariant (Deterministic Timeouts)
> **Directive**: *No operation may wait indefinitely for an external system state.*

- Every synchronization loop (`wait_for_window`, `wait_for_element`, UIA retry, process attachment) **MUST** accept an explicit `timeout` parameter with an enforced non-infinite default (e.g., 5.0 to 10.0 seconds).
- Polling intervals must use exponential backoff or bounded intervals with jitter rather than tight, CPU-burning loops.
- If a timeout expires, the operation must raise a descriptive `TimeoutError` or return an unambiguous failure result object; it must never block the calling thread permanently.

```python
# Compliant: Bounded poll with explicit deadline
def wait_for_element(window, query, timeout=5.0, poll_interval=0.25):
    deadline = time.time() + timeout
    while time.time() < deadline:
        elem = window.find_element(query)
        if elem:
            return elem
        time.sleep(poll_interval)
    raise TimeoutError(f"Element '{query}' not found within {timeout}s")
```

---

### 2. Pre-Dispatch State Invariant (Verification Before Side-Effects)
> **Directive**: *Never dispatch input into an unverified or unconfirmed target.*

- Prior to sending any hardware-level keystroke or mouse click, the system must assert:
  1. The target window handle (`HWND`) remains valid (`IsWindow(hwnd)` returns true).
  2. The window is not cloaked by the Desktop Window Manager (`DWMWA_CLOAKED == 0`).
  3. The target window is in the foreground (`GetForegroundWindow() == target_hwnd`).
- If focus has been stolen by an unexpected system dialogue or notification, the action must **immediately abort** rather than blindly sending input into the wrong process.

---

### 3. Hierarchical Fallback Ladder (Fault Escalation)
> **Directive**: *Prefer minimally invasive, non-disruptive interaction mechanisms before escalating to physical input simulation.*

Element interactions must follow a deterministic 3-tier escalation ladder:
1. **Tier 1 (Direct API / Accessible Pattern)**: `IUIAutomationInvokePattern::Invoke()`, `TogglePattern`, or `ValuePattern`. This executes silently in the background without moving the user's mouse cursor or stealing OS focus.
2. **Tier 2 (Window Message)**: Direct Win32 message dispatch (`SendMessage` / `PostMessage` with `WM_COMMAND`, `BM_CLICK`).
3. **Tier 3 (Physical Simulation)**: Hardware-level mouse click or `SendInput` keyboard injection. Used only when accessibility patterns are unsupported by the target application.

Each escalation step must be recorded in diagnostic telemetry.

---

### 4. Guaranteed Resource Reclamation (Zero-Leak Discipline)
> **Directive**: *Every operating system resource acquired must have a deterministic, guaranteed release.*

- Win32 Device Contexts (`GetDC`), GDI objects (`CreateCompatibleBitmap`), window thread attachments (`AttachThreadInput`), and COM interfaces must be managed within Python context managers (`__enter__` / `__exit__`) or protected by `try...finally` blocks.
- Thread input attachments (`AttachThreadInput`) must always detach even if an exception occurs during the foreground transition.

```python
# Compliant: Guaranteed detachment
attached = win32process.AttachThreadInput(cur_tid, target_tid, True)
try:
    win32gui.SetForegroundWindow(hwnd)
finally:
    if attached:
        win32process.AttachThreadInput(cur_tid, target_tid, False)
```

---

### 5. Fail-Safe Disarm Mechanism (Emergency Abort)
> **Directive**: *Autonomous agents and automated scripts must provide an immediate circuit breaker to halt execution.*

- Any executing `ActionChain` or background MCP task must be cancelable.
- Future GUI and CLI runners should support a fail-safe tripwire (such as moving the mouse to a screen corner or pressing an emergency abort key) that immediately clears queued input buffers and halts execution.

---

### 6. Zero Silent Failures (Explicit Error Telemetry)
> **Directive**: *Win32 API and COM HRESULT failures must never be suppressed or ignored.*

- Return values and system errors (`GetLastError()`) must be evaluated.
- Failure states must bubble up with rich diagnostic context (target `HWND`, process ID, process name, window title, selector query, and underlying OS error code).
- Suppressed exceptions (`except Exception: pass`) are strictly forbidden in input dispatch paths.

---

### 7. Pre-Flight Inspection & Dry-Run Decoupling
> **Directive**: *Read and inspection operations must have zero side-effects on system state.*

- Query resolution (`Query.find_one`, `winpilot inspect`, UIA hierarchy dump) must be completely idempotent and read-only.
- The system must provide agents the ability to preview matched elements, bounding coordinates, and enabled states before issuing state-modifying actions.

---

### 8. Input Sanitization & Clipboard Hygiene
> **Directive**: *Do not leave persistent or corrupted state in system-wide shared resources.*

- When using the clipboard injection technique (`Ctrl+V` paste) for high-speed multi-character typing:
  1. The target field must be verified as accepting text input.
  2. Large payloads must be checked against sane memory limits.
  3. When appropriate, preserve and restore previous clipboard contents to minimize disruption to the human operator.

---

### 9. Structured Flight Recorder (Deterministic Audit Logging)
> **Directive**: *Every automated side-effect must generate structured audit telemetry.*

- Dispatched commands, selector resolutions, and window state transitions should produce consistent structured logs:
  `[Timestamp] [Action] [Target HWND] [PID] [Selector] [Tier] [Status: SUCCESS|FAIL] [Duration ms]`
- This telemetry enables post-mortem failure analysis when an autonomous agent encounters an unexpected UI state.

---

### 10. Post-Condition State Assertion
> **Directive**: *An action is not complete until the post-interaction state is verified.*

- After clicking an element or submitting a form, verify that the state transition occurred (e.g. menu expanded, dialog appeared, text entered, or element dismissed).
- If the expected post-condition fails within the bounded timeout, trigger appropriate retry or recovery logic.

---

## Summary Table

| Directive | Core Principle | Primary Failure Prevented |
|---|---|---|
| 1. Bounded Execution | Strict timeouts on all waits | Indefinite hanging / thread lock |
| 2. Pre-Dispatch State | Assert HWND and foreground before typing | Typing sensitive text into wrong window |
| 3. Fallback Ladder | UIA Pattern → Win32 Message → Hardware | Unnecessary cursor disruption & fragile clicks |
| 4. Resource Reclamation | `finally` block handle release | GDI/DC leaks, thread input lockups |
| 5. Fail-Safe Disarm | Emergency abort mechanism | Runaway loop taking over user system |
| 6. Zero Silent Failures | Explicit HRESULT / error propagation | Invisible failures masking broken automations |
| 7. Pre-Flight Inspection | Pure read-only query verification | Accidental click during inspection |
| 8. Clipboard Hygiene | Safe string handling & clipboard safety | Corrupted user clipboard / dropped keystrokes |
| 9. Flight Recorder | Structured audit telemetry | Unexplained agent misclicks / impossible debugging |
| 10. Post-Condition Assertion | Verify expected outcome after dispatch | Premature continuation before UI is ready |
