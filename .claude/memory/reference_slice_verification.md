---
name: reference-slice-verification
description: Verify geometry numerically — thin-Box slices, refactor equivalence (volume/bbox vs old construction, relative tolerances), intersect-volume fit checks
metadata:
  type: reference
---

Verify built geometry numerically by intersecting the solid with thin `Box` slabs (build123d, via `solid.intersect(Box(...).located(Location((x, y, z))))`):

- **Full-section area by z**: `slice.volume / thickness` — catches graded features (lead-ins, tapers: area must change monotonically through the zone and stay constant outside it).
- **Bbox extents of a slice**: feature reach at a given height (e.g. dovetail tab tip x_max grading 17.71 → 18.0 over the lead-in zone) — exact against the analytic arc/taper value when the slab position is accounted for (bbox takes the extreme within the slab thickness).
- **Narrow probe strips** (`Box(0.04, 100, t)` across a cavity): material length = `volume / (w·t)` — measures pocket/mouth widths that bbox can't see.

**When a probe contradicts expectations**: before theorizing, run the *identical* probe on the committed version via `git stash` → probe → `git stash pop`. If HEAD shows the same number, the measurement (window placement, extent assumptions) is wrong, not the geometry. This separated a misread probe window from a suspected missing-pad bug in cablechannel in one round-trip.

**Refactor equivalence**: when restructuring construction code, replicate the *old* construction verbatim inside a tmp script and compare both paths' `solid.volume` and bbox corners. Tolerances matter: OCC boolean noise is ~1e-9 *relative* (use `delta < 1e-6 * volume`, never small absolute thresholds) and OCC bboxes are inflated by ~1e-7 (a 1e-9 bbox/coordinate check produces false MISMATCHes on correct geometry). Construction-order changes (different frame, align vs move) shift results within that noise; bit-identical deltas (1e-13) indicate the constructions are literally the same cuts.

**Assembled-fit check**: `part_a.intersected(part_b)` volume — exactly 0 proves a sliding fit (cap on channel), a nonzero value measures the collision (178 mm³ proved the down-cap seam coupling). The result may be a ShapeList of lumps; sum their volumes.

Related: [[reference-arrange-scene-pattern]]
