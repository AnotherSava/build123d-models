# File mapping — InverseCSG/tmp/ → build123d-models/

This is the concrete mapping. Source files are in `D:\projects\InverseCSG\tmp\` and `D:\projects\InverseCSG\tmp\diaframma\`. Destination is `D:\projects\3d\build123d-models\`.

## Code → `src/sava/csg/build123d/reconstruct/`

Module structure to create (rename + light refactor as part of the move):

| Source (InverseCSG/tmp/) | Destination | Notes |
|---|---|---|
| `analyze_iris_planes.py` | `src/sava/csg/build123d/reconstruct/planes.py` | Rename. Drop the OFF reader (move to `mesh_io.py`). Drop top-level CLI; expose `cluster_planes()` and `read_off()` as public functions. |
| `analyze_iris_planes.py` (read_off + STL) | `src/sava/csg/build123d/reconstruct/mesh_io.py` | New file. Move `read_off()` here. Add `read_stl()` adapted from `stl_to_off.py` (replace the OFF-writing step with a direct return). Unified entry point: `read_mesh(path)` that dispatches by extension. |
| `stl_to_off.py` | folded into `mesh_io.py::read_stl()` | The conversion step was an artifact of feeding InverseCSG's pipeline. Direct STL reading is simpler. |
| `plane_to_pencil.py` (boundary + simplify) | `src/sava/csg/build123d/reconstruct/boundary.py` | The `boundary_polygon()` + `simplify_collinear()` parts. |
| `plane_to_pencil.py` (Pencil emission) | `src/sava/csg/build123d/reconstruct/pencil_emit.py` | The `emit_pencil()`, `emit_plane()`, and `fmt()` parts. Or split `fmt()` into `numbers.py` if you prefer a tiny dedicated module. |
| `extrusion_view.py` (`classify_planes_vs_axis`, `pick_axis`) | `src/sava/csg/build123d/reconstruct/extrusion.py` | The classification + axis-pick logic. Per-loop cylinder detection lives in `api.py::_detect_circle` and runs during emit on every layer's loops. |
| `find_datum_and_repencil.py` (datum picking, frame construction) | `src/sava/csg/build123d/reconstruct/datum.py` | The `plane_line_in_xs()`, `pick_datum()`, frame-builder, origin-shift logic. |

Additionally create:

| New file | Purpose |
|---|---|
| `src/sava/csg/build123d/reconstruct/__init__.py` | Public API: `reconstruct(path) -> ReconstructionResult`, exports |
| `src/sava/csg/build123d/reconstruct/api.py` | The `ReconstructionResult` dataclass and the top-level `reconstruct()` function that orchestrates everything |
| `src/sava/csg/build123d/reconstruct/__main__.py` | CLI entry point: `python -m sava.csg.build123d.reconstruct <input.stl> --out <out.py>` |

## Render scripts → keep as `tmp/` exploration tools

The visualization scripts are research aids, not library code. Move them to `build123d-models/tmp/reconstruct_dev/` so they live alongside their data but stay out of the importable module:

| Source | Destination |
|---|---|
| `render_iris_planes.py` | `tmp/reconstruct_dev/render_planes_3d.py` |
| `render_pencil_2d.py` | `tmp/reconstruct_dev/render_pencil_2d.py` |
| `extrusion_view.py` (rendering parts) | `tmp/reconstruct_dev/render_cross_section.py` |
| `find_datum_and_repencil.py` (rendering parts) | `tmp/reconstruct_dev/render_datum_aligned.py` |

(The pure-logic parts of `extrusion_view.py` and `find_datum_and_repencil.py` go to the production module per the table above; the matplotlib bits stay in tmp.)

## Test data → `tests/sava/csg/build123d/reconstruct/data/`

| Source | Destination |
|---|---|
| `tmp/diaframma/obj_1.off` | `tests/sava/csg/build123d/reconstruct/data/iris_blade.off` |
| (original STL still in `build123d-models/tmp/diaframma/obj_1_Diaf 3.stl`) | Already there |
| `tmp/diaframma/datum_aligned/blade_datum_aligned.py` | `tests/sava/csg/build123d/reconstruct/data/expected_iris_blade.py` |
| `tmp/diaframma/planes_pencil.md` | `tests/sava/csg/build123d/reconstruct/data/expected_per_plane_pencil.md` |

## Visualizations → `docs/code/reconstruct/images/` or `tmp/reconstruct_dev/sample_outputs/`

Reference images from the iris-blade run. Useful as pedagogical material and visual regression references.

| Source | Destination |
|---|---|
| `tmp/diaframma/planes/00_overview.png` | `docs/code/reconstruct/images/planes_overview.png` |
| `tmp/diaframma/planes/01..10_plane.png` | `docs/code/reconstruct/images/plane_NN.png` |
| `tmp/diaframma/pencil_2d/01..09_pencil.png` | `docs/code/reconstruct/images/pencil_NN.png` |
| `tmp/diaframma/extrusion/cross_section_overlay.png` | `docs/code/reconstruct/images/cross_section_overlay.png` |
| `tmp/diaframma/datum_aligned/datum_aligned_overlay.png` | `docs/code/reconstruct/images/datum_aligned_overlay.png` |

(Pick `docs/code/reconstruct/` to match build123d-models' existing pattern of `docs/code/<topic>.md`.)

## Documentation → `docs/code/reconstruct/`

| Source (this transfer package) | Destination |
|---|---|
| `README.md` | `docs/code/reconstruct/README.md` (or the module's own README) |
| `ALGORITHM.md` | `docs/code/reconstruct/ALGORITHM.md` |
| `FINDINGS.md` | `docs/code/reconstruct/FINDINGS.md` |

## Files that do NOT move

Stay in InverseCSG (these are genuinely tied to the InverseCSG pipeline):

- `tmp/benchmark.py`
- `tmp/benchmark_results.txt`
- `tmp/diaframma/ransac.conf`
- `tmp/diaframma/run1/` (the actual InverseCSG pipeline run output — keep for reference)

## What to do with `tmp/stl_to_off.py`

Two options:
1. **Move it to build123d-models** as `tmp/reconstruct_dev/stl_to_off.py` for occasional use (e.g., if running the InverseCSG pipeline again on a new STL for cross-validation).
2. **Keep it in InverseCSG** since it's really an input adapter for that pipeline (which only reads OFF).

I'd lean toward (2) — keep it where it's used. The build123d-models reconstruction reads STL directly via `mesh_io.read_stl()`.

## Post-transfer cleanup

Once transfer is complete and tests pass in build123d-models:

```bash
# In InverseCSG repo
rm tmp/analyze_iris_planes.py
rm tmp/plane_to_pencil.py
rm tmp/render_iris_planes.py
rm tmp/render_pencil_2d.py
rm tmp/extrusion_view.py
rm tmp/find_datum_and_repencil.py
rm -r tmp/diaframma/planes
rm -r tmp/diaframma/pencil_2d
rm -r tmp/diaframma/extrusion
rm -r tmp/diaframma/datum_aligned
rm tmp/diaframma/planes_pencil.md
rm tmp/diaframma/obj_1.off   # only if you don't want a backup
```

Or simply `rm -r tmp/transfer tmp/diaframma/{planes,pencil_2d,extrusion,datum_aligned}` plus the scripts listed above.
