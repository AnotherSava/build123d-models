---
name: reference_build123d_mirrored_compound_volume
description: build123d Compound.volume returns 0 for a mirrored multi-solid compound; sum per-solid volumes instead
metadata:
  type: reference
---

build123d's `Compound.volume` / `Part.volume` **returns 0 for a compound of multiple solids that has been mirrored** (e.g. after `.mirror(Plane.XY)`), even though each contained solid reports its correct volume. Other aggregate metrics (`.area`, `.faces()`, `.center(CenterOf.MASS)`) are unaffected. Hit when basket's lids (a 2-solid compound + a sliver) broke the regression signature's centre-of-mass division (`volume` was 0 → divide-by-zero).

Work around it by summing per-solid volumes: `sum(s.volume for s in shape.solids())` — identical to `.volume` for single solids and un-mirrored compounds, so it's a safe drop-in. See `_shape_volume` in `tests/sava/csg/build123d/models/_signature.py`. Related: [[reference_model_regression_suite]].
