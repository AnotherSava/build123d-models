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

### Core Classes (in `src/sava/csg/build123d/common/`)

- **SmartSolid**: Primary wrapper around build123d shapes. Provides:
  - Fluent API for transformations (move, rotate, scale, fillet, cut, fuse)
  - Alignment system using `Alignment` enum (LL, L, LR, CL, C, CR, RL, R, RR) for positioning relative to other solids
  - Bound box helpers (x_min, x_max, x_mid, y_size, etc.)
  - Support for both single solids and ShapeList collections

- **SmartBox**: Extends SmartSolid for box primitives with cutout operations

- **Pencil**: 2D drawing tool for creating complex profiles via lines and arcs, then extruding/revolving them into 3D shapes. Supports mirroring across axes in arbitrary planes (not just XY)

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

### Geometry Utilities (`geometry.py`)

- **Alignment**: Enum for positioning (Left/Center/Right relative to Left/Center/Right)
- **Direction**: Cardinal directions (N/S/E/W) with axis helpers
- Vector/rotation math utilities including `rotate_orientation` for fixed-axis rotations (vs build123d's object-attached rotations)
- **create_wire_tangent_plane()**: Creates a plane tangent to a wire at a specified position (0.0-1.0 parameter)
- **solidify_wire()**: Converts a wire to a 3D solid by sweeping a small circle along it (useful for visualization)

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
from build123d import Plane, Axis

# Works in any plane orientation, not just XY
tilted_plane = Plane.XY.rotated((30, 45, 15))
pencil = Pencil(tilted_plane)
pencil.draw(50, 45)
face = pencil.create_mirrored_face(Axis.X)  # Mirrors correctly in tilted plane
```

**Orientation note:** The `rotate()` method uses fixed axes (global coordinate system), while `orient()` uses build123d's default object-attached axes.

## Code Style Guidelines

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

### Type Hints

Always specify parameter and return types:

```python
def calculate_distance(point1: Vector, point2: Vector) -> float:
    return (point2 - point1).length

def create_boxes(count: int, size: float = 1.0) -> list[Box]:
    return [Box(size, size, size) for _ in range(count)]
```

### Import Organization

All imports at top of file. Order (with blank lines between groups):
1. Standard library (`import os`, `from typing import List`)
2. Third-party (`from build123d import Vector, Plane, Box`)
3. Local (`from sava.common.common import flatten`)

Inline imports only allowed for: circular import resolution, conditional imports, performance-critical lazy loading, type checking only.

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

### Refactoring Safety

- When changing field/function names, check all usages (including tests) and update accordingly
- Use search tools to find all references before making breaking changes
- Run all tests after refactoring
- **Backwards compatibility**: Don't worry too much about maintaining backwards compatibility for internal APIs. As long as you check all usages in the codebase (using Grep/search tools) and update them, breaking changes are fine. This is a personal project, not a public library.

### Git Workflow

- **IMPORTANT**: Do not create git commits unless explicitly asked by the user
- When the user requests commits, group related changes into logical, focused commits with clear messages
- Never mention "Claude Code" or AI assistance in commit messages
- Do not push to remote unless explicitly requested

### Windows Bash Commands

When running commands via Bash on Windows, always use forward slashes (`/`) in paths, not backslashes (`\`). Backslashes are interpreted as escape characters by bash and get stripped.

```bash
# Good
cd D:/projects/3d/build123d-models && ./venv/Scripts/python.exe -m pytest tests/

# Bad - backslashes will be stripped
D:\projects\3d\build123d-models\venv\Scripts\python.exe -m pytest tests/
```

### Formatting

- Leave an empty line at the end of every file
- Prefer single-line expressions over multi-line formatting. Keep expressions on one line even if they're long, rather than breaking them across multiple lines with parentheses.
  ```python
  # Good
  radius_at_bottom = self.dim.outer_radius_top * (1 - z_param_bottom) + self.dim.outer_radius_bottom * z_param_bottom

  # Avoid
  radius_at_bottom = (
      self.dim.outer_radius_top * (1 - z_param_bottom) +
      self.dim.outer_radius_bottom * z_param_bottom
  )
  ```

  **Exception**: Multi-line formatting is acceptable when creating objects or calling functions with all parameters as named parameters:
  ```python
  # Acceptable
  thread = IsoThread(
      major_diameter=major_diameter,
      pitch=pitch,
      length=height,
      external=False,
      end_finishes=("chamfer", "fade")
  )

  # Also acceptable for single-line if not too long
  thread = IsoThread(major_diameter=major_diameter, pitch=pitch, length=height, external=False, end_finishes=("chamfer", "fade"))
  ```
