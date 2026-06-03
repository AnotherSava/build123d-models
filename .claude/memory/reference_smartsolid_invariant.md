---
name: reference-smartsolid-invariant
description: "SmartSolid maintains origin==location.position AND _orientation==solid.orientation; _reanchor restores after OCC ops, _apply_tracked_transforms restores after builder rebuilds"
metadata: 
  node_type: memory
  type: reference
---

`SmartSolid` maintains TWO coupled invariants for single-shape solids:
- `self.origin == self.solid.location.position`
- `self._orientation == self.solid.orientation`

Together these let `orient()`'s location-anchored rotation pivot coincide with the user-facing anchor (so `rotate(Axis.X/Y/Z)` rotates around the world axis line) AND make `rotate(0)` a true no-op (no stale cumulative orientation).

**Construction (`__init__`)** seeds `_orientation` from the incoming `self.solid.orientation` (NOT assumed `(0,0,0)`) and `_reanchor()`s `origin` to `location.position`. This is what makes `plane=`-constructed solids — e.g. `SmartBox(..., plane=P)`, `SmartBox.with_top` — satisfy the invariant: their rotation is baked into `solid.orientation`, and assuming `(0,0,0)` would make `rotate()` overwrite (silently drop) the baked plane rotation, and transform-replay (`_apply_tracked_transforms`) lose it. Pinned by `test_orientation_invariant_holds` / `test_rotate_composes_with_reframe`.

Separately, a `plane=`-constructed box still needs an *honest* `solid.location.position` for `colocate`/rebuild to re-place it. If P's origin is offset from world origin, `_reanchor` zeroes the position while geometry stays put, so the location lies. `with_top` avoids this by anchoring the plane at the world origin and `move()`-ing into place; `SmartBox.taper` rebuilds the box then uses `colocate(self)` (copies the real `solid.location`) rather than replaying Euler `_orientation`. Pinned by `test_taper_preserves_placement_on_reframed_box` / `test_result_has_honest_location_for_colocate`.

Two complementary helpers maintain the invariants depending on what kind of op just ran:

**OCC ops that produce a fresh BRep (`fuse`, `cut`, `intersect`, `mirror`, `scale`, `pad`):** the BRep bakes in the prior orientation/position at identity location and identity orientation. So we **reset** both tracked fields:
```
self.origin = Vector(0, 0, 0)
self._orientation = Vector(0, 0, 0)
self._reanchor()  # syncs location.position to (0,0,0) via relocate, preserving world geometry
```
`_reanchor()` uses build123d's `relocate` (deprecated but the only API that changes location without moving geometry). Skipping the `_orientation` reset causes a latent double-rotation bug: a subsequent `rotate_z(0)` re-applies the stale cumulative orientation. Pinned by `test_rotate_fuse_rotate_zero_does_not_double_rotate`.

**Subclass builder rebuilds (`SmarterCone._rebuild` → `extend`/`inner`/`_recalculate_inner`):** `_build_solid()` always produces an unrotated solid at the origin in `self.plane` — so we **replay** the tracked transforms after each rebuild:
```
self.solid = self._build_solid()
self._apply_tracked_transforms()  # sets solid.orientation = self._orientation, then translates to self.origin
self.assert_valid()
```
This makes builder calls commute with prior `rotate(Axis.X/Y/Z)` and `move()` — any order of interleaving produces the same world geometry as "complete the builder chain first, then transform." Pinned by `TestSmarterConeBuilderTransformCommute`.

**`ShapeList`-valued solids** (boolean ops that produced disconnected pieces): no single `location` to anchor; both helpers are no-ops. `rotate()` falls back to rotating a wrapped `Compound` at origin.

**Behavioral consequence**: `self.origin` does NOT follow the shape through boolean ops / mirror / scale — it resets to `(0, 0, 0)`. Use `bound_box.center()` for "where is this shape now."

Related: [[build123d-smartbox-orient-gotcha]] (`~/.claude/learnings/`) — underlying build123d location-pivot mechanics, `relocate` API specifics.
