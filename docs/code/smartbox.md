# SmartBox — Box Primitives Guide

Box primitive with optional tapering support. Creates rectangular solids where the top face can differ in size from the base, producing frustum shapes. Inherits all fluent API methods from SmartSolid (see `smartsolid.md`).

## Quick start

```python
from sava.csg.build123d.common.smartbox import SmartBox

# Simple box: length 100, width 80, height 50
box = SmartBox(100, 80, 50)

# Tapered box: base 100x80, top 90x70
tapered = SmartBox(100, 80, 50, tapered_length=90, tapered_width=70)

# Tapered box defined by wall angles (80 degrees from horizontal)
angled = SmartBox.with_base_angles_and_height(100, 80, 50, 80, 80)
```

## Constructor

```python
SmartBox(length, width, height, tapered_length=None, tapered_width=None, plane=Plane.XY, label=None)
```

| Parameter | Description |
|-----------|-------------|
| `length` | X dimension at the base |
| `width` | Y dimension at the base |
| `height` | Z dimension |
| `tapered_length` | X dimension at the top (defaults to `length`) |
| `tapered_width` | Y dimension at the top (defaults to `width`) |
| `plane` | Plane to create the box in (default: XY) |
| `label` | Optional label for export logging |

The box is always centered on X and Y, with its base at Z=0.

## Class methods

### `with_base_angles_and_height`

Define tapering by wall angles instead of explicit top dimensions.

```python
SmartBox.with_base_angles_and_height(length, width, height, angle_length, angle_width)
```

| Parameter | Description |
|-----------|-------------|
| `angle_length` | Angle of length-direction walls from horizontal (90 = vertical, <90 = inward taper) |
| `angle_width` | Angle of width-direction walls from horizontal (90 = vertical, <90 = inward taper) |

```python
# 10-degree inward taper on all walls
box = SmartBox.with_base_angles_and_height(100, 80, 50, 80, 80)

# Vertical length walls, tapered width walls
box = SmartBox.with_base_angles_and_height(100, 80, 50, 90, 75)
```

### `with_delta`

Create a tapered box where the top is offset by a uniform delta on each side.

```python
SmartBox.with_delta(length, width, height, delta)
```

Positive delta makes the top larger, negative makes it smaller. The top dimensions become `length + 2*delta` and `width + 2*delta`.

```python
# Top is 4mm smaller on each axis (2mm inset per side)
box = SmartBox.with_delta(100, 80, 50, -2)
```

## Tapering queries

For tapered boxes, query dimensions at any height:

```python
box = SmartBox(100, 80, 50, tapered_length=80, tapered_width=60)

box.tapered              # True — whether box is tapered
box.slope_length         # rate of length change per unit height: (80-100)/50 = -0.4
box.slope_width          # rate of width change per unit height: (60-80)/50 = -0.4
box.length_at(0.5)       # length at half height: 90
box.width_at(0.5)        # width at half height: 70
box.center(0.5)          # center point at half height: Vector(0, 0, 25)
```

## `create_offset`

Create a new box with dimensions adjusted by per-direction offsets. Positive = outward (larger), negative = inward (smaller). Correctly accounts for taper when adjusting dimensions.

```python
# Uniform offset: expand by 2mm on all sides
bigger = box.create_offset(2)

# Per-direction: expand east/west, shrink top
adjusted = box.create_offset(0, east=2, west=2, up=-5)

# Common pattern: create an inner cavity
inner = outer.create_offset(-wall_thickness)
```

| Parameter | Direction |
|-----------|-----------|
| `north` | +Y wall |
| `south` | -Y wall |
| `east` | +X wall |
| `west` | -X wall |
| `up` | +Z (top) |
| `down` | -Z (bottom) |

Each direction defaults to the base `offset` value if not specified.

## `create_shell`

Create a hollow shell by cutting between the box and an offset box.

```python
# Hollow box with 2mm walls (cut interior)
shell = box.create_shell(-2)

# Per-direction wall thickness
shell = box.create_shell(-2, up=0)  # open top

# Outer shell (expand outward)
outer_shell = box.create_shell(2)
```

All non-zero offsets must have the same sign:
- Negative: creates inner box, subtracts from self (hollow interior)
- Positive: creates outer box, subtracts self from it (shell around original)

## `add_cutout`

Cut a rectangular notch into a wall of the box, with optional filleted edges.

```python
box.add_cutout(direction, length, radius_bottom=0, radius_top=None, width=None, height=None, shift=0)
```

| Parameter | Description |
|-----------|-------------|
| `direction` | Which wall: `Direction.N`, `S`, `E`, `W` |
| `length` | Size of the cutout along the wall |
| `radius_bottom` | Fillet radius at the bottom corners |
| `radius_top` | Fillet radius at the top edge (defaults to `radius_bottom`) |
| `width` | Depth of the cutout into the box (defaults to full width along that axis) |
| `height` | Height of the cutout from bottom (defaults to full height) |
| `shift` | Offset the cutout along the wall from center |

```python
from sava.csg.build123d.common.geometry import Direction

# Full-height cutout on the south wall with filleted edges
box.add_cutout(Direction.S, 30, radius_bottom=3, height=box.z_size)

# Partial-height cutout on the west wall, limited depth
box.add_cutout(Direction.W, 20, radius_bottom=2, width=15, height=25)

# Cutout shifted off-center
box.add_cutout(Direction.N, 30, radius_bottom=3, height=box.z_size, shift=10)
```

## Inherited from SmartSolid

SmartBox inherits the full SmartSolid API. See `smartsolid.md` for:

- Alignment (`.align()` builder, `align_x/y/z`, Alignment enum)
- Transformations (move, rotate, scale, mirror)
- Boolean operations (cut, fuse, intersect)
- Cutting helpers (cut_x/y/z)
- Filleting (fillet_x/y/z, fillet_by)
- Bound box properties (x_min/mid/max, x_size, etc.)
- Clone, pad, color
