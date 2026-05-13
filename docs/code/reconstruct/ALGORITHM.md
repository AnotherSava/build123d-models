# Algorithm — STL to parametric Pencil reconstruction

## Pipeline

```
STL/OFF
   │  mesh_io.read()
   ▼
(V, F)                                          ← vertex array + triangle indices
   │  planes.cluster()
   ▼
plane clusters                                  ← coplanar triangle groups
   │  extrusion.pick_axis()
   ▼
candidate axis  ←  largest plane's normal
   │  extrusion.classify()
   ▼
(caps, side_walls)                              ← if any "other" → abort: not 2.5D
   │  datum.pick()
   ▼
datum plane  ←  largest side-wall by area
   │  datum.build_frame()
   ▼
local frame (x_dir, y_dir, z_dir, origin)
   │  boundary.extract_silhouettes()
   ▼
list of (depth, polygon2d) per cap
   │  extrusion.detect_cylinders()
   ▼
list of cylinders parallel to extrusion axis
   │  pencil_emit.emit()
   ▼
build123d Python source
```

## Step-by-step with rationale

### 1. Mesh ingestion — `mesh_io.read(path)`

Read OFF (text, simple) or STL (binary or ASCII). For STL, deduplicate vertices since STL stores each vertex once per adjacent triangle.

Return `(verts, faces)` where `verts: list[tuple[float, float, float]]` and `faces: list[tuple[int, int, int]]`.

### 2. Coplanarity clustering — `planes.cluster(verts, faces, ang_tol_deg=2.0, off_tol=0.05)`

For each triangle:
- Compute unit normal `n = (v1-v0) × (v2-v0)`, normalize.
- Compute signed offset `d = n · v0`.
- Canonicalize sign so the first non-zero normal component is positive.

Match each triangle to an existing plane cluster if:
- `n · cluster.n > cos(ang_tol_deg)` AND
- `|d - cluster.d| < off_tol`

When matched, update the cluster's `(n, d)` as an area-weighted running average for numerical stability.

**Why these tolerances**: tessellation introduces angular noise up to ~1° on smooth-ish flat faces and offset noise up to ~0.02mm. The 2°/0.05mm thresholds capture this without merging genuinely different planes (typically 30°+ angular separation).

Output: `list[PlaneCluster]` with fields `normal, d, area, tri_indices, vertex_set`.

### 3. Candidate extrusion axis — `extrusion.pick_axis(planes)`

Sort planes by area descending. Take the largest plane's normal as the candidate extrusion axis.

**Why this works**: in a 2.5D-extrudable part, the front and back caps are the largest planar faces because they cover the full silhouette. The side walls have areas bounded by `(silhouette_edge_length) × (depth_range)`, which is smaller. So "largest plane" reliably picks a cap face, whose normal IS the extrusion axis.

For non-2.5D parts this guess will fail step 4, which is fine — we abort.

### 4. Plane classification — `extrusion.classify(planes, axis, tol_deg=3.0)`

For each plane, compute `dot = |n · axis|`:
- `dot > cos(3°)`  → **cap** (parallel to axis)
- `dot < sin(3°)`  → **side wall** (perpendicular to axis)
- otherwise         → **other** (a tilted face)

**Abort condition**: if any plane is "other", the part is not 2.5D-extrudable. Return `is_2d5_extrudable=False` with a list of offending planes.

**Why 3° tolerance**: same noise budget as coplanarity. Real flat faces of authored parts almost always come out at <0.5° from their intended normal direction; 3° is generous slack.

### 5. Datum selection — `datum.pick(side_walls)`

Among side-wall planes, pick the one with maximum **plane area** (not edge length in cross-section — edge length skews toward long thin walls and ignores depth coverage). The datum is the "ground plane" against which the cross-section is sketched.

**Why plane area is the right metric**: a side wall's area = `(silhouette edge length) × (depth range it covers)`. The plane with maximum area is the one with the most physical contact with the part body — exactly the intuitive "back" or "floor."

### 6. Local frame construction — `datum.build_frame(axis, datum, silhouettes)`

```
z_dir = axis                       (extrusion direction)
y_dir = datum.normal               (orient so shape mass is in Y+)
x_dir = y_dir × z_dir              (right-hand rule)
```

Compute `(min_u, min_v)` over all silhouette vertices in the new frame, then set:

```
new_origin = min_u * x_dir + min_v * y_dir
```

After this transform, every silhouette vertex satisfies `u ≥ 0` and `v ≥ 0` — the part lives in the first quadrant of the local cross-section plane, with the datum at `v = 0`.

