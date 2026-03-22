# High-Level Class Documentation

## Overview

Create a complete set of usage guides in `docs/code/` for the project's high-level 3D modeling classes. These docs serve as Claude Code's reference when building/updating models — they describe *when* and *how* to use each class with practical examples. The existing `smartercone.md` sets the tone: recipe-oriented, concise, example-heavy.

## Context

- Files involved:
  - Create: `docs/code/smartsolid.md` — shared fluent API (alignment, transforms, cuts, fillets, booleans, bound box)
  - Create: `docs/code/smartbox.md` — box primitives with tapering and cutouts
  - Create: `docs/code/pencil.md` — 2D sketching tool for profiles
  - Create: `docs/code/smartloft.md` — lofted shapes between profiles
  - Create: `docs/code/smartrevolve.md` — shapes from revolving faces
  - Create: `docs/code/sweepsolid.md` — shapes from sweeping profiles along paths
  - Create: `docs/code/smartsphere.md` — sphere primitives
  - Modify: `docs/code/smartercone.md` — align structure with other docs
  - Modify: `CLAUDE.md` — add docs/code/ pointer, high-level primitives guideline, alignment preference
- Related patterns: existing `docs/code/smartercone.md` as style reference (feel free to improve the style as you go)
- Source files: all in `src/sava/csg/build123d/common/`

## Development Approach

- Primarily documentation, no tests needed. However, if code comments or docstrings are found to be outdated, update/extend them.
- Complete each doc fully before moving to the next
- Read the source file and check usages across the codebase before writing each doc to ensure accuracy and discover real-world patterns
- Each doc follows a similar structure (see Design Notes), adapted to each class's needs

## Design Notes

**Document structure (consistent across all docs):**
Each doc follows this template:
1. Title + one-line description
2. Quick start (2-3 minimal examples)
3. Core API sections with parameter tables and examples
4. Cross-reference to `smartsolid.md` for inherited methods

**Alignment emphasis:**
`smartsolid.md` gives alignment a prominent section. The `.align()` builder is presented as the recommended approach for positioning. The Alignment enum (LL/L/LR/CL/C/CR/RL/R/RR) is explained with a visual/conceptual model. Convenience methods (`align_x`, `align_xy`, etc.) can be used in simple cases but `.align()` is the default recommendation.

**CLAUDE.md updates:**
- Add a pointer to `docs/code/` directory as the authoritative usage reference
- Add guideline: keep `docs/code/` docs up to date after any changes to the corresponding source code
- Add guideline: prefer high-level primitives (SmartBox, SmarterCone, SmartSphere, Pencil, SmartLoft, SmartRevolve, SweepSolid) over raw build123d primitives unless there's a significant reason not to
- Add guideline: use `.align()` and alignment operations for positioning objects rather than manual coordinate math

**What NOT to document:**
- Internal/private methods (underscore-prefixed). If methods that feel internal lack the underscore convention, feel free to rename them.
- Legacy classes (SmartCone — superseded by SmarterCone)
- Implementation details — focus on usage patterns

**Tone:**
- Recipe-oriented: "here's how to do X" not "this method accepts parameters..."
- Short examples that can be copy-pasted
- Parameter tables for methods with multiple options
- No exhaustive API reference — just the patterns a model-builder needs
- Documents must be both user-friendly (readable by a human) and efficiently usable by Claude Code as a reference when generating model code

## Implementation Steps

### Task 1: SmartSolid doc (foundation)

**Files:**
- Create: `docs/code/smartsolid.md`
- Read: `src/sava/csg/build123d/common/smartsolid.py`, `alignmentbuilder.py`, `geometry.py` (Alignment enum)

- [x] Read source files for current API
- [x] Write `smartsolid.md` covering:
  - Quick start (create, transform, export)
  - **Alignment** (prominent section): `.align()` builder as primary, Alignment enum explained, examples of common positioning tasks
  - Transformations: move, rotate, orient, scale, mirror, copy
  - Boolean operations: cut, fuse, intersect
  - Cutting helpers: cut_x/y/z with cut/cut_fraction/keep/keep_fraction
  - Filleting: fillet_x/y/z, fillet_by with filters
  - Bound box properties: x_min/mid/max, x_size, etc.
  - clone, pad, color
  - Mutating vs non-mutating convention (verb vs verbed)

### Task 2: SmartBox doc

**Files:**
- Create: `docs/code/smartbox.md`
- Read: `src/sava/csg/build123d/common/smartbox.py`

