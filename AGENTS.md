# AGENTS.md — Repository Conventions for Agent Contributors

## Git Workflow

- **Minor / Routine Changes**: Execute `.\sync.ps1` without arguments. It automatically runs pytest verification, scans for secrets, and generates conventional commit messages (`feat`/`refactor`/`test`/`docs` + scope + hunk context + churn stats) from the staged diff.
- **Major Changes** (new core primitives, recipe expansions, MCP server tools, CLI commands): Execute `.\sync.ps1 -m "type(scope): detailed commit summary"` with a descriptive message to preserve clear historical context.
- **Pre-Commit Verification**: The sync pipeline runs `pytest` automatically. Never bypass test failures with `-SkipTests` unless explicitly instructed.
- **Secret Hygiene**: Staged diffs are scanned for API keys, private keys, and tokens prior to commit. Offending secrets will abort the sync and reset staged changes.
