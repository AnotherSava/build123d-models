---
name: Use skill base directory from prompt header
description: When a skill prompt includes "Base directory for this skill:", go directly to that path instead of searching
type: feedback
---

When a skill is invoked, the prompt header includes `Base directory for this skill: <path>`. Use that path directly to find skill files (e.g. `SKILL.md`) instead of searching with find/glob through multiple directories.

**Why:** Wasted time and tokens doing broad filesystem searches when the exact path was already provided in the conversation context.

**How to apply:** Before searching for skill-related files, check the current conversation for the "Base directory for this skill" header and read files directly from that path.
