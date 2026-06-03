---
name: Iris diaphragm — mesh-reconstruction-driven rewrite
description: Iris blade approach uses the project's reconstruct module to derive parametric Pencil code directly from the reference STL/OFF
type: project
---
## Goal

Add an iris diaphragm to the dispenser bottle mount (dispenserbottlemount.py) so rotating two rings changes the aperture size to grip pipes/bottles of varying diameters (25-35mm). The iris replaces the fixed central hole.

## Approach (Updated 2026-05-11)

InverseCSG approach is **superseded**. The chosen path is the project's own `sava.csg.build123d.reconstruct` module (added 2026-05-11): it converts the iris-blade STL/OFF directly into parametric Pencil + build123d code. The canonical reconstruction of the blade is checked in at `tests/sava/csg/build123d/reconstruct/data/expected_iris_blade.py`.

The InverseCSG analysis below is preserved for historical context (mesh structure, primitive list, SCAD round-trip validation) but is no longer the path being executed.

## Status (as of 2026-05-11, this session)

`iris.py` rewritten: `create_blade()` uses reconstructed Pencil-extruded geometry with three stacked layers (back protrusion, body, pivot pin), all built in default Plane.XY then translated to `(pcd_radius, 0)`. Mirrors the reconstruct module's emit format directly — no polygon-tuple indirection.

Reconstruct module improvements this session (in `src/sava/csg/build123d/reconstruct/`):
- Layer classification by depth-vs-body-z-range: `back_protrusion` / `front_protrusion` / `pocket` (replaces old `recess` / `pivot_tip`).
- `CylinderFeature.base` field (centroid of base face in cross-section local coords).
- Emit anchors cross-section origin on the vertex shared by the most emit-eligible polygons (`find_shared_start`); both Pencils drop `start=`.
- Pencil emit uses `Pencil()` (default Plane.XY) + a single final cross-section transform; `SmarterCone.cylinder(r, h).move(u, v, z)` for pins; `.fuse()` / `.cut()` instead of `+` / `-`.
- Angle convention bug fixed (`atan2(-dx, dy)` → CCW-from-+Y for `Pencil.draw`).
- Polygon winding bug fixed (CW polygons reversed so `+h` extrudes in `+z_dir`).
- Nice-angle heuristic (multiples of 15°) → `draw`; otherwise `jump((dx, dy))`.
- Param-less axis snap (e.g. `down()`) when a stroke lands on local x=0 / y=0.

Next step: integrate the finished blade into `dispenserbottlemount.py` for the bottle-grip mechanism (rotating two rings changes aperture for 25–35 mm pipes/bottles).

## Iris Ring (obj_8) Reconstruction (2026-05-12, this session)

`obj_8_Diaf 1.stl` reconstructed at **98.9% volume match** (16039 / 16213 mm³) as a single connected solid — outer 91.6 mm gear-tooth ring, central Φ41 round through-hole, 6 radial pivot pockets at z=1.5, annular rim on top.

Reconstruct module extensions (commits 02917f9, 18330ca, 0382209 on iris-diaphragm branch):
- **Multi-loop caps**: `boundary_polygons()` walks every disjoint boundary loop on a cap, not just one. Each cap returns `list[list[Vec]]`.
- **Recursive nested-loop emit** alternating fuse/cut by depth parity: outer=solid, hole=cut, island=fuse, hole-in-island=cut, ... Names are hierarchical (`body_hole_0_island_0`).
- **Sub-mm step filter** (`_filter_noise_step_loops`): groups boundary loops by 2D shape + centroid; if a group's plane-offset spread is below 0.1 mm, all members are dropped as sliver-wall artifacts (top/bottom of a noise step inside an otherwise flat cap). obj_8's cap[0] had 6 loops → 2 after filter (just the outer octagon + central Φ41 hole).
- **No-datum fallback**: circular parts (no flat side wall) use the provisional ex0/ey0 frame instead of crashing in `pick_datum()` — the in-plane rotation is arbitrary for rotationally-symmetric parts and any orthonormal frame is equally valid.
- Final cross-section transform now handles `blade.solid` being a `ShapeList` (when boolean ops leave disconnected pieces — relevant when through-hole assumptions are wrong).

**STL preprocessing tool survey**: no commonly-used tool (MeshLab/PyMeshLab/trimesh/MeshFix/Blender) targets sub-mm coplanar step cleanup specifically. Generic "merge close vertices" is too blunt — risks erasing legitimate sub-mm features. The fix lives in our reconstruct pipeline, not upstream — don't re-survey next session.

Open issues for the next pass:
- `simplify_collinear` collapses tessellated arcs into chords (perp_tol=0.05 mm vs sub-tolerance sagitta on tight circles). The outer octagonal outline still comes out chord-flattened. Would need arc detection (emit `Pencil.arc(...)` for runs of constant radius from a common center) or a Douglas–Peucker-style algorithm.
- Front/back loop matching for through-hole vs surface-recess discrimination — not needed for obj_8 (the only inner loop on cap[0] was Φ41, a true through-hole) but will matter for other parts.

