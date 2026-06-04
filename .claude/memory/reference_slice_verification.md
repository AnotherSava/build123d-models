---
name: reference-slice-verification
description: Verify model geometry numerically with thin-Box slice intersections; baseline contradictory probes against HEAD via git stash
metadata:
  type: reference
---

Verify built geometry numerically by intersecting the solid with thin `Box` slabs (build123d, via `solid.intersect(Box(...).located(Location((x, y, z))))`):

- **Full-section area by z**: `slice.volume / thickness` — catches graded features (lead-ins, tapers: area must change monotonically through the zone and stay constant outside it).
- **Bbox extents of a slice**: feature reach at a given height (e.g. dovetail tab tip x_max grading 17.71 → 18.0 over the lead-in zone) — exact against the analytic arc/taper value when the slab position is accounted for (bbox takes the extreme within the slab thickness).
- **Narrow probe strips** (`Box(0.04, 100, t)` across a cavity): material length = `volume / (w·t)` — measures pocket/mouth widths that bbox can't see.

**When a probe contradicts expectations**: before theorizing, run the *identical* probe on the committed version via `git stash` → probe → `git stash pop`. If HEAD shows the same number, the measurement (window placement, extent assumptions) is wrong, not the geometry. This separated a misread probe window from a suspected missing-pad bug in cablechannel in one round-trip.

Related: [[reference-arrange-scene-pattern]]
