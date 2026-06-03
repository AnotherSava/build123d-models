---
name: arrange-scene-pattern
description: "Multi-part export: assembled 3MF scene FIRST, then clear(), then STL (which applies bed_orientation)"
metadata:
  node_type: memory
  type: reference
---

For models with multiple parts shown both as an assembled 3MF visualization AND as slicer-ready STLs. See [[feedback-visualization-orientation]] for the why.

1. `create_*()` methods return parts in **scene (visualization) orientation** — not print orientation.
2. Arrange the parts into their assembled positions (`.align(...)`, `.move(...)`) and `export(...)` + `save_3mf(path, current=True)` **first** — this is the visualization scene, with colors. `show_red`/`show_green`/`show_blue` overlays land correctly here because parts are in scene pose.
3. Call `exporter.clear()` to reset the module-level `_shapes` dict.
4. `export(...)` the parts in their print layout and `save_stl(path)`. STL export applies each part's `SmartSolid.bed_orientation` (a rotation vector, default `None`) via `get_solid(apply_bed_orientation=True)` — so a part can sit one way in the scene and print flipped flat on the bed, without ever rotating it in the model code.

**Why the clear() step matters:** `save_3mf` does NOT clear `_shapes` afterward, and `export()` appends. Without `clear()` between the 3MF and STL passes, shapes get duplicated.

**Correct examples:** `src/sava/csg/build123d/models/hydroponics/tray.py` and `splitter.py` (`export_all`). NOTE: `cablechannel.py` still uses an older print-orientation + STL-first pattern and is the counter-example to avoid.
