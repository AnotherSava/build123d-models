# Pencil — 2D Sketching Guide

2D drawing tool for creating profiles via lines, arcs, and splines, then converting them to 3D shapes by extrusion, revolution, or mirroring. All drawing happens in a local 2D coordinate system on a plane.

## Quick start

```python
from sava.csg.build123d.common.pencil import Pencil

# L-shaped profile, extruded to 3D
bracket = Pencil()
bracket.right(20)
bracket.up(5)
bracket.left(5)
bracket.up(15)
bracket.left()
solid = bracket.extrude(10)

# Half-profile mirrored and extruded
pencil = Pencil()
pencil.right(15)
pencil.down(8)
pencil.right(5)
solid = pencil.extrude_mirrored_y(20)

# Revolved shape (torus-like)
pencil = Pencil(start=(30, 0))
pencil.arc_with_radius(5, -90, 180)
pencil.arc_with_radius(5, 90, 180)
solid = pencil.revolve(360, Axis.Y)
```

## Constructor

```python
Pencil(plane=Plane.XY, start=(0, 0))
```

| Parameter | Description |
|-----------|-------------|
| `plane` | Working plane for the sketch. Drawing uses the plane's local X/Y axes. Default: `Plane.XY` |
| `start` | Starting position in plane-local coordinates. Default: origin `(0, 0)` |

Common plane choices: `Plane.XY` (default), `Plane.XZ`, `Plane.YZ`, or any custom/rotated plane.

```python
# Draw in the XZ plane
pencil = Pencil(Plane.XZ)

# Start at an offset position
pencil = Pencil(start=(20, 0))

# Use a custom plane from another object
pencil = Pencil(pipe.create_path_plane(), (-radius, 0))
```

### `from_points` — Pencil from a vertex list

When you already have the polygon's vertices, skip the per-segment `draw`/`jump_to` calls:

```python
Pencil.from_points([(0, 0), (10, 0), (10, 5), (0, 5)], plane=Plane.XY)
```

The pencil starts at `points[0]` (the plane origin is shifted there) and adds one straight `Line` segment per subsequent point. The polygon auto-closes back to `points[0]` when you call `create_face` / `extrude`. Requires at least 2 points.

## Cardinal direction drawing

Move in straight lines along the local X/Y axes. Called without arguments, they return to 0 on that axis.

```python
pencil.right(10)       # +X by 10
pencil.left(5)         # -X by 5
pencil.up(8)           # +Y by 8
pencil.down(3)         # -Y by 3

pencil.right()         # go to X=0 (close horizontally)
pencil.left()          # go to X=0
pencil.up()            # go to Y=0
pencil.down()          # go to Y=0
```

### Absolute positioning

```python
pencil.x_to(25)        # move to X=25 (horizontal only)
pencil.y_to(10)        # move to Y=10 (vertical only)
pencil.right_to(25)    # same as x_to but asserts X increases
pencil.left_to(5)      # same as x_to but asserts X decreases
pencil.up_to(10)       # same as y_to but asserts Y increases
pencil.down_to(-5)     # same as y_to but asserts Y decreases
```

Each `_to` method accepts an optional second `angle` (degrees, same convention as
`draw` — CCW from +Y). When supplied, the move travels along that angle until it
reaches the target X (for `right_to`/`left_to`) or Y (for `up_to`/`down_to`) — the
orthogonal coordinate is computed from the angle:

```python
pencil.right_to(1.2294, -38.7829)  # diagonal until X=1.2294 (ends at ~(1.2294, 1.53))
pencil.up_to(10, 30)               # diagonal up-left until Y=10
pencil.left_to(0, 60)              # diagonal up-left until X=0
pencil.down_to(0, 150)             # diagonal down-left until Y=0
```

The angle must have a non-zero component along the locked direction (e.g. `right_to`
needs `sin(angle) < 0` so the +X component is positive), otherwise the target is
unreachable and the call asserts.

## `draw` — line at an angle

```python
pencil.draw(length, angle)
```

Draw a straight line of `length` at `angle` degrees (0 = +X, 90 = +Y, counterclockwise).

```python
pencil.draw(20, 45)     # diagonal line, 45 degrees up-right
pencil.draw(10, 180)    # same as left(10)
pencil.draw(4.5, 144)   # line at 144 degrees
```

## `jump` / `jump_to` — straight line to a point

```python
pencil.jump((dx, dy))           # line relative to current position
pencil.jump_to((x, y))          # line to absolute position
```

```python
# Diagonal step in a profile
pencil.jump((-5, -5))

# Return to a known position
pencil.jump_to((-thickness, 0))
```

