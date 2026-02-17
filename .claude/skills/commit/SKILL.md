---
name: commit
description: Analyzes changes and generates Conventional Commit messages
disable-model-invocation: true
allowed-tools: Read, Bash(git diff:*), Bash(git add:*), Bash(git commit:*), Bash(git status:*), Bash(git log:*), Bash(python3 .claude/skills/commit/scripts/format_files.py)
---

# Commit Changes

You are tasked with creating git commits for the changes made during this session.

## Process:

1. **Optimize imports in modified files**

2. **Think about what changed:**
   - Review the conversation history and understand what was accomplished
   - Run `git status` to see current changes
   - Run `git diff` to understand the modifications

3. **Plan your commit(s):**
   - Group into atomic commits by feature/fix/refactor, make sure that each element can be committed independently.
   - Identify which files belong together
   - Put model file (.stl and .3mf) changes into the same group as code changes for that model
   - Draft Conventional Commit messages (type: subject\n\nbody bullets)
   - Use imperative mood in commit messages
   - Subject line max 50 characters, body lines wrapped at 72 characters
   - Focus on why the changes were made, not just what

4. **Validate each commit message:**
   - Imperative mood ("add" not "added")
   - Subject line ≤ 50 characters
   - No trailing period
   - Type prefix not repeated in description (e.g. not "refactor: refactor...")
   - No capitalized first word after type prefix

5. **Present your plan to the user:**
   - Separate each commit with a unicode line: `━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━`
   - For each commit show:
     1. **Commit N**
     2. Commit message with only the type prefix in **bold** (e.g. **refactor**: description), no code block
     3. Number of files and lines changed, then file list with brief descriptions (use `format_files.py` — see below)
   - To format the file list:
     - Write JSON array of `[file, changes]` pairs to `.claude/skills/commit/scripts/input/input.json`
     - Run `python3 .claude/skills/commit/scripts/format_files.py` and paste the output as-is
   - End with: "I plan to create **N** commit(s) with these changes. Shall I proceed?"

6. **Execute upon confirmation:**
   - Use `git add` with specific files (never use `-A` or `.`)
   - Create commits with your planned messages
   - Show the result with `git log --oneline -n [number]`

## Important:
- **NEVER add co-author information or Claude attribution**
- Commits should be authored solely by the user
- Do not include any "Generated with Claude" messages
- Do not add "Co-Authored-By" lines
- Write commit messages as if the user wrote them

## Examples

Good commit messages:
- `feat: add marker holder model`
- `refactor: consolidate edge filtering logic in edgefilters module`
- `chore: update README with published models, add missing deps to requirements`
- `feat: add fillet radius reuse and arc support to Pencil`

Bad commit messages:
- `feat: added new marker holder model to the project` (past tense, verbose)
- `refactor: refactored edge filtering` (redundant — type already says refactor)
- `update stuff` (no type, vague)
- `fix: fix bug` (no useful information)
- `feat: add SmartBox.with_delta() class method and update all callers to use it` (too long, move details to body)

## Out of scope:
- Do NOT push to remote
- Do NOT amend existing commits
- Do NOT create or switch branches

## Remember:
- You have the full context of what was done in this session
- Group related changes together
- Keep commits focused and atomic when possible
- The user trusts your judgment - they asked you to commit
