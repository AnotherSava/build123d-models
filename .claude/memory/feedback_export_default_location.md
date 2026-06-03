---
name: Export to default location
description: When the user asks to export a model, always export to the project's default 3MF/STL location, not to tmp/
type: feedback
---
When the user asks to "export" a model (single or multi-part), save it to the project's default location: `models/current_model.3mf` for 3MF, `models/current_model/` for STL. This is what `save_3mf()` / `save_stl()` write by default when called with no `location` argument — just don't pass an explicit path.

**Why:** the user has `f3d models/current_model.3mf --watch --opacity=0.6` set up to auto-reload on changes (per CLAUDE.md). Writing to `tmp/foo.3mf` bypasses that viewer and forces them to re-launch f3d on each new path.

**How to apply:** for `save_3mf()` and `save_stl()` calls, omit the `location` argument unless the user explicitly asks for a different path. Applies to all export tasks — preview shots, debug visualizations, final geometry, multi-color part checks.