## Arcs

### `arc` — three-point arc (relative)

```python
pencil.arc(midpoint_vector, destination_vector)
```

Both vectors are relative to the current position. The arc passes through all three points (start, midpoint, destination).

```python
pencil.arc((5, 5), (10, 0))    # arc bulging upward
```

### `arc_abs` — three-point arc (absolute)

```python
pencil.arc_abs(midpoint_abs, destination_abs)
```

Same as `arc` but midpoint and destination are in absolute coordinates.

### `arc_with_destination` — arc to point with specified angle

```python
pencil.arc_with_destination(destination, angle)
```

| Parameter | Description |
|-----------|-------------|
| `destination` | Target point relative to current position |
| `angle` | Arc angle in degrees. Positive = counter-clockwise (left), negative = clockwise (right) |

```python
# Arc curving left to reach a point
pencil.arc_with_destination((10, 15), 45)

# Arc curving right
pencil.arc_with_destination((10, 15), -45)
```

`arc_with_destination_abs` is the absolute-coordinate variant.

### `arc_with_radius` — arc from center offset

```python
pencil.arc_with_radius(radius, centre_angle, arc_degrees)
```

| Parameter | Description |
|-----------|-------------|
| `radius` | Distance from current position to arc center |
| `centre_angle` | Direction to arc center (degrees, 0 = +X) |
| `arc_degrees` | How far to sweep. Positive = extends the arc, sign determines direction |

```python
# Half-circle (180°) with center directly above
pencil.arc_with_radius(10, 90, 180)

# Quarter turn
pencil.arc_with_radius(5, -90, 90)
```

### `arc_with_vector_to_intersection` — arc constrained by tangent

```python
pencil.arc_with_vector_to_intersection(vector_to_tangents_intersection, angle)
```

Creates an arc where the tangent lines at start and end intersect at the given point. Useful for smoothly connecting angled sections.

### `double_arc` — S-curve to destination

```python
pencil.double_arc(destination, shift_coefficient=0.5, angle=None)
```

Draws two arcs with opposite curvatures to reach `destination`, creating a smooth S-curve.

| Parameter | Description |
|-----------|-------------|
| `destination` | Target point relative to current position |
| `shift_coefficient` | Where to split (0-1). 0.5 = equal arcs. Default: 0.5 |
| `angle` | Arc angle for each curve. None = auto-calculated |

```python
# Smooth transition between two horizontal levels
pencil.double_arc((10, 30))

# Control the split point (first arc shorter)
pencil.double_arc(-arc_destination_vector, 0.75)

# Connect two points with a smooth curve
pencil.double_arc(Vector(-thickness, height))
```

## Splines

### `spline` — smooth curve (relative)

```python
pencil.spline(destination, destination_tangent, intermediate_points=None, start_tangent=None)
```

| Parameter | Description |
|-----------|-------------|
| `destination` | Target point relative to current position |
| `destination_tangent` | Direction of the curve at the end point |
| `intermediate_points` | Optional points to pass through (relative) |
| `start_tangent` | Override start direction (default: auto from previous curve) |

```python
# Simple spline arriving horizontally
pencil.spline((50, 50), (1, 0))

# Spline through intermediate points
pencil.spline((50, 50), (1, 0), intermediate_points=[(20, 30), (40, 20)])

# Override start tangent
pencil.spline((50, 50), (1, 0), start_tangent=(0, 1))
```

`spline_abs` is the absolute-coordinate variant.

## Inline fillets

Call `.fillet(radius)` between drawing operations to round the corner at the current position. The fillet is applied when the next segment is added.

```python
# Fillet between two lines
pencil.right(10).fillet(2).up(10)

# Reuse the last radius (omit argument)
pencil.right(10).fillet(2).up(10).fillet().left(5)

# Multiple fillets in a complex profile
pencil = Pencil(Plane.YZ)
pencil.right(width / 2)
pencil.jump((offset, offset))
pencil.fillet(fillet_radius)
pencil.up_to(height)
pencil.fillet()
pencil.jump((-offset, -offset))
```

Note: `.fillet()` cannot be called before the first drawing operation. The radius is remembered — subsequent `.fillet()` calls without arguments reuse the last radius.

A trailing `.fillet()` (with no segment drawn after it) also works: it applies to the next implicitly drawn segment — the auto-close line of `create_wire(enclose=True)` / `create_face()` / `extrude()`, or the segment the mirrored-wire builders add to reach the mirror axis.

