---
name: reference_notch_inplane_wedge
description: Forward-porting add_notch — build the wedge natively in-plane (no orient) so coplanar faces merge and downstream booleans stay stable; the Direction vector-rewrite dropped alignment helpers
metadata: 
  node_type: memory
  type: reference
---

Porting the Grand Austria Hotel inserts (`celebrities`, `turnorder`) forward exposed two things (2026-07-03):

**The `Direction` enum vector-rewrite silently dropped alignment helpers.** The old scalar `IntEnum` had `alignment_closer` / `alignment_middle` / `alignment_further` / `orthogonal_axis` / `horizontal`; the vector-`Enum` rewrite kept only `axis` / `rotate` / `from_vector`. `add_notch` (smartsolid) and `add_cutout` (smartbox) both depend on the missing properties — and **only the GAH models use them**, so the breakage sat unnoticed (`add_cutout` threw `AttributeError: 'Direction' object has no attribute 'alignment_middle'`). Fix was purely additive: restore `alignment_closer`/`alignment_middle` computed from `value` sign (positive axis N/E/U → RL/R, negative S/W/D → LR/L). Note the axis-direction flip: old `Direction.axis` returned the canonical +axis; current returns the vector direction (S → -Y), so golden's align logic can't be transcribed verbatim.

**Build a fused wedge natively in its plane, never orient-then-move it.** A triangular notch built in XY then `orient()`ed and aligned lands ~1e-7 off exact coincidence with the box faces, so `UnifySameDomain` leaves the coplanar bottom/side faces split (9 faces vs golden's 7). `.clean()` won't merge them, and the stray edges then get filleted by a later `fillet_z` / destabilise the boolean cut — a 2–3% volume drift with matching bbox. Rebuilt via `Pencil(Plane.YZ|XZ)` drawn directly in the vertical plane and placed by **translation only** (mirror for +axis faces) → exact coincidence, 7 faces, golden geometry reproduced. This is the boolean-merge sibling of the fillet-at-origin rule in [[feedback_build_at_origin_then_align]] and CLAUDE.md's rotated-then-moved fillet note.

Verified against a golden worktree at `e7130ad^` (where the pre-stub `add_notch` lived); run it with `SmartSolid.assert_valid` monkeypatched to a no-op (`is_valid` became a property, so the old method-call guard raises `TypeError: 'bool' object is not callable`). See [[reference_forward_port_stale_model]]. Residual: `add_cutout` was itself rewritten, so overlapping cutouts differ from golden at the shared corner (each cutout matches golden alone) — a benign rewrite artifact, baselined as current geometry.