## Approach (Updated 2026-05-10 — superseded)

Earlier attempts at hand-reverse-engineering the reference STLs into build123d code failed ("without much success" per user). New approach: use **InverseCSG** to auto-convert each reference STL into OpenSCAD primitives, then translate those into parametric build123d code.

User intent: keep `e4afac5` (iris blade dataclass + create_blade structure) but replace its implementation with the SCAD-derived geometry. All commits between `e4afac5` and HEAD were dropped as "failed attempts" at the sliding-blade mechanism.

Reset on 2026-05-10: branch reset from `00e1bec` to `e4afac5`. The dropped commits are preserved at tag `iris-sliding-attempt`.

## Reference STL Pipeline

1. Reference STL extracted to `D:/projects/InverseCSG/tmp/diaframma/`:
   - `obj_1.off` ... `obj_8.off` (6 blades, 2 rings)
2. InverseCSG output per part: `D:/projects/InverseCSG/tmp/diaframma/run1/`
   - `csg/solution_0.scad` — combined SCAD with bbox intersection
   - `csg/csg_0_0.scad` — inner CSG without bbox
   - `points/final_primitives.prim` — clean primitive list (planes + cylinders + bounding sphere)

## Blade Analysis (from `obj_1.off` + InverseCSG primitives)

**Reference blade bbox:** 18.9 × 17.5 × 26.5 mm

**Structure** (from mesh vertex inspection):
- Body slab Z=0 to ~3.5 mm (154/162 vertices). Tilted parallelepiped — bottom and top faces are inclined, not flat. Cross-section at Z=0 clusters at the (-X, -Y) corner of the bbox; at Z=0.5 it clusters at (+X, -Y). So the body is a twisted/tilted slab, not a horizontal one.
- Pin Z=3.5 to 26.5 mm, ~3.5 mm square (octagonal) cross-section, prismatic. Very few vertices — clean prism.
- Two tiny features at Z=6.5 and Z=8.5 (the "structural extensions" from earlier notes).

**InverseCSG primitives** (in local frame after rotating +47° around Z and translating to bbox center):
- 9 planes form polyhedron faces:
  - 3 X-cuts (normal +X, signed dist from origin: -1.36, +1.64, +5.64)
  - 2 Y-cuts (normal +Y, signed dist: -11.10, +0.75)
  - 1 Z-floor (normal +Z, dist -13.25)
  - 3 tilted around X axis (normal in +Y/Z, z-tilts -30°, -38.8°, +60°) — these form the body's sloped top transitions
- 3 cylinders:
  - cyl 0: r=1.82, horizontal axis along +X, at body height. Edge round on body.
  - cyl 1: r=0.90, horizontal axis along +Y, near origin. Another edge round.
  - cyl 2: r=5.98, tilted -60° down, passes near body. Curved sweep face.
- 1 sphere at origin r=653 — irrelevant bounding sphere

## SCAD Round-Trip Validation

Rendering `solution_0.scad` via OpenSCAD CLI (`C:/Program Files/OpenSCAD/openscad.exe`) produces an STL with bbox 19.38 × 17.30 × 29.67 mm. The Z is 3.17 mm taller than the reference OFF mesh (26.50 mm) because the SCAD wraps the inner CSG in a bbox cube intersection that's 31.80 mm tall — OpenSCAD respects that as the upper bound. The actual blade fills only 26.5 mm.

So **for accurate dimensions, use the OFF mesh bbox (26.5 mm), not the SCAD-rendered STL bbox (29.67 mm)**.

## Current Implementation State (after 2026-05-10 reset)

`src/sava/csg/build123d/models/other/iris.py` — replaced (commit not yet made). Now contains:
- `IrisDimensions` dataclass: `body_length` 18.9, `body_width` 17.5, `body_height` 3.6, `pin_diameter` 3.5, `pin_height` 22.9. Defaults reproduce reference bbox.
- `create_blade(dim)` — simple slab body + cylinder pin. Body bottom at Z=0, pin extends to Z=26.5.

This is **first-pass simplified geometry** — body is a flat slab (not the actual tilted parallelepiped), pin is a circular cylinder (not octagonal). User chose "Body only, pin parameterized" for fidelity level, so the body slope/tilt is a TODO refinement.

`tests/sava/csg/build123d/models/other/test_iris.py` — replaced with bbox/dimension tests, 10 tests passing.

## Analysis Scripts (`tmp/`)

- `iris_scad_analyze.py` — renders SCAD via OpenSCAD, prints raw primitive params, compares bbox
- `iris_scad_local_frame.py` — transforms primitives into local blade frame (rotated +47° around Z)
- `iris_offmesh_inspect.py` — inspects OFF mesh: Z distribution, XY footprint per slab
- `iris_blade_compare.py` — exports parametric blade, compares bbox to SCAD-rendered reference

## Preserved Artifacts

