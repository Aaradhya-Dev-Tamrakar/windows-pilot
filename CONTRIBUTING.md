# Contributing to WinPilot

Thank you for contributing to WinPilot! This project provides Windows desktop automation for AI agents and human operators, built on mission-critical safety tenets.

---

## 1. Development Environment Setup

WinPilot requires **Windows 10/11** and **Python 3.10+**.

```powershell
# Clone the repository
git clone https://github.com/AaradhyaDT/windows-pilot.git
cd windows-pilot

# Set up a virtual environment using uv (recommended) or standard venv
uv venv
.\.venv\Scripts\activate

# Install WinPilot in editable mode with development dependencies
uv pip install -e ".[dev]"
```

---

## 2. Adherence to Mission-Critical Directives

All code contributions must adhere to **The WinPilot Safety & Reliability Directives** documented in [`docs/SAFETY_DIRECTIVES.md`](docs/SAFETY_DIRECTIVES.md):

- **No Infinite Waits**: Every loop or synchronization call (`wait_for_*`, UIA search) must enforce a bounded timeout.
- **Pre-Dispatch Verification**: Before synthesizing hardware keystrokes or mouse clicks, assert that the target `HWND` is valid, uncloaked, and in the foreground.
- **Resource Reclamation**: Release GDI handles, DC contexts, and thread input attachments in `finally` blocks.
- **Zero Silent Failures**: Propagate typed errors rather than swallowing COM or Win32 exceptions.
- **Idempotent Inspection**: `inspect` and element queries must be pure read operations with zero side effects.

---

## 3. Code Standards & Linting

WinPilot enforces formatting and linting via **Ruff**:

```powershell
# Run Ruff lint check
.\.venv\Scripts\ruff.exe check .

# Automatically apply safe fixes
.\.venv\Scripts\ruff.exe check --fix .

# Format code
.\.venv\Scripts\ruff.exe format .
```

---

## 4. Testing Guidelines

Tests are automated using **Pytest**:

```powershell
# Run the test suite
.\.venv\Scripts\pytest.exe -v
```

- **Unit tests** must run offline and headlessly in CI without requiring live target applications running on the machine (see [`tests/test_cli.py`](tests/test_cli.py) and [`tests/test_query.py`](tests/test_query.py)).
- Live integration tests against real desktop apps should be placed in distinct, opt-in test fixtures or invoked manually.

---

## 5. Git Workflow & Conventional Commits

We follow Conventional Commits:
- `feat(scope)`: New functionality
- `fix(scope)`: Bug fixes
- `refactor(scope)`: Code restructuring without feature changes
- `test(scope)`: Adding or modifying test cases
- `docs(scope)`: Documentation improvements
- `chore(scope)`: Build system or configuration adjustments

You can also use the repository sync tool:
```powershell
.\sync.ps1 -Message "feat(core): enhance uncloaking verification"
```
