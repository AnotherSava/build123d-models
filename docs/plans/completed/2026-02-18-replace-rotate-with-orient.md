# Replace rotate() Internals with orient()

## Overview
- Build123d's `.rotate()` method on shapes (Solid, Wire, Face) is heavy and not recommended; `.orientation` property setting is the preferred lightweight approach
- Keep the user-facing `rotate()` API on SmartSolid (fixed-axis, incremental) unchanged
- Internally, `rotate()` should compute the new absolute orientation and delegate to `orient()` instead of calling build123d's `.rotate()` or `.moved(Location(Rotation(...)))`
- Also replace all `Vector.rotate()`, `Plane.rotated()`, `Wire.rotate()`, `Face.rotate()` calls with our own math from `geometry.py`

## Context (from discovery)
- **Core files**: `smartsolid.py` (rotate/orient definitions), `geometry.py` (rotation math utilities)
- **Subclass overrides**: `sweepsolid.py`, `smartloft.py` (rotate/orient overrides for subsidiary objects)
- **Also affected**: `smartrevolve.py` (_rotate_plane_around_axis uses Vector.rotate), `geometry.py` (Direction.rotate uses Vector.rotate)
- **Model file**: `basket.py` line 194 calls `.solid.rotate()` directly — should be updated
- **Existing helpers**: `rotate_orientation()`, `convert_orientation_to_rotations()`, `rotate_vector()`, `multi_rotate_vector()`, `orient_axis()`, `calculate_orientation()` — all use pure math, no build123d rotation

## Development Approach
- **Testing approach**: Ensure sufficient test coverage BEFORE refactoring, then verify tests pass after changes
- Complete each task fully before moving to the next
- Make small, focused changes
- **CRITICAL: every task MUST include new/updated tests** for code changes in that task
- **CRITICAL: all tests must pass before starting next task**
- **CRITICAL: update this plan file when scope changes during implementation**
- Run tests after each change
- Pay particular attention to tests combining consecutive move/orient/rotate operations

## Testing Strategy
- **Unit tests**: required for every task
- Existing tests cover basic rotate/orient but have significant gaps (see Task 1)
- Key gap areas: consecutive operations, arbitrary axes, convenience methods, _orientation tracking

## Progress Tracking
- Mark completed items with `[x]` immediately when done
- Add newly discovered tasks with ➕ prefix
- Document issues/blockers with ⚠️ prefix
- Update plan if implementation deviates from original scope

## Implementation Steps

### Task 1: Add missing test coverage for rotate/orient before refactoring
Focus on gaps that will serve as regression tests for the refactoring.

- [x] Verify `rotate_vector()` has sufficient test coverage for arbitrary axes — added 4 parametrized cases (180° XY diagonal, 180° XZ diagonal, 360° arbitrary, 240° around (1,1,1)) plus small angle test
- [x] Add tests for `rotate_x()`, `rotate_y()`, `rotate_z()` convenience methods — 6 parametrized cases verifying they match `rotate(Axis, angle)`
- [x] Add tests for `rotated()` and `oriented()` (returns copy) — verify original unchanged and copy rotated
- [x] Add tests for consecutive `rotate()` calls: two 45° = single 90°, three axes, 4x90° return, 360° return
- [x] Add tests for `rotate()` + `move()` + `rotate()` sequence — verify origin at each step
- [x] Add tests for `orient()` + `move()` + `orient()` sequence — verify origin tracking
- [x] Add tests for mixing `rotate()` and `orient()` — rotate_then_orient replaces, orient_then_rotate adds
- [x] Add test for arbitrary axis rotation — bounds after 180° around (1,1,0), origin via custom axis, 360° return
- [x] Add test verifying `_orientation` field matches `solid.orientation` after orient, rotate, consecutive rotates, rotate+orient, rotate_multi
- [x] Add test for 360° rotation returning to original state
- [x] Add tests for SweepSolid: rotate_multi+move consistency, orthonormality, origin tracking
- [x] Add tests for SmartLoft: consecutive rotate calls, rotate+move+rotate, 4x90° return
- [x] Run tests — 639 passed

⚠️ **Discovered pre-existing bugs during testing:**
1. `SweepSolid.rotate(Axis, angle)` is broken: `self.plane_path.rotated(axis, angle)` passes wrong arg types to `Plane.rotated()` (expects VectorLike, not Axis+float). No existing tests call this path directly.
2. `SweepSolid.orient()` with consecutive calls: `self.plane_path = self.plane_path.rotated(rotations)` is incremental but solid orientation is absolute — double-rotates the plane. Task 4 will fix both.

