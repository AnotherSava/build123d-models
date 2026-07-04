---
name: reference_forward_port_stale_model
description: Port a stale/broken model forward by running its last-working commit as a golden oracle and diffing per sub-part
metadata: 
  node_type: memory
  type: reference
  originSessionId: 7d59a8c7-e41f-4991-85a3-1a5c974895e5
---

When a model no longer runs because the **common code it depends on changed underneath it** (renamed/removed helpers, shifted semantics), port it forward against a *golden oracle* instead of guessing:

1. **Find the last-working commit.** `git log --follow` the model file; cross-reference the add/remove commits of the symbols it imports (`git log -S "def foo("`). The last commit where *every* import resolves is the golden one. (Real case: hydroponics `stand.py` — golden was `8502562`, ~Dec 2025; the later "use SmartLoft" refactor was applied but never run, so it was import-broken from birth.)
2. **Run golden as ground truth.** `git worktree add /tmp/x <golden>`, then `PYTHONPATH=/tmp/x/src venv/Scripts/python.exe -m <module>`. build123d is *usually* API-stable, so old model code usually runs on the current venv and gives reference geometry. **But not always** — if the library itself drifted (build123d removed a method the old code called; symptom `'Solid' object has no attribute 'rotate_multi'`), the golden can't be rebuilt. Fall back to the **already-committed output artifacts (the STLs) as the golden**, comparing orientation-invariant metrics (volume, surface area, sorted bounding-box) so print-pose mirrors/rotations don't affect the match. (basket forward-port, 2026-07-03.)
   - **If the drift is only in a validation guard** (e.g. `is_valid` went method→property, so golden's `assert_valid()` raises `TypeError: 'bool' object is not callable`), monkeypatch the guard to a no-op (`SmartSolid.assert_valid = lambda self: None`) and run golden for real — you get true reference geometry without rebuilding. This is the **only** option when the model has no committed STLs to fall back to (models that export at import time, e.g. `grand_austria_hotel/*`). (GAH forward-port, 2026-07-03.)
3. **Diff per sub-part, not just the whole model.** A matching final bbox/volume hides compensating errors. Build a diagnostic that reports `volume + bbox size + center` for every `create_*` sub-part, run it under both PYTHONPATHs, and `diff`. Each diverging part points at one changed common API. Fix, re-diff, repeat until only benign residuals remain.
4. **Whole-model XOR is unreliable here.** OCCT booleans (`-`, `intersect`) *fail/return garbage on near-coincident complex solids* (coincident faces) — you'll see ~200% mismatch or `None`. Point-in-solid classification (`BRepClass3d_SolidClassifier`) works but is ~ms/call, too slow for dense sampling. The per-part diff in step 3 is the decisive check; it localizes features (e.g. a drainage hole) that equal total volume would mask.

Common-API drifts found this way in `stand.py` (all fixed **model-side**, not in common code):
- **Pencil** now ignores the Z component of its `start` vector (shifts plane by in-plane X/Y only). To offset a profile along the plane normal, shift the plane itself: `plane.offset(dz)`.
- **SweepSolid.create_path_plane / create_plane_end** track movement only through the fluent `move`/`align` API. A direct `solid.position = ...` assignment bypasses tracking → stale path plane. Use `.move(dx,dy,dz)` instead.
- **SmartSolid rotation rename was not behavior-preserving:** golden `rotate(rots, plane)` was orient-only (spins in place); current `rotate_multi(rots, plane)` *also* rotates the origin around the plane (translates). For the old in-place flip use `orient(rotate_orientation(solid.orientation, rots, plane))`.
- **SmarterCone rewrite** changed cone/taper geometry ~0.07% (same bbox); connector volumes differ by a few mm³. Benign — an intentional common-code improvement, not a model bug; don't chase it.

Related: [[reference_slice_verification]], [[reference_smartsolid_invariant]], [[reference_extrude_winding_direction]], [[feedback_build_at_origin_then_align]]
