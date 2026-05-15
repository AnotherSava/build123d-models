# Findings — research log

Discoveries from developing the 2.5D reconstruction algorithm, anchored to the iris blade case (`tests/sava/csg/build123d/reconstruct/data/iris_blade.off`). Read this before iterating on the algorithm — most of these were surprising and several were arrived at after wrong turns.

## What the iris blade actually is

The reference mesh (162 vertices, 320 triangles, bbox 18.9 × 17.5 × 26.5 mm) is **a flat 3-mm-thick petal**, oriented in a plane whose normal is `(+0.683, −0.731, 0)` — tilted ~47° from world X around Z.

Aspect ratio along the part's own axes: **3 × 22 × 26.5 mm** (thickness × length × height). This is what an iris diaphragm blade actually looks like: a thin, tall, broadly-triangular petal that pivots around a pin at its base.

### iris.py has been rewritten from this reconstruction (RESOLVED)

Historical: an earlier version of `IrisDimensions` had tapered-loft defaults (`body_base_length: 13.0`, `body_base_width: 14.0`) that did not match the source STL, derived from a projection artifact of the tilted blade.

`src/sava/csg/build123d/models/other/iris.py` has since been rewritten to mirror the reconstruction emit directly — three stacked Pencil-extruded layers (back protrusion + body + pivot pin) built in default `Plane.XY`, translated to put the pivot at `(pcd_radius, 0)`. Blade volume now matches the source mesh (~1155 mm³).

## The 2.5D property is mathematically exact, not approximate

When we take the largest plane's normal as the candidate extrusion axis, every other plane on the blade has `|n · axis|` equal to either 1.0000 or 0.0000 — **no values in between**, no "tilted" planes:

```
CAP faces (⊥ to extrusion axis):
  area= 347.97  |n·axis|=1.0000  depth=+3.889
  area= 331.92  |n·axis|=1.0000  depth=+0.889
  area=  26.32  |n·axis|=1.0000  depth=-0.611
  area=  10.17  |n·axis|=1.0000  depth=+7.889

SIDE-WALL faces (∥ to extrusion axis):
  area=  74.87  |n·axis|=0.0000
  area=  69.28  |n·axis|=0.0000
  area=  62.23  |n·axis|=0.0000
  area=  36.12  |n·axis|=0.0000
  area=  24.25  |n·axis|=0.0000
  area=  19.50  |n·axis|=0.0000

OTHER: 0
```

