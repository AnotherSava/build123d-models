---
created: 2026-09-28 16:54:36
---

# Treat a leading-slash anchored gitignore line as a duplicate of its unslashed global twin in gitignore-scope-global

The project line `/.claude/settings.local.json` and the global excludes entry `.claude/settings.local.json` are the same rule: a leading slash and a mid-string slash both anchor a pattern to the repo root. The v2 rule `gitignore-scope-global` does not report it, because `same_rule()` keys on `normalise(entry)`, which strips only a leading `**/`, so the leading `/` makes the two bodies differ even though `floats()` answers False for both.

The fix belongs in the dotfiles repo, in `claude/conventions/rules/gitignore-scope-global.py` (strip a leading `/` from an anchored pattern before comparing bodies), and in its version README's definition of a duplicate. It is not this repo's to change. Once it ships, this repo's root `.gitignore` line `/.claude/settings.local.json` will be reported and should be deleted.

Found on 2026-09-28 during /adopt, raised by the scouting verifier for v2.