- [x] Read source file
- [x] Write `smartbox.md` covering:
  - Quick start (basic box, tapered box)
  - Constructor and class methods (with_base_angles_and_height, with_delta)
  - Tapering: slopes, dimension queries (length_at, width_at, center)
  - create_offset, create_shell
  - add_cutout with directions
  - Reference to smartsolid.md for inherited methods

### Task 3: Pencil doc

**Files:**
- Create: `docs/code/pencil.md`
- Read: `src/sava/csg/build123d/common/pencil.py`

- [x] Read source file
- [x] Write `pencil.md` covering:
  - Quick start (draw a profile, extrude it)
  - Drawing primitives: right/left/up/down, jump/jump_to, draw, x_to/y_to
  - Arcs: arc, arc_abs, arc_with_destination, arc_with_radius, double_arc
  - Splines: spline, spline_abs
  - Inline fillets: fillet() between drawing operations
  - Creating geometry: create_wire, create_face, create_mirrored_face_x/y
  - Extrusion: extrude, extrude_mirrored_x/y
  - Revolve: revolve()
  - Custom planes: working in non-XY planes

### Task 4: SmartLoft doc

**Files:**
- Create: `docs/code/smartloft.md`
- Read: `src/sava/csg/build123d/common/smartloft.py`

- [x] Read source file
- [x] Write `smartloft.md` covering:
  - Quick start (loft between two profiles)
  - SmartLoft.create(base, target, height)
  - SmartLoft.extrude(profile, amount, direction)
  - Profile tracking through transformations
  - Reference to smartsolid.md for inherited methods

### Task 5: SmartRevolve doc

**Files:**
- Create: `docs/code/smartrevolve.md`
- Read: `src/sava/csg/build123d/common/smartrevolve.py`

- [x] Read source file
- [x] Write `smartrevolve.md` covering:
  - Quick start (revolve a face)
  - Constructor parameters (sketch, axis, angle, sketch_plane)
  - create_plane_at(t) for accessing cross-sections
  - Typical workflow: Pencil → face → SmartRevolve
  - Reference to smartsolid.md for inherited methods

### Task 6: SweepSolid doc

**Files:**
- Create: `docs/code/sweepsolid.md`
- Read: `src/sava/csg/build123d/common/sweepsolid.py`

- [x] Read source file
- [x] Write `sweepsolid.md` covering:
  - Quick start (sweep a profile along a path)
  - Constructor parameters (sketch, path, path_plane)
  - Path plane methods: create_path_plane, create_plane_start/end
  - Typical workflow: create Wire path, create profile, sweep
  - Reference to smartsolid.md for inherited methods

### Task 7: SmartSphere doc

**Files:**
- Create: `docs/code/smartsphere.md`
- Read: `src/sava/csg/build123d/common/smartsphere.py`

- [x] Read source file
- [x] Write `smartsphere.md` covering:
  - Quick start (solid sphere, hollow sphere, hemisphere)
  - Constructor: radius, internal_radius, angle
  - create_hollow class method
  - create_offset, create_shell
  - create_sphere, create_inner_sphere, create_outer_sphere
  - Reference to smartsolid.md for inherited methods

### Task 8: Update SmarterCone doc

**Files:**
- Modify: `docs/code/smartercone.md`

- [x] Review current doc against source code for accuracy
- [x] Ensure structural consistency with other docs (title format, section ordering)
- [x] Add "See smartsolid.md for inherited methods" reference if missing
- [x] Verify all examples are still correct

### Task 9: Update CLAUDE.md

**Files:**
- Modify: `CLAUDE.md`

- [x] Add pointer to `docs/code/` as the detailed usage reference for high-level classes
- [x] Add guideline: prefer high-level primitives (SmartBox, SmarterCone, SmartSphere, Pencil, SmartLoft, SmartRevolve, SweepSolid) over raw build123d when building models
- [x] Add guideline: use `.align()` builder and alignment operations for positioning objects — avoid manual coordinate math
- [x] Ensure existing class descriptions in CLAUDE.md don't contradict the new docs

### Task 10: Verify acceptance criteria

- [x] All 8 docs exist in `docs/code/` and follow consistent structure
- [x] Each doc accurately reflects current source code API
- [x] CLAUDE.md points to docs/code/ and includes high-level primitives + alignment guidelines
- [x] Move this plan to `docs/plans/completed/`
