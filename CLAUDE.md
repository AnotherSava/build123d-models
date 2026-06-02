# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

A Python project for creating 3D models (primarily board game inserts and other designs) using the [build123d](https://github.com/gumyr/build123d) CAD framework. The project provides custom wrapper classes and utilities that simplify common 3D modeling operations.

## Build123d Direct API

This project heavily uses the build123d library and particularly its **Direct API**. When working with this codebase, familiarize yourself with the Direct API documentation:

**[Build123d Direct API Reference](https://build123d.readthedocs.io/en/stable/direct_api_reference.html)**

The Direct API provides the fundamental primitives (Box, Cylinder, Sphere, etc.) and operations (fillet, chamfer, extrude, etc.) that this project's custom classes (SmartSolid, SmartBox, Pencil) wrap and extend.

## Commands

**Run all tests:**
```bash
python -m pytest tests/
```

**Run a single test file:**
```bash
python -m pytest tests/sava/csg/build123d/common/test_smartsolid.py
```

**Run a specific test:**
```bash
python -m pytest tests/sava/csg/build123d/common/test_smartsolid.py::TestSmartSolidBoundBox::test_get_bound_box_standard_planes
```

**View model output:** Use F3D viewer with auto-reload:
```bash
f3d models/current_model.3mf --watch --opacity=0.6
```

## Architecture

> **Detailed usage guides** for each class live in `docs/code/` (e.g. `docs/code/smartsolid.md`, `docs/code/smartbox.md`). Consult those when building or updating models — they contain practical examples, parameter tables, and recommended patterns.

### Core Classes (in `src/sava/csg/build123d/common/`)

- **SmartSolid**: Primary wrapper around build123d shapes. Provides:
  - Fluent API for transformations (move, rotate, scale, fillet, cut, fuse)
  - Alignment system using `Alignment` enum (LL, L, LR, CL, C, CR, RL, R, RR) for positioning relative to other solids
  - Bound box helpers (x_min, x_max, x_mid, y_size, etc.)
  - Support for both single solids and ShapeList collections
  - Cut helpers (`cut_x`, `cut_y`, `cut_z`): trim along an axis using `cut` (absolute to remove), `cut_fraction` (fraction to remove), `keep` (absolute to keep), or `keep_fraction` (fraction to keep)

- **SmartBox**: Extends SmartSolid for box primitives with cutout operations. Supports per-side tapering (independent wall angles or symmetric top dimensions), producing frustum/wedge shapes with a possibly off-center top. Construction math (parameter resolution, solid building, offset geometry) lives in `boxgeometry.py`

- **Pencil**: 2D drawing tool for creating complex profiles via lines and arcs, then extruding/revolving them into 3D shapes. Supports mirroring across axes in arbitrary planes (not just XY)

- **SmarterCone**: Cone/cylinder builder with fluent API. Provides:
  - Builder pattern: `SmarterCone.base(radius).extend(radius=, height=, angle=)` for chaining sections
  - Supports negative heights (cone extends in -Z direction)
  - `extend()` parameter combinations: (radius+height), (angle+height), (angle+radius), (radius only — radius step at same height), (height only), (no params — inner-only step, chain `.inner()` to change only inner radius)
  - `angle` convention: positive = inward (radius decreases), negative = outward (radius increases)
  - Shell creation (`create_shell`), offset (`create_offset`), inner/outer extraction
  - Shift support for off-axis sections
  - Fillet at section junctions
  - `InnerMode` enum controls how `extend()` auto-propagates inner radius:
    - `THICKNESS` (default): preserves wall thickness (outer - inner)
    - `RADIUS`: preserves inner radius and inner shifts as-is
    - Set via `inner(radius, mode=InnerMode.RADIUS)`

- **SmartSphere**: Sphere primitive with inner/outer shell creation and SmartSolid transformations

- **SmartLoft**: Creates 3D shapes by lofting between two profiles or extruding a profile along a direction

- **SmartRevolve**: Creates 3D shapes by revolving a 2D face around an axis

- **SweepSolid**: Creates 3D shapes by sweeping a 2D profile along a path

- **ModelCutter** (`modelcutter.py`): Advanced cutting system for splitting models along wire paths
  - `CutSpec`: Dataclass defining a cut (wire path, plane orientation, optional thickness)
  - `cut_with_wires()`: Cuts a model into pieces along one or more wires
    - Thin cuts (thickness=0): Split model without removing material
    - Thick cuts (thickness>0): Remove a slice of material along the wire AND split into separate pieces
    - Progressive cutting: Each cut subdivides all existing pieces
    - Properly handles disconnected solids after material removal
  - Uses `create_wire_tangent_plane()` from geometry.py to orient cutting planes

- **Exporter**: Exports models to 3MF format. Default output is `models/current_model.3mf`. Includes debug helpers (`show_red`, `show_blue`, `show_green`) for visualizing shapes

### Mesh Reconstruction (`src/sava/csg/build123d/reconstruct/`)

Convert 2.5D-extrudable STL/OFF meshes into authored Pencil + build123d code. Research-stage; aborts with a reason when the input isn't 2.5D. Public API: `reconstruct(path) -> ReconstructionResult`. See `docs/code/reconstruct/` for algorithm, findings, and the iris-blade reference test.

### Geometry Utilities (`geometry.py`)

- **Alignment**: Enum for positioning (Left/Center/Right relative to Left/Center/Right)
- **Direction**: Cardinal directions (N/S/E/W) with axis helpers
- Vector/rotation math utilities including `rotate_orientation` for fixed-axis rotations (vs build123d's object-attached rotations)
- **create_wire_tangent_plane()**: Creates a plane tangent to a wire at a specified position (0.0-1.0 parameter)
- **solidify_wire()**: Converts a wire to a 3D solid by sweeping a small circle along it (useful for visualization)
- **are_points_too_close()**: Use this function when comparing points/vectors/vertices for equality instead of direct comparison or manual distance checks

### Project Structure

```
src/sava/csg/build123d/
├── common/           # Core utilities and base classes
└── models/           # Actual 3D model definitions
    ├── common/       # Shared model components
    ├── inserts/      # Board game inserts (e.g., grand_austria_hotel/)
    └── other/        # Other models (hydroponics/, poweradapters.py)
```

## Key Patterns

**Creating and exporting a model:**
```python
from sava.csg.build123d.common.smartbox import SmartBox
from sava.csg.build123d.common.exporter import export, save_3mf

box = SmartBox(100, 50, 30)
box.fillet_z(5)
export(box)
save_3mf()
```

**Exporting multiple shapes with labels:**
```python
export(main_body, "body")
export(screw, "screw")
save_3mf()  # Single 3MF with all shapes
save_stl()  # Separate STL files: body.stl, screw.stl
```

**Alignment system:** Use `align_x`, `align_y`, `align_z`, or `align` to position solids relative to each other or to origin (pass `None` as reference).

**Cutting models along wires:**
```python
from sava.csg.build123d.common.modelcutter import cut_with_wires, CutSpec
from sava.csg.build123d.common.geometry import create_wire_tangent_plane
from build123d import Wire, Line

model = SmartBox(100, 50, 30)
wire = Wire([Line((50, 0, 0), (50, 50, 30))])
plane = create_wire_tangent_plane(wire, 0.0)

# Thin cut (split into pieces)
pieces = cut_with_wires(model, CutSpec(wire, plane))

# Thick cut (remove material)
pieces = cut_with_wires(model, CutSpec(wire, plane, thickness=2.0))

# Multiple cuts
wire2 = Wire([Line((0, 25, 0), (100, 25, 30))])
plane2 = create_wire_tangent_plane(wire2, 0.0)
pieces = cut_with_wires(model, CutSpec(wire, plane), CutSpec(wire2, plane2))
```

**Pencil mirroring in custom planes:**
```python
from sava.csg.build123d.common.pencil import Pencil
from build123d import Plane

# Works in any plane orientation, not just XY
tilted_plane = Plane.XY.rotated((30, 45, 15))
pencil = Pencil(tilted_plane)
pencil.right(20)
pencil.up(10)
face = pencil.create_mirrored_face_x()  # Mirrors correctly in tilted plane
```

**Orientation note:** The `rotate()` method uses fixed axes (global coordinate system), while `orient()` uses build123d's default object-attached axes.

### Prefer high-level primitives

When building models, prefer the project's high-level classes (SmartBox, SmarterCone, SmartSphere, Pencil, SmartLoft, SmartRevolve, SweepSolid) over raw build123d primitives (Box, Cylinder, Sphere, etc.). The high-level classes provide alignment, fluent transformations, and consistent patterns. Only drop down to raw build123d when the high-level API doesn't cover your use case.

### Use alignment for positioning

Use `.align()` and alignment operations (`align_x`, `align_y`, `align_z`) for positioning objects relative to each other. Avoid manual coordinate math — the alignment system handles bounding-box-relative positioning cleanly. See `docs/code/smartsolid.md` for full alignment documentation.

### Build in scene (visualization) orientation

Each `create_*` method should return its part in the orientation that reads best in the **assembled scene** — how the part sits relative to the others when you view the whole model. That natural state is what flows into the assembled 3MF view, and it's what makes the `show_red` / `show_green` / `show_blue` debug helpers overlay where you expect.

Do **not** build in print orientation. If a part prints better in a different pose (flat face on the bed, no overhangs), set its `bed_orientation` (a rotation vector) on the SmartSolid. Export applies `bed_orientation` **only when writing STL** — so the part still visualizes in scene pose but slices ready-to-print. Leave `bed_orientation` unset when the scene pose already prints fine.

Achieve the scene orientation natively in the Pencil trace (choose the start point and direction so the geometry comes out posed correctly) — don't build in some other orientation and then `rotate_x`/`move` it after.

**Export flow** (see `tray.py` / `splitter.py`): arrange the parts into their assembled positions and `save_3mf(...)` **first** (the visualization scene, with colors), then `clear()`, then export the parts in their print layout and `save_stl(...)` (which applies each part's `bed_orientation`). Exporting 3MF first gives the assembled debug view; the `clear()` between prevents the STL pass from duplicating shapes into the 3MF.

## Code Style

### Model Dimensions

Each geometric model must include a `dimensions` dataclass defining every numeric measurement. No geometry constants should be hardcoded; reference `dim.<field>` instead. Preferred orientation: `length` >= `width`.

```python
@dataclass
class MyModelDimensions:
    length: float = 100.0
    width: float = 50.0
    height: float = 25.0

def make_my_model(dim: MyModelDimensions):
    base = Box(dim.length, dim.width, dim.height)
```

### Testing

- Prefer parametrized tests over separate test functions
- Always run newly created tests to verify they work
- Use the virtual environment: `venv/Scripts/python.exe`

```python
@pytest.mark.parametrize("input,expected", [
    (5, [5]),
    ([1, 2, 3], [1, 2, 3]),
    ([1, [2, 3], 4], [1, 2, 3, 4]),
])
def test_flatten(input, expected):
    assert list(flatten(input)) == expected
```

### Refactoring

- After modifying code, update any related documentation in `docs/code/`, comments, and docstrings to stay in sync
- **Backwards compatibility**: Don't worry about maintaining backwards compatibility for internal APIs. As long as you check all usages and update them, breaking changes are fine. This is a personal project, not a public library.

### Git Workflow

- When the user requests commits, group related changes into logical, focused commits with clear messages
- Put model file (.stl and .3mf) changes into the same commit as the code changes for that model