### Task 2: Add helper to rotate Plane using our own math
Create a utility function that rotates a Plane without using build123d's `.rotated()` or `Vector.rotate()`.

- [x] Add `rotate_plane(plane, axis, angle)` to geometry.py (line ~374) — uses `rotate_vector()` on x_dir, z_dir, origin
- [x] Add `orient_plane(plane, orientation)` to geometry.py (line ~389) — uses `convert_orientation_to_rotations()` + `multi_rotate_vector()`
- [x] Write tests for `rotate_plane()` — 4 basic parametrized, offset origin, arbitrary axis, orthonormality, 360° return (8 tests)
- [x] Write tests for `orient_plane()` — 4 basic parametrized, offset origin, matches build123d, orthonormality, multi-axis (8 tests)
- [x] Run tests — 655 passed

### Task 3: Refactor SmartSolid.rotate() to delegate to orient()
The core change: `rotate()` computes new orientation and calls `SmartSolid.orient()`.

- [x] Rewrite `SmartSolid.rotate()` to:
  1. Compute new orientation: `new_orient = rotate_orientation(self._orientation, rotations_vector, Plane.XY)` (already exists for standard axes)
  2. For arbitrary axes: compute new orientation via `rotate_vector()` on each axis from `orient_axis()`, then `calculate_orientation()`
  3. Call `SmartSolid.orient(self, new_orient)` — uses direct call to avoid polymorphic dispatch to subclass overrides
  4. Apply position delta via `self.solid.moved(Location(tuple(delta)))` — orient() updates self.origin but doesn't move solid
  5. Remove `self.solid.moved(Location(rotation))` and `self.solid.rotate()` calls
- [x] Replace `self.origin = self.origin.rotate(axis, angle)` with orient()'s origin tracking — handled by `SmartSolid.orient()` so removed
- [x] Remove the `Rotation` import (no longer needed)
- [x] Verify `rotate_multi()` still works (it already delegates to `orient()` via `rotate_orientation`)
- [x] Run ALL existing tests — 655 passed

⚠️ **Key design decision**: `SmartSolid.orient(self, ...)` (direct call) instead of `self.orient(...)` (polymorphic) — subclass rotate() methods handle their own subsidiary objects (profiles, paths) separately. This avoids double-transformation bugs where orient() and rotate() both transform subsidiaries.

### Task 4: Refactor SweepSolid to avoid build123d rotate
Update SweepSolid to store original plane and use orientation-based approach.

- [x] Add `_original_plane_path` field to `SweepSolid.__init__()` — stores the initial plane at creation time
- [x] Update `SweepSolid.copy()` to copy `_original_plane_path`
- [x] Refactor `SweepSolid.orient()`:
  - Set `self.path.orientation = rotations` (already lightweight)
  - Reconstruct `self.plane_path` via `_rebuild_plane_path()` using `orient_plane()` from original
  - Plane origin = `self.origin + oriented_original_origin` (absolute, no cumulative errors)
- [x] Refactor `SweepSolid.rotate()` override:
  - Path: `path.orientation = self._orientation` + `path.moved(delta)` (same pattern as solid)
  - Plane: `_rebuild_plane_path()` from original
  - Removed `self.path.rotate(axis, angle)` (build123d Wire.rotate)
  - Removed `self.plane_path.rotated(axis, angle)` (build123d Plane.rotated — was buggy)
- [x] `SweepSolid.move()` unchanged — `_original_plane_path` is never modified; plane_path.origin += offset as before
- [x] Write tests: 12 new tests (consecutive rotations, orient idempotency, rotate(Axis) now works, orthonormality)
- [x] Run tests — 667 passed

### Task 5: Refactor SmartLoft to avoid build123d rotate
Update SmartLoft to use orientation-based approach.

- [x] Refactor `SmartLoft.orient()` — set profile orientations (unchanged, already uses `.orientation =`)
- [x] Refactor `SmartLoft.rotate()` override:
  - Replaced `self.base_profile.rotate(axis, angle)` with `.orientation + .moved(per-profile delta)`
  - Per-profile delta = `rotate_vector(old_center, axis, angle) - old_center` (needed because profiles are at different positions)
  - Added `rotate_vector` import from geometry
- [x] Existing tests verify SmartLoft rotate/orient consistency (14 tests including 3 from Task 1)
- [x] Run tests — 667 passed

### Task 6: Replace remaining build123d rotate calls
Update remaining files that use build123d's rotation methods.