**Gotcha**: compute `min_u, min_v` from the raw 3D vertices in the mesh, NOT from earlier-projected 2D points. Reprojecting through 2D loses the depth coordinate and gives wrong origin offsets.

### 7. Silhouette extraction — `boundary.boundary_polygon()` + `datum.to_local()`

For each cap face's triangle set:
1. Count each edge's occurrences across the triangles. Edges with count = 1 are boundary edges.
2. Walk the directed boundary edges into a closed ring of vertices (`boundary.boundary_polygon`).
3. Project each ring vertex to (u, v) coordinates in the datum-aligned frame via `datum.to_local()`.
4. Simplify collinear vertices iteratively (`boundary.simplify_collinear`): drop vertex `b` if its perpendicular distance to line `ac` is < 0.05 mm. Iterate until stable.

**Why distance-based simplification** (not cross-product): tessellation makes "straight" edges into many short, slightly non-collinear segments. A cross-product threshold of 1e-3 is too tight at typical edge scales (1–5 mm); a 0.05 mm perpendicular-distance threshold collapses tessellation noise while preserving real corners.

### 8. Cylinder detection — `extrusion.detect_cylinders(verts, faces, planes, axis)`

Cylinders manifest in coplanarity clustering as **a swarm of small triangle patches in a localized bbox, with normals sweeping smoothly through orientations** sharing a common perpendicular = the cylinder axis.

Detection heuristic:
1. Find planes with area below some threshold (e.g., 5% of largest cap).
2. Group them by spatial proximity (overlapping bboxes).
3. For each group: compute the common axis as the normal direction shared by all the patches' normals (i.e., the direction perpendicular to all of them).
4. If that axis is parallel to the extrusion axis (within tol), it's a cylinder we can emit as `Cylinder(r, h)` along Z.
5. Estimate radius from the bbox dimensions perpendicular to the axis, or from `√(total_area / (2π * height))`.

Alternatively, if RANSAC output is available, use its cylinder fits directly — they're more accurate.

### 9. Code emission — `api.py::_emit_code` + `pencil_emit.emit_pencil_for`

**Layer classification.** Non-body caps are tagged by their depth relative to the body's z-range `[min(back_depth, front_depth), max(...)]`:
- depth **below** that range → `back_protrusion` (fused below the body)
- depth **above** that range → `front_protrusion` (fused above the body)
- depth **inside** that range → `pocket` (cut from the body)

**Cylinder substitution.** Every loop in every layer is tested for circularity by `_detect_circle`: ≥16 vertices and polygon area within 5% of `π·r̄²` (r̄ = mean distance from the area-weighted centroid). The area-ratio test (not radial equidistance) handles real STL cylinders that pick up flat chord sections at CSG boolean intersections — radial deviation balloons to ~17% there even though the area still matches a circle within 1%. Loops that pass emit as `SmarterCone.cylinder(r, h)` instead of a Pencil polygon, with `base = (u, v, z)` taken from the post-simplification centroid (smooths out the flat-chord artifacts) and the same `cut`/`fuse` op the polygon path would have used at that nesting depth. This generalizes across all layer roles — body holes, pockets, protrusion outers, protrusion holes, nested islands — not just the `front_protrusion` single-loop case.

**Box substitution.** Loops that aren't circles are tested for rectangularity by `_detect_box`: oriented-bounding-box fill ratio ≥ 95% AND at least 3 interior corners within 6° of 90°. The OBB is found by rotating-calipers approximation (smallest axis-aligned bbox when polygon is rotated to align with each of its edges in turn). The right-angle-count threshold separates true boxes (4 right corners) and rectangles-with-one-chamfered-corner (3 right corners + 2 chamfer angles) from trapezoids and parallelograms whose OBB fill ratio can also land in the 95% band. Detected boxes emit as `SmartBox(L, W, h).rotate_z(angle).move(cu, cv, shift_z)` — `SmartBox` is XY-centered but Z-base-aligned (same as `SmarterCone.cylinder` and `Pencil.extrude`), so `shift_z` lands the box base at the layer's base z, top at `shift_z + h`.

**Duplicate detection.** Within each non-body layer, depth-0 outers with no nested children are grouped by canonical signature: `('cylinder', r)` for cylinders, `('box', L, W)` for boxes, `('polygon', sorted_canonical_vertices)` for Pencil polygons. Polygon canonical form is centroid-translated to origin + PCA-rotated to align principal axis with +X (with 180° flip resolution); the rotation needed to recover the source pose is stored per-instance. Groups with ≥ 2 members emit as a `for` loop over `(angle, cu, cv)` placements with a single template invocation; singletons emit individually. Outers with children skip dedup (would need to also dedup their children — rare in practice, not worth the complexity).

