# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

A Python project for creating 3D models (primarily board game inserts and other designs) using the [build123d](https://github.com/gumyr/build123d) CAD framework. The project provides custom wrapper classes and utilities that simplify common 3D modeling operations.

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

- **Pencil**: 2D drawing tool for creating complex profiles via lines and arcs, then extruding/revolving them into 3D shapes

- **SweepSolid**: Creates 3D shapes by sweeping a 2D profile along a path

- **Exporter**: Exports models to 3MF format. Default output is `models/current_model.3mf`. Includes debug helpers (`show_red`, `show_blue`, `show_green`) for visualizing shapes

### Geometry Utilities (`geometry.py`)

- **Alignment**: Enum for positioning (Left/Center/Right relative to Left/Center/Right)
- **Direction**: Cardinal directions (N/S/E/W) with axis helpers
- Vector/rotation math utilities including `rotate_orientation` for fixed-axis rotations (vs build123d's object-attached rotations)

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
from sava.csg.build123d.common.exporter import Exporter

box = SmartBox(100, 50, 30)
box.fillet_z(5)
Exporter(box).export()
```

**Alignment system:** Use `align_x`, `align_y`, `align_z`, or `align` to position solids relative to each other or to origin (pass `None` as reference).

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

### Formatting

- Leave an empty line at the end of every file
