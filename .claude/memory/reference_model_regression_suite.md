---
name: reference_model_regression_suite
description: Guard models vs geometry drift via B-rep-invariant signatures; byte-comparing exported 3MF/STL is a trap
metadata:
  type: reference
---

Committed models are guarded against silent geometry drift by `tests/sava/csg/build123d/models/test_model_regression.py` (see `docs/code/model_regression.md`). Each covered model exposes `build() -> ModelSpec` (`common/modelspec.py`); the suite rebuilds it, runs the real `export_model` into a temp dir, and compares a committed `signature.json` of B-rep invariants (volume, area, bbox, center-of-mass, solid/face/edge/vertex counts) with relative tolerance.

**Do not byte-compare exported meshes to detect regressions.** 3MF is a zip with embedded timestamps/UUIDs — never byte-reproducible. Binary STL is stable within a run but its tessellation density drifts across build123d/OCP kernel versions (observed: marker_holder 42622 → 43054 triangles, geometry unchanged), so committed meshes can't be reproduced triangle-for-triangle and a byte-lock would false-fail on every dependency bump. B-rep invariants are the tessellation-independent signal. Related: [[reference_slice_verification]].

Add a model: give it `build()`, register in `MODEL_BUILDERS`, then `MODEL_REGRESSION_REBASELINE=1 pytest tests/ -m regression` to create `signature.json`; re-baseline the same way to bless intentional geometry changes. The suite carries a `regression` marker so it is excluded from the frequent `pytest tests/` run (pytest.ini `addopts = -m "not regression"`); it runs via `-m regression` and through `/commit`, which runs `.claude/commit-checks.sh` (base suite then regression). Import-time-export models (poweradapters, cablestorage, grand_austria_hotel) must move export into `build()`/`__main__` before they can be covered.
