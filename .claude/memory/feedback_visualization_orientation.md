---
name: feedback-visualization-orientation
description: "Build models in scene/visualization orientation, NOT print orientation; use SmartSolid.bed_orientation for print"
metadata: 
  node_type: memory
  type: feedback
---

Models (and each `create_*` method) must be built in **scene (visualization) orientation** — how parts sit relative to each other in the assembled model. Do NOT build in print orientation. When a part prints better in a different pose, set `SmartSolid.bed_orientation` (a rotation vector); export applies it **only for STL**, never for the 3MF scene.

This reverses earlier guidance I gave in another session (the "build in print orientation" CLAUDE.md note, commit 862e22d) — the user said that was "completely wrong."

**Why:** scene orientation makes the assembled 3MF read correctly and makes the `show_red` / `show_green` / `show_blue` debug overlays land where expected. It's also why the export flow exports the assembled scene as 3MF first, then `clear()`s, then re-exports as STL (where `bed_orientation` is applied). See [[arrange-scene-pattern]] for the export-flow mechanics.

**How to apply:** when writing/reviewing any model `create_*` method or its export, keep geometry in scene pose; reach for `bed_orientation` (not `rotate_x`/`move` in the model code) to fix print pose. Don't reintroduce print-orientation-first guidance. `cablechannel.py` still uses the old pattern and should be migrated if touched.
