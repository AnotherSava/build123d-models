# Iris Diaphragm for Dispenser Bottle Mount

## Overview

Replace the fixed central hole in the dispenser bottle mount with a non-overlapping thick-blade iris diaphragm mechanism. Rotating the top ring relative to the bottom ring changes the aperture size, allowing the mount to grip pipes/bottles of varying diameters (25–35mm, potentially smaller). The iris uses 5 tall, rigid blades that fill the full height between the two rings (~20mm), providing enough contact area to hold a shampoo bottle vertically without tilting.

## Context

- Files involved:
  - Modify: `src/sava/csg/build123d/models/other/dispenserbottlemount.py` — add iris mechanism
  - Create: `src/sava/csg/build123d/models/other/iris.py` — parametric iris blade geometry generator
- Related patterns: SmarterCone for rings, Pencil for blade profiles, `.clone()` + `.rotate_z()` for replicating blades
- Dependencies: none beyond existing build123d framework

## Development Approach

- Testing approach: Visual verification with F3D viewer, plus unit tests for parametric geometry
- Complete each task fully before moving to the next
- **CRITICAL: tests cover common/reusable functionality (iris geometry generator), NOT end models** — models will continue evolving
- **CRITICAL: all tests must pass before starting next task**

## Design Notes

**Mechanism overview:**
Three part types: body ring (bottom), actuator ring (top), and K identical blades. Blades pivot around vertical posts on the body ring. Each blade has a drive pin on top that slides in an arc slot on the actuator ring. Rotating the actuator ring pushes all drive pins simultaneously, causing all blades to swing in unison — closing or opening the aperture.

**Blade geometry:**
Each blade is a tall paddle (~20mm height) shaped as an arc sector in XY, extruded in Z. The inner edge is curved to match pipe curvature at mid-range aperture. The pivot hole is near the outer edge. A drive pin (short cylinder) protrudes from the top surface, offset angularly from the pivot axis. The blade profile is drawn with Pencil (inner arc, outer arc, two connecting edges), then extruded to blade height.

**Pivot and drive mechanics:**
- Pivot: vertical cylindrical post on body ring floor, blade has a matching hole. Post height = blade height. Blade rotates freely around the post.
- Drive: short pin on blade top surface fits into an arc-shaped slot cut into actuator ring underside. Slot arc length determines the rotation range (and thus aperture range).
- Pin clearance: 0.2mm gap for PETG on 0.4mm nozzle FDM (Bambu P1S).

**Parametric dimensions (in `dimensions` dataclass):**
- `blade_count: int = 5` — number of iris blades
- `aperture_diameter_min: float = 25.0` — smallest aperture (mm)
- `aperture_diameter_max: float = 35.0` — largest aperture (mm)
- `pin_diameter: float = 3.0` — pivot and drive pin diameter
- `pin_clearance: float = 0.2` — gap between pin and hole/slot for print tolerance
- `blade_height: float` — blade height in Z (derived from ring gap by default, but overridable)
- `blade_thickness: float = 2.0` — blade thickness in radial direction at inner edge (wall thickness of the gripping surface)
- Derived: `pcd_radius` (pitch circle diameter for pivot posts), `blade_angular_span`, `drive_slot_arc_length`, `rotation_range`

**Ring modifications:**
- Bottom ring (body): central hole enlarged to accommodate blade sweep. Pivot posts added on a pitch circle. Floor remains solid (pipe rests on it if it reaches the bottom).
- Top ring (actuator): central hole enlarged similarly. Arc slots cut into underside for drive pins. Outer mounting geometry (dispenser grip, lip) unchanged.

**Aperture range geometry:**
At minimum aperture (25mm): blades are rotated maximally inward, inner edges form a roughly pentagonal opening approximating 25mm diameter. No gaps between adjacent blades.
At maximum aperture (35mm): blades are rotated outward, gaps appear between them. Pipe is constrained by 5 contact points — sufficient for centering and tilt prevention given 20mm blade height.

