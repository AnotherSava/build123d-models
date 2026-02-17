#!/usr/bin/env python3
"""Format file-changes pairs as aligned inline-code markdown.

Reads JSON from input/input.json (relative to this script).
Write the input file first, then run this script. The input file is deleted after use.

Input format: [["src/foo/bar.py", "Add helper"], ["src/baz.py", "Fix bug"]]

Output:
    `src/foo/bar.py`   Add helper
    `src/baz.py`       Fix bug
"""
import json
from pathlib import Path


def format_files(pairs: list[list[str]]) -> str:
    max_len = max(len(f"`{f}`") for f, _ in pairs)
    lines = []
    for file, changes in pairs:
        name = f"`{file}`"
        lines.append(f"{name:<{max_len}}   {changes}")
    return "\n".join(lines)


if __name__ == "__main__":
    input_file = Path(__file__).parent / "input" / "input.json"
    pairs = json.loads(input_file.read_text())
    input_file.unlink()
    print(format_files(pairs))
