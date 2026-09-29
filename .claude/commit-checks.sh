#!/usr/bin/env bash
# Project commit-checks, run by the /commit skill before it plans commits. This repo
# commits straight to main and has no CI, so nothing else reads a change on its way in.
# The conventions checker runs first: it re-measures every rule this repo has adopted,
# and nothing else runs it between /adopt walks. Then the fast base suite, then the
# slower model regression suite (kept out of the default `pytest tests/` run via the
# `regression` marker). All must pass; a non-zero exit blocks the commit plan.
# A pass does not cover lint: ruff runs per edited file from the PostToolUse hook,
# and import organization (F401/I001) is left to /clean-code, not checked here.
set -eu
root="$(git rev-parse --show-toplevel)"
cd "$root"
python3 ~/.claude/conventions/check.py .
venv/Scripts/python.exe -m pytest tests/ -q
venv/Scripts/python.exe -m pytest tests/ -m regression -q
