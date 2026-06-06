"""PostToolUse hook: lint the just-edited Python file with ruff.

Auto-fixes what it can (ruff check --fix); if violations remain, prints them to
stderr and exits 2 so Claude sees the report and corrects the code.
"""
import json
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
RUFF = PROJECT_ROOT / "venv" / "Scripts" / "ruff.exe"


def main() -> int:
    payload = json.load(sys.stdin)
    file_path = (payload.get("tool_input") or {}).get("file_path") or ""
    if not file_path.endswith(".py"):
        return 0
    try:  # only lint files inside this project
        Path(file_path).resolve().relative_to(PROJECT_ROOT)
    except ValueError:
        return 0
    result = subprocess.run([str(RUFF), "check", "--fix", file_path], capture_output=True, text=True)
    if result.returncode == 0:
        return 0
    sys.stderr.write(result.stdout + result.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