- [x] Update `_rotate_plane_around_axis()` in `smartrevolve.py` — replaced with `rotate_plane()` from geometry.py; removed helper entirely
- [x] Update `SmartRevolve.create_plane_at()` — replaced `plane.rotated(self._orientation)` with `orient_plane()` from geometry.py
- [x] Update `Direction.rotate()` in `geometry.py` — replaced `self.value.rotate(axis, angle)` with `rotate_vector(self.value, axis, angle)`
- [x] Update `rotate_axis()` in `geometry.py` — replaced `axis.direction.rotate()` with `rotate_vector()`
- [x] Update `basket.py` line 194 — replaced `.solid.rotate(Axis.Z, ...)` with `.rotate(Axis.Z, ...).solid`
- [x] Write tests for Direction.rotate() using our math — 5 tests (4 parametrized + 360° return)
- [x] Run tests — 672 passed

### Task 7: Verify acceptance criteria
- [x] Verify no remaining calls to build123d `.rotate()` on any shape (Solid, Wire, Face, Vector) in src/ — confirmed, all `.rotate()` calls are our own SmartSolid/Direction methods
- [x] Verify no remaining calls to `Plane.rotated()` in src/ — only a docstring reference in geometry.py
- [x] Verify `_orientation` consistency across all rotate/orient/move combinations — covered by Task 1 tests (test_orientation_matches_solid_orientation)
- [x] Run full test suite — 672 passed
- [x] Grep for any remaining `.rotate(` calls and verify they are either our own methods or acceptable — all verified

### Task 8: Update documentation
- [x] Update comments in `smartsolid.py` about rotation approach — no stale rotation workaround comments found; existing comments (lines 260-263, 281-290) are accurate for the new approach
- [x] Update CLAUDE.md orientation note if needed — orientation note on line 143 is still accurate (user-facing behavior unchanged)

## Technical Details

### How rotate() → orient() delegation works
1. `rotate(Axis.Z, 45)` is called
2. Save `old_origin` before any changes
3. Compute new orientation: `new_orient = rotate_orientation(self._orientation, (0,0,45), Plane.XY)`
4. Call `SmartSolid.orient(self, new_orient)` (direct, non-polymorphic) which:
   - Undoes current orientation's effect on origin
   - Applies new orientation's effect on origin
   - Sets `self.solid.orientation = new_orient` (lightweight build123d property)
   - Sets `self._orientation = new_orient`
5. Compute position delta: `delta = self.origin - old_origin`
6. Move solid by delta: `self.solid.moved(Location(tuple(delta)))` (translation only)
7. For subclasses, their `rotate()` override handles subsidiary objects (path, profiles, etc.) after calling `super().rotate()`

### Arbitrary axis rotation
For non-X/Y/Z axes, compute new orientation by:
1. Get current axes: `x_axis, y_axis, z_axis = orient_axis(self._orientation)`
2. Rotate each axis around the arbitrary axis: `rotate_vector(axis.direction, arb_axis, angle)`
3. Compute new orientation: `calculate_orientation(new_x, new_y, new_z)`
4. Call `self.orient(new_orient)`

### SweepSolid plane tracking
Store `_original_plane_path` at creation. In `orient()`, reconstruct from original:
```python
self.plane_path = orient_plane(self._original_plane_path, rotations)
# Adjust origin for solid position
```
This avoids cumulative plane rotation errors from repeated `Plane.rotated()` calls.

### Build123d calls being replaced
| Current call | Replacement |
|---|---|
| `self.solid.rotate(axis, angle)` | `self.orient(new_orientation)` via `self.solid.orientation = ...` |
| `self.solid.moved(Location(Rotation(...)))` | `self.orient(new_orientation)` via `self.solid.orientation = ...` |
| `self.origin.rotate(axis, angle)` | Handled by `orient()` origin tracking |
| `self.path.rotate(axis, angle)` | `self.path.orientation = ...` (via SweepSolid.orient) |
| `self.plane_path.rotated(axis, angle)` | `orient_plane()` from geometry.py |
| `self.plane_path.rotated(rotations)` | `orient_plane()` from geometry.py |
| `self.base_profile.rotate(axis, angle)` | `self.base_profile.orientation = ...` (via SmartLoft.orient) |
| `plane.x_dir.rotate(axis, angle)` | `rotate_vector(plane.x_dir, axis, angle)` |
| `plane.rotated(self._orientation)` | `orient_plane(plane, orientation)` |
| `Direction.value.rotate(axis, angle)` | `rotate_vector(value, axis, angle)` |

## Post-Completion

**Manual verification:**
- Test with actual 3D models to verify visual correctness (especially models using rotation like basket.py, poweradapters.py)
- Compare performance of orientation-based approach vs old rotate approach
