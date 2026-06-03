---
name: Single-line constructors preferred in emitted code
description: When emitting code (reconstruct module, generators), keep constructor calls on a single line even when long
type: feedback
---
When emitting generated Python (e.g. `sava.csg.build123d.reconstruct` output), prefer single-line constructor calls — even when they're wide — over multi-line argument formatting. Same rule for hand-written code.

**Why:** the user explicitly asks for this. Aligns with the global style guideline ("Prefer single-line expressions over multi-line formatting, even if they're long; exception: multi-line acceptable for constructors with all named parameters"). Multi-line `Plane(\n    origin=...,\n    x_dir=...,\n    z_dir=...,\n)` reads as bureaucratic next to a one-liner.

**How to apply:** in `pencil_emit.py` / `api.py::_emit_code` and similar generators, build constructor argument strings with `f'Plane(origin=..., x_dir=..., z_dir=...)'` rather than multi-line `code.append` blocks. Don't worry about line length.
