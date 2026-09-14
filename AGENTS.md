# AGENTS.md — Repository Conventions for Autonomous & Agent Contributors

Welcome, Agent. This document establishes operating principles, execution constraints, and validation standards for autonomous coding agents contributing to `windows-pilot`.

---

## 1. Safety Directives Compliance (MANDATORY)

Before implementing features or modifying code, you **MUST** read and adhere to [**The WinPilot Safety & Reliability Directives**](docs/SAFETY_DIRECTIVES.md):

1. **Bounded Execution**: Never write infinite polling loops (`while True:`) without an explicit timeout and failure outcome.
2. **Pre-Dispatch State Verification**: Prior to sending physical input, verify target `HWND` validity, foreground focus, and uncloaked state.
3. **Fallback Escalation**: Follow the ladder: `UIATree Pattern` -> `Win32 Message` -> `Physical Simulation`.
4. **Guaranteed Cleanup**: Always clean up GDI/DC handles and thread input attachments in `finally` blocks.
5. **Zero Silent Failures**: Never suppress COM or Win32 errors with empty `except Exception: pass`.

---

## 2. Code Quality & Pre-Commit Gates

Before committing any modifications, you must ensure both linter and test suite pass with zero errors:

```powershell
# 1. Run Ruff Linter
.\.venv\Scripts\ruff.exe check .

# 2. Run Test Suite
.\.venv\Scripts\pytest.exe -v
```

If tests fail, diagnose and resolve the issue immediately. Never bypass test failures with `-SkipTests`.

---

## 3. Git Workflow & Automation

- **Minor / Routine Changes**: Execute `.\sync.ps1` without arguments. It automatically runs pytest verification, scans for secrets, and generates conventional commit messages (`feat`/`refactor`/`test`/`docs` + scope + churn stats).
- **Major Changes** (new primitives, recipe expansions, MCP tools): Execute `.\sync.ps1 -m "type(scope): detailed commit summary"` with a descriptive message to preserve clear historical context.
- **Secret Hygiene**: Staged diffs are automatically scanned for credentials prior to commit.

---

## 4. Documentation References

- Architecture Specification: [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md)
- MCP Guide: [`docs/MCP_GUIDE.md`](docs/MCP_GUIDE.md)
- CLI Reference: [`docs/CLI_REFERENCE.md`](docs/CLI_REFERENCE.md)
- Application Recipes: [`docs/RECIPES.md`](docs/RECIPES.md)
- Action Plan & Roadmap: [`docs/ACTION_PLAN.md`](docs/ACTION_PLAN.md)
