## Summary of Changes

A concise description of the changes introduced by this pull request.

## Motivation & Context

Why is this change required? What problem does it solve? If it fixes an issue, please link it here.

## Safety Directives Checklist

Please verify compliance with [The WinPilot Safety & Reliability Directives](docs/SAFETY_DIRECTIVES.md):

- [ ] **Bounded Execution**: All polling loops and synchronization calls have explicit, non-infinite timeouts.
- [ ] **Pre-Dispatch Verification**: Input actions assert target HWND validity, foreground state, and lack of cloaking.
- [ ] **Resource Reclamation**: Win32 handles (DC, GDI, ThreadInput) are safely released in `finally` blocks.
- [ ] **Zero Silent Failures**: COM/Win32 errors are checked and raised with context instead of ignored.
- [ ] **Tests Included**: Offline unit tests are added or updated under `tests/`.
- [ ] **Linter & Tests Pass**: `ruff check .` and `pytest` run cleanly.
