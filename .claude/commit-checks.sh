#!/usr/bin/env bash
# Project commit-checks, run by the /commit skill before it plans commits.
# Fast base suite first, then the slower model regression suite (kept out of the
# default `pytest tests/` run via the `regression` marker). Both must pass; a
# non-zero exit blocks the commit plan.
set -eu
root="$(git rev-parse --show-toplevel)"
cd "$root"
venv/Scripts/python.exe -m pytest tests/ -q
venv/Scripts/python.exe -m pytest tests/ -m regression -q