**Polar-pattern detection** (`_detect_polar_pattern`). Before emitting a dedup group's placement list, the group is tested for N-fold rotational symmetry: all positions on a common circle (≤1% radial deviation from centroid), uniform 360°/N angular spacing, AND primitive rotations advancing by the same step modulo the primitive's self-symmetry period (180° for `SmartBox`, 360° for chiral polygons, skipped for `SmarterCone.cylinder`). When detected, the emit becomes `template = ...; pivot = Axis((cx, cy, 0), (0, 0, 1)); for i in range(N): blade.op(template.copy().rotate(pivot, i * step))` — the design intent ("six pockets in a 6-fold polar pattern") is preserved in the code, and identical-pose rotations (e.g. a box rotated 60° per copy around the central axis, with the box's own orientation rotating in lockstep) collapse into one rotate call instead of an explicit placement list. Requires N ≥ 3 (a 2-element pattern is ambiguous with reflection).

**Shared anchor.** Before emit, the cross-section origin is shifted onto the vertex shared by the most emit-eligible polygons (`find_shared_start`, ties broken by leftmost-bottommost). After the shift, that vertex is at local `(0, 0)`, so every `Pencil` opens with bare `Pencil()` and drops `start=`.

**Build in default `Plane.XY`.** All Pencil ops, extrudes, moves, and `SmarterCone.cylinder(r, h)` run in clean local coords. A single optional `cross_section` Plane transform at the end places the blade in the source-mesh world frame; deleting that block keeps the blade local-frame.

**Pencil strokes** (per silhouette, after CW polygons are reversed to CCW so `extrude(+h)` lands in `+z_dir`):
- `right(dx)` / `left(-dx)` when `|dy| < 1e-3`; `up(dy)` / `down(-dy)` when `|dx| < 1e-3`. The argument is **omitted** when the destination lands on the local-anchor axis (`right()` / `down()` snaps to 0).
- Otherwise compute `angle = degrees(atan2(-dx, dy))` (matches `Pencil.draw`'s CCW-from-+Y convention). If it snaps to a multiple of 15° within 0.05°, emit `draw(length, angle)`; else emit `jump((dx, dy))` — `jump` is more readable than a `draw` with an ugly angle.
- Auto-close on `extrude` handles the final edge.

**Cylinder placement.** `SmarterCone.cylinder(r, h)` (defaults to `Plane.XY`, base at origin) followed by `.move(cu, cv, cz)` — `cz` is the base z, not the center, matching `CylinderFeature.base`.

**Composition.** `.fuse()` for protrusions and cylinders, `.cut()` for pockets. (Don't emit `+` / `-` — `SmartSolid` doesn't define those operators.)

**Number formatting.** Apply `numbers.fmt()` to every literal:
- Snap `|x| < 0.0005` to `0`
- Strip trailing zeros (`3.000` → `3`)
- Drop unsigned `+` prefix

## Complexity

- Coplanarity clustering: O(F · P) where F = triangles, P = current cluster count. For typical CAD meshes (F < 10k, P < 20), well under a second.
- Boundary walk: O(F) per plane.
- Datum selection: O(P).
- Code emission: O(total vertices in simplified silhouettes).

Total: linear in mesh size for the geometries this targets.

## Verification

The reference test is the iris blade (`obj_1_Diaf 3.stl`, 162 vertices, 320 triangles). Expected behavior:

- 9 significant planes detected (4 caps + 6 side walls of which 5 are flat, 1 is the floor)
- Extrusion axis: `(+0.683, -0.731, 0)` within ±0.001
- Datum: the floor (normal = world Z), area 74.87 mm²
- 4 depth layers at `−0.611, +0.889, +3.889, +7.889` named `back_protrusion`, `back`, `front`, `front_protrusion` (the last's single circular loop is replaced by a `SmarterCone.cylinder` primitive via the generalized circle-detection in `_emit_nested_loops`)
- 1 cylinder: `r ≈ 1.8`, `h = 4`, base at cross-section-local `(-3.78, 1.70, 3)` after the shared-anchor shift
- Emitted code: 5-stroke body (jump + draw + left + draw + down) + 3-stroke back protrusion (jump + left + down) + 1 `SmarterCone.cylinder` primitive + an optional `cross_section` Plane transform that places everything back in the source-mesh world frame
- `exec()`ing the emitted code reproduces the source mesh's bbox `(18.9 × 17.5 × 26.5 mm)` and volume `~1125 mm³`

Run `python -m pytest tests/sava/csg/build123d/reconstruct/` to validate end-to-end.