**Assembly:**
1. Place blades onto pivot posts on body ring (drop-in from above)
2. Press actuator ring on top, aligning drive pins with slot entries
3. No tools or glue needed

**Printability (Bambu P1S, 0.4mm nozzle, PETG):**
- Minimum wall thickness: 1.2mm (3 perimeters)
- Pin diameter: 3mm (prints reliably)
- Pin clearance: 0.2mm (standard for PETG moving parts)
- Blades print flat on bed (best layer adhesion for tall thin parts)
- Rings print upright (same as current model)

## Implementation Steps

### Task 1: Parametric iris blade geometry

**Files:**
- Create: `src/sava/csg/build123d/models/other/iris.py`

- [x] Define `IrisDimensions` dataclass with all parametric iris dimensions
- [x] Implement geometric calculations: PCD radius, blade angular span, pivot position, drive pin position, rotation range, slot arc length — all derived from the parametric inputs
- [x] Implement `create_blade()` — generates a single blade SmartSolid:
  - XY profile with Pencil: inner arc, outer arc, connecting edges, pivot hole
  - Extrude to blade height
  - Add drive pin cylinder on top surface
- [x] Implement `create_blades(rotation_angle)` — clones and rotates K blades around Z, with each blade rotated by its individual pivot angle based on the actuator rotation
- [x] Write tests: blade geometry at 0° rotation (closed), at max rotation (open), blade count parametric, aperture diameter at closed matches `aperture_diameter_min`
- [x] Run project test suite — cannot run in CI container (requires Windows + cadquery-ocp native CAD kernel); syntax verified, tests ready for local validation

### Task 2: Modified body ring (bottom) with pivot posts

**Files:**
- Modify: `src/sava/csg/build123d/models/other/dispenserbottlemount.py`

- [ ] Update `DispenserBottleMountDimensions` to include iris parameters (or reference `IrisDimensions`)
- [ ] Modify bottom ring creation: enlarge central opening to accommodate blade sweep area
- [ ] Add pivot posts on PCD — K cylinders protruding from the ring floor
- [ ] Verify pivot posts are correctly positioned and sized
- [ ] Visual verification with F3D
- [ ] Run project test suite — must pass before next task

### Task 3: Modified actuator ring (top) with drive slots

**Files:**
- Modify: `src/sava/csg/build123d/models/other/dispenserbottlemount.py`

- [ ] Modify top ring creation: enlarge central opening to match bottom ring
- [ ] Cut arc-shaped drive slots into underside of top ring — one per blade, positioned on the drive pin circle
- [ ] Slot dimensions: width = pin_diameter + 2*pin_clearance, arc length = rotation_range on drive pin circle
- [ ] Visual verification with F3D
- [ ] Run project test suite — must pass before next task

### Task 4: Assembly and export

**Files:**
- Modify: `src/sava/csg/build123d/models/other/dispenserbottlemount.py`

- [ ] Update `create()` to return body ring, actuator ring, and K blades
- [ ] Position all parts in assembled view for visualization (blades at mid-aperture)
- [ ] Update export to output all parts with labels: "bottom", "top", "blade" (single blade for printing K copies)
- [ ] Visual verification with F3D: check assembly fits, blades rotate freely in simulation, aperture range looks correct
- [ ] Run project test suite — must pass before next task

### Task 5: Verify acceptance criteria

- [ ] Visual test: export at min aperture — blades form tight polygon ~25mm
- [ ] Visual test: export at max aperture — blades open to ~35mm with gaps
- [ ] Visual test: assembly view — all parts fit together, no intersections
- [ ] Parametric test: change blade_count to 6, verify geometry adjusts
- [ ] Parametric test: change aperture range, verify geometry adjusts
- [ ] Run full test suite: `python -m pytest tests/`

### Task 6: Update documentation

- [ ] Update CLAUDE.md if internal patterns changed
- [ ] Move this plan to `docs/plans/completed/`