```python
# Rounds the corner at (10, 10) between the up-segment and the auto-close line
pencil.right(10).up(10).fillet(2).extrude(5)
```

## Creating geometry

### Wire

```python
wire = pencil.create_wire()           # auto-closes back to start
wire = pencil.create_wire(enclose=False)  # open wire (no closing segment)
```

Use open wires for paths (e.g., SweepSolid paths, ModelCutter wires).

### Face

```python
face = pencil.create_face()           # closed face (auto-encloses)
face = pencil.create_face(enclose=False)  # face from already-closed wire
```

### Mirrored face

Draw half of a symmetric profile, then mirror it to create a full closed face.

```python
# Mirror across local Y axis (symmetric left-right)
face = pencil.create_mirrored_face_y(center=0)

# Mirror across local X axis (symmetric top-bottom)
face = pencil.create_mirrored_face_x(center=0)
```

The `center` parameter shifts the mirror axis. Default is 0 (mirror at origin).

Corresponding wire methods: `create_mirrored_wire_x()`, `create_mirrored_wire_y()`.

## Extrusion

### Basic extrude

```python
solid = pencil.extrude(height)
solid = pencil.extrude(height, label="bracket")
```

Auto-closes the profile and extrudes it along the plane's normal direction. Returns a SmartSolid.

### Mirrored extrude

Draw half a profile, mirror it, and extrude in one step:

```python
# Mirror across Y axis, then extrude
solid = pencil.extrude_mirrored_y(height, center=0)

# Mirror across X axis, then extrude
solid = pencil.extrude_mirrored_x(height, center=0)
```

This is the most common pattern for symmetric profiles — draw one half and let the mirror complete it.

```python
# Typical symmetric profile
pencil = Pencil()
pencil.right(dim.top_length / 2)
pencil.down(dim.height)
pencil.right(dim.flange)
pencil.down(dim.lip)
pencil.left()
solid = pencil.extrude_mirrored_y(dim.depth)
```

## Revolve

```python
solid = pencil.revolve(angle=360, axis=Axis.Y, enclose=True, label=None)
```

Revolves the profile around an axis. Returns a SmartRevolve (which extends SmartSolid).

| Parameter | Description |
|-----------|-------------|
| `angle` | Revolution angle in degrees. Default: 360 (full revolution) |
| `axis` | Axis of revolution. Default: `Axis.Y` |
| `enclose` | Auto-close the profile. Default: True |

```python
# Full revolution (vase, cylinder, etc.)
pencil = Pencil()
pencil.right(20)
pencil.up(50)
pencil.left(10)
solid = pencil.revolve()

# Partial revolution (torus segment)
pencil = Pencil(Plane.XZ, start=(radius, 0))
pencil.arc_with_radius(tube_r, -90, 180)
pencil.arc_with_radius(tube_r, 90, 180)
torus = pencil.revolve(270, Axis.Z)
```

## Working in custom planes

All Pencil operations work in the plane's local coordinate system. The resulting geometry is automatically transformed to global coordinates.

```python
# Profile in the XZ plane (extrudes along Y)
pencil = Pencil(Plane.XZ)
pencil.right(20)
pencil.up(10)
pencil.left()
solid = pencil.extrude(30)

# Profile in the YZ plane
pencil = Pencil(Plane.YZ)
pencil.right(width / 2)
pencil.down(height)
pencil.left()
solid = pencil.extrude_mirrored_y(depth)

# Tilted plane
tilted = Plane.XY.rotated((30, 45, 15))
pencil = Pencil(tilted)
pencil.right(20)
pencil.up(10)
face = pencil.create_mirrored_face_x()
```

## Common recipes

### Wire path for SweepSolid

```python
path = Pencil(plane)
path.up(straight_length)
path.arc_with_radius(bend_radius, -90, -bend_angle)
path.draw(extra_distance, -bend_angle)
wire = path.create_wire(False)
# Use wire with SweepSolid
```

### Symmetric bracket

```python
pencil = Pencil()
pencil.right(base_width / 2)
pencil.up(wall_height).fillet(3)
pencil.left(lip_width)
solid = pencil.extrude_mirrored_y(depth)
```

### Revolved connector

```python
pencil = Pencil()
pencil.arc_with_radius(radius, 180, 90)
pencil.down(height - radius)
pencil.right()
solid = pencil.revolve(enclose=False)
```

## Inherited from SmartSolid

`.extrude()` and `.extrude_mirrored_x/y()` return SmartSolid instances. `.revolve()` returns a SmartRevolve. See `smartsolid.md` for the full fluent API (alignment, transforms, booleans, filleting, etc.).
