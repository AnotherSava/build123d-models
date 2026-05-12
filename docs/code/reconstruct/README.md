# `sava.csg.build123d.reconstruct` — parametric reconstruction from mesh

Convert a triangle mesh (STL, OFF) into authored build123d code: Pencil sketches extruded along a detected axis, plus cylindrical primitives where appropriate.

## Scope

Handles **2.5D-extrudable parts** — anything whose surface decomposes into a small number of stacked planar caps perpendicular to one axis, with side walls parallel to that axis. This covers most sheet-metal-style, plate-style, and blade-style CAD parts. It does **not** handle:

- Sculpted / true 3D surfaces (lofts between non-similar profiles, free-form)
- Multi-axis cylindrical features
- Parts with no dominant flat reference

When the input fails the 2.5D check, the algorithm aborts and reports why. The intent is to be a **fast path for the common case**, not a universal mesh-to-CAD converter.

## Public API

```python
from sava.csg.build123d.reconstruct import reconstruct, ReconstructionResult

result: ReconstructionResult = reconstruct('path/to/iris_blade.off')

# result.is_2d5_extrudable: bool — was the part 2.5D?
# result.extrusion_axis: Vector
# result.x_dir / y_dir / z_dir / origin: Vector — datum-aligned local frame
# result.datum_plane: PlaneCluster
# result.layers: list[Layer] — silhouettes + depths + names ('front'/'back'/'recess'/'pivot_tip')
# result.cylinders: list[CylinderFeature] — axis: Vector, radius / height / area: float
# result.code: str — clean Pencil + build123d source that reproduces the body
# result.error: str | None — reason if is_2d5_extrudable is False
```

A CLI is provided for one-shot use:
```bash
python -m sava.csg.build123d.reconstruct path/to/blade.stl --out reconstructed_blade.py
```

## Files

| File | Purpose |
|---|---|
| `api.py` | `reconstruct()` orchestrator + `ReconstructionResult`/`Layer`/`CylinderFeature` dataclasses |
| `mesh_io.py` | Read OFF/STL → `(vertices, faces)` |
| `planes.py` | Cluster mesh triangles into coplanar groups |
| `boundary.py` | Walk boundary edges of a plane → ordered polygon, simplify collinear |
| `extrusion.py` | Pick extrusion axis, classify caps/side-walls, detect cylinders |
| `datum.py` | Choose datum plane, build local frame, shift origin to 1st quadrant |
| `pencil_emit.py` | Emit Pencil polygon-walks with `fmt()`-cleaned numbers |
| `numbers.py` | `fmt()` helper for readable numeric literals |

## See also

- `ALGORITHM.md` — step-by-step procedure with rationale
- `FINDINGS.md` — research log: what the iris blade actually is, validations, gotchas
- `tests/` — fixtures (iris blade STL) and end-to-end smoke tests

## Status

Research-stage. Iterating on the algorithm and accumulating test cases.