- Tag `iris-sliding-attempt` — points at the dropped 00e1bec (12 commits of failed sliding-mechanism attempt)
- `tmp/iris_reference/`, `tmp/iris_standalone/` — moved from `models/other/` before reset (visualization artifacts + earlier standalone export)
- `tmp/iris_scad_render/solution_0.stl` — OpenSCAD render of the InverseCSG output (for visual comparison)

## Next Steps

1. Visually verify the parametric blade matches reference proportions in F3D (`f3d tmp/iris_scad_render/blade_parametric.stl tmp/iris_scad_render/solution_0.stl`)
2. Refine body geometry: add the tilt/slope (loft between rotated cross-sections, or chamfered top edges from the 3 tilted planes)
3. User to provide InverseCSG SCAD output for the 2 rings (`obj_7`, `obj_8`)
4. Translate rings similarly
5. Integrate into `dispenserbottlemount.py` for the bottle-grip mechanism

## Reconstruct + Iris Expansion (2026-05-12, later in this session)

Reconstruct module additions:
- Cylinder detection generalized: runs per-loop on every layer (not just `front_protrusion`) via area-ratio test (polygon area within 5% of π·r̄²). Handles real STL cylinders that pick up flat chord sections at CSG boolean intersections — radial deviation balloons to ~17% there even though the area still matches a circle within 1%.
- Box detection (`_detect_box`): OBB fill ratio ≥ 95% AND ≥3 interior corners within 6° of 90°. Emits `SmartBox(L, W, h).rotate_z(angle).move(cu, cv, shift_z)`.
- Duplicate detection: depth-0 leaf outers with matching canonical signature (`('cylinder', r)` / `('box', L, W)` / `('polygon', sorted_canonical_vertices)`) collapse into a single template + placement-list `for` loop. Polygon canonical form: centroid-translated to origin + PCA-rotated to align principal axis with +X.
- Polar-pattern detection (`_detect_polar_pattern`): N-fold rotational symmetry collapses further into `template + Axis pivot + for i in range(N): rotate(pivot, i*step)`. Tests positions on a common circle + uniform 360°/N angular spacing + primitive rotations advancing by the same step modulo self-symmetry period (180° for SmartBox, 360° for chiral polygons, skipped for cylinders).
- obj_8 emit shrank 1102 → 83 lines (92% reduction).

`SmartSolid.rotate` bugs fixed (separate commit, see `~/.claude/learnings/build123d-smartbox-orient-gotcha.md`):
- `geometry.rotate_axis` was treating direction vectors as positions inside `rotate_vector` (translated by axis position). Off-origin axes corrupted directions. Fixed by using a direction-only axis.
- `SmartSolid.rotate` arbitrary-axis branch had the same bug + an orient+delta pattern that only works for axes through world origin. Rewritten to apply `gp_Trsf.SetRotation` directly for off-origin axes.
- `SmartBox.__init__` was building via `make_box.move(Location((-L/2, -W/2, 0)))`, leaving `Location.position` at `(-L/2, -W/2, 0)`. `solid.orientation = (a, b, c)` rotates around `Location.position`, so every `rotate_z` was rotating around the box's edge instead of through its centre. Fixed by constructing on a shifted Plane.

`iris.py` expansion:
- Added `create_diaphragm_plate()` + `build_diaphragm_plate_pieces()` helper. Reverse-engineered verbatim from `tmp/diaframma/obj_8_Diaf 1.stl`: 42-gon body, central aperture, six radial slot pockets in a 6-fold polar pattern, raised aperture collar. Aperture re-centred to origin so `create_blades(dim)` and the plate share the same iris centre.
- `IrisDimensions` defaults realigned to source meshes: `blade_count` 5→6, `pcd_radius` 30→31.23, `aperture_diameter_max` 35→41, `aperture_diameter_min` 25→12.86, `drive_pin_offset` 5→3.27. Old defaults preserved as `_LEGACY_DEFAULTS` (frozen IrisDimensions instance) for future plate parametrization across other iris designs.
- `__main__` block: exports `models/other/iris/iris.3mf` (assembled view, plate + blades labelled separately for colour) and `models/other/iris/stl/blade.stl` (single printable petal — the assembly is one plate + six identical blades).

Source-mesh naming convention (user clarified):
- `obj_N_Diaf K.stl` — `obj_N` is the instance index in the source assembly; `Diaf K` is the part type.
- Diaf 3 = iris blade (six identical instances per assembly — obj_1..obj_6 are the same part).
- Diaf 1 and Diaf 2 = plates (one of each per assembly).

Open questions:
- Drive mechanism: the slot's 39 mm length doesn't match the computed `drive_slot_arc_length` (3.27 × ~0.71 rad ≈ 2.3 mm). Either the slot serves a different mechanical purpose than `drive_pin_offset` models, or the real drive feature lives on the Diaf 2 plate (obj_7) which hasn't been reconstructed yet.
- Plate parametric rewrite: `create_diaphragm_plate` is verbatim hardcoded; making it derive from `IrisDimensions` would enable swapping in `_LEGACY_DEFAULTS` (5-blade) or other configurations.