The blade is a true 2.5D stepped extrusion. The structure has four cap depths (`−0.611, +0.889, +3.889, +7.889`) and three thickness layers: a 1.5 mm **back protrusion** (a small strip extending behind the body's back face — *not* a pocket cut into the body), a 3 mm main body, and a 4 mm pivot protrusion on the front. The algorithm names them `back_protrusion` / `front_protrusion` and fuses them rather than subtracting; the older "recess" name was misleading.

This property is detectable with a single dot-product test. Once detected, the entire reconstruction is mechanical.

## The pivot pin is a real cylindrical feature, not a tessellation artifact

The mesh contains ~82 small triangle clusters in a localized bbox (X∈[207,211], Y∈[185,189], Z∈[0.1,3.6]) with normals smoothly sweeping through orientations. Earlier I assumed these were tessellation noise; they're not.

Evidence they form a cylinder:
- Bbox is small, localized — characteristic of a discrete feature, not random noise spread over the surface
- Normals sweep continuously through orientations that all share a common perpendicular: `(+0.683, −0.731, 0)` — exactly the extrusion axis
- Total area of the group ≈ 55 mm², consistent with a cylinder of `r=1.82, h=4` (lateral area `2πrh = 2π·1.82·4 = 45.8`, plus end-caps)
- The "orange face" at depth `+7.889` (area 10.17 mm²) ≈ `π·1.82² = 10.4 mm²` — this is the cylinder's flat tip

RANSAC independently fits a cylinder here with center `(205.22, 191.67, 1.80)`, axis `(0.683, -0.731, 0)` (matches our extrusion axis), and radius `1.8183`. Two independent methods agree.

**Earlier wrong claim**: I previously called these "spurious cylinders" RANSAC was finding. That was wrong; the cylinders are real features of the part.

## Cross-validation: RANSAC vs coplanarity clustering

| | RANSAC | Coplanarity clustering |
|---|---|---|
| Significant planes detected | 9 | 9 (≥1% of area) |
| Plane normals | match within tolerance | match within tolerance |
| Cylinder count | 3 | 1 well-localized group, 2 likely RANSAC artifacts |
| Extrusion-axis-aligned cylinder | yes, radius 1.82 | yes (the localized group) |

Two of RANSAC's 3 cylinders are likely spurious (the r=0.89 and r=5.98 fits), but the main pivot pin is correctly identified by both methods.

## Algorithm parameters that mattered (with rationale)

| Parameter | Value | Why this value |
|---|---|---|
| Coplanarity angular tolerance | 2° | Tessellation introduces up to ~1° of normal noise on flat faces |
| Coplanarity offset tolerance | 0.05 mm | Mesh quantization is sub-millimeter; 0.05 mm catches the noise without merging real parallel planes |
| Cap/side-wall classification | 3° | Same noise budget plus headroom; authored flat faces fall well within |
| Collinear simplification | 0.05 mm perpendicular distance | Cross-product epsilon (e.g., 1e-3) was too tight: produced 75-gon for what should be a 6-gon |
| Datum selection metric | plane area | Edge-length-in-cross-section picks tall thin walls; area picks "largest contact" which matches intuition |
| Number-formatting fmt() snap | `\|x\| < 5e-4` | Distinguishes "approximately zero from numerical noise" from real small values |

## Gotchas (things that bit me during development)

1. **Reconstructing 3D from 2D projections loses the depth coordinate.** When computing the new-frame origin shift, use original 3D vertices from `boundary_polygon`, not points reconstructed from earlier-projected 2D polygons. Caused the cross-section to render at 1/30 the correct scale.

2. **matplotlib's `axhline()` does not autoscale.** When laying out the cross-section overlay, the only patches added were `Polygon` instances; matplotlib doesn't autoscale axes for patches by default. Set `xlim/ylim` explicitly from polygon extents.

3. **Pencil's `start` parameter shifts the plane origin, doesn't just set the initial pen position.** After `Pencil(plane, start=(a, b))`, the pencil is at local `(0, 0)` in a shifted frame — all subsequent moves are relative to `(a, b)`. The closing `create_face(enclose=True)` returns to `(0, 0)` in the shifted frame = `(a, b)` in the original.

4. **The largest plane is not always a cap — but it usually is.** For 2.5D parts the front/back face is biggest; works by inspection of plane-area distributions. Worth adding a sanity check: if the chosen axis fails step 4 (any "other" planes), try the next-largest plane's normal before giving up.

5. **The datum heuristic gives different answers based on metric.** Edge-contact-length picks `Plane 4` (the top-left bevel, 46 mm of contact edge across silhouettes) as datum. Plane area picks `Plane 3` (the floor, 74.87 mm²). The floor is the intuitive answer; plane area is the right metric.

6. **iris.py's `bbox_length` / `bbox_width` properties are hardcoded constants, not computed from dimensions.** Returns 18.9 and 17.5 regardless of what the dataclass fields are set to. Misleading.

## Algorithmic limits

What this algorithm does NOT handle:

- **Lofts / sweeps / free-form surfaces.** These produce "other" planes (tilted) and fail step 4.
- **Multi-axis features.** A part with cylindrical holes drilled perpendicular to the extrusion axis isn't expressible this way.
- **Rotational/mirror symmetries.** Two identical 6-gon silhouettes rotated 60° apart show up as two separate layers, not `PolarLocations(0, 6) * one`. Symmetry detection is a separate Tier-1 problem on top of 2.5D detection.
- **Self-intersecting silhouettes.** If a silhouette has a hole, the boundary walk produces a self-intersecting result. Needs proper handling via even-odd winding or face triangulation.
- **Bad meshes.** Non-manifold edges, flipped normals, isolated triangles — all break clustering. Pre-cleanup (trimesh.repair or similar) is needed for noisy input.

## Future enhancement directions

1. **Symmetry detection (Tier 1.5+).** After 2.5D detection, look for rotational/mirror/grid patterns among the silhouettes. Emit `PolarLocations` / `mirror` / `GridLocations` when applicable. For the full 8-blade iris diaphragm assembly, this collapses N copies of the same silhouette into one.

2. **Non-axis-parallel cylinder support.** Detect cylinders with arbitrary axes; emit `Cylinder` with appropriate `Pos`/`Rot`.

3. **Verification harness.** After emitting code: execute it in build123d, export STL, compute Hausdorff distance against source. Make this a CI requirement: a reconstruction is "accepted" only if Hausdorff < `eps`.

4. **Multi-strategy axis search.** If the largest plane's normal fails step 4, try the next-largest, then the cross product of the top two, then the smallest distinct plane normal in the set, etc. Cheaply expands the algorithm's coverage.

5. **Robust to mesh noise.** Use surface-fit RANSAC for plane detection instead of triangle coplanarity clustering. Slower but tolerates uneven tessellation.

6. **Authored-shape recovery (Tier 3).** When the 2D silhouette has obvious 2D-CAD structure (a rectangle plus a fillet plus a rounded corner), emit `Pencil` with `fillet()` calls instead of a raw polygon. Captures user intent, not just the mesh.

## Pedagogical artifacts

The `data/` folder of this transfer package contains visualizations from the iris-blade development run:

- `planes/00_overview.png` — color-coded view of all 9 planes
- `planes/01-09_plane.png` — one image per plane with that plane highlighted
- `planes/10_fillet_group.png` — the "fillet group" that turns out to be the pivot pin
- `pencil_2d/01-09_pencil.png` — 2D polygon outlines with numbered stroke directions
- `extrusion/cross_section_overlay.png` — all 4 cap silhouettes + cylinder overlay in cross-section
- `datum_aligned/datum_aligned_overlay.png` — final clean reconstruction in the datum-aligned frame
- `datum_aligned/blade_datum_aligned.py` — generated build123d code for the blade

These are useful as both regression-test references and pedagogical material for "what is this algorithm actually doing."
