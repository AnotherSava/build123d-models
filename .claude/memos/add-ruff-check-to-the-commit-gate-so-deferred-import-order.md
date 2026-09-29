---
created: 2026-09-28 17:23:57
---

# Add ruff check to the commit gate so deferred import-order violations cannot reach main

`.claude/commit-checks.sh` runs the conventions checker and both pytest suites, but no lint. The PostToolUse hook (`.claude/hooks/ruff_check.py`) auto-fixes each edited file except import organization (F401 unused, I001 sorting), which is deferred to commit time via /clean-code — so nothing enforces those rules if /clean-code is skipped. Candidate line: `venv/Scripts/ruff.exe check .` (config in `ruff.toml`); the baseline was clean on 2026-09-28 ("All checks passed!"). When added, drop the header line saying a pass does not cover lint.

Raised during /adopt v9 (commit-gate) on 2026-09-28.
