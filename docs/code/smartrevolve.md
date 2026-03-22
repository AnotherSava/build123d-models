# SmartRevolve — Revolved Shapes

Creates 3D shapes by revolving a 2D face around an axis. Tracks the original sketch plane and axis through transformations, allowing retrieval of cross-section planes at any angular position along the revolve.

## Quick start

```python
from build123d import Axis, Plane
from sava.csg.build123d.common.pencil import Pencil
from sava.csg.build123d.common.smartrevolve import SmartRevolve

# Revolve a profile 360 degrees around Y to make a donut
pencil = Pencil(Plane.XZ, start=(10, 0))
pencil.arc_with_radius(3, 0, 180).arc_with_radius(3, 180, 180)
donut = pencil.revolve(360, Axis.Y)

# Revolve a rectangle 180 degrees for a half-pipe
pencil = Pencil(Plane.XZ, start=(5, 0))
pencil.right(2).up(3).left(2)
half_pipe = pencil.revolve(180, Axis.Y)

# Direct constructor (less common — prefer Pencil.revolve())
face = pencil.create_face()
shape = SmartRevolve(face, Axis.Z, 270, Plane.XZ)
```

## Creating with `Pencil.revolve()`

The easiest way to create a SmartRevolve. Draws a profile, then revolves it.

```python
pencil.revolve(angle=360, axis=Axis.Y, enclose=True, label=None)
```

| Parameter | Type | Description |
|-----------|------|-------------|
| `angle` | `float` | Revolve angle in degrees. Default `360`. |
| `axis` | `Axis` | Axis to revolve around. Default `Axis.Y`. |
| `enclose` | `bool` | Auto-close the profile before revolving. Default `True`. |
| `label` | `str` | Optional label for the solid. |

The profile must be offset from the revolve axis — if the profile crosses or touches the axis, the revolve will fail.

```python
# Bowl shape: half-circle revolved around Y
pencil = Pencil(Plane.XZ, start=(5, 0))
pencil.arc_with_radius(5, 0, 180)
bowl = pencil.revolve(360, Axis.Y)

# Partial revolve for a curved wall
pencil = Pencil(Plane.XZ, start=(20, 0))
pencil.right(2).up(30).left(2)
wall = pencil.revolve(90, Axis.Z)
```

## Direct constructor

```python
SmartRevolve(sketch, axis, angle, sketch_plane, label=None)
```

| Parameter | Type | Description |
|-----------|------|-------------|
| `sketch` | `Face` | The face to revolve. |
| `axis` | `Axis` | Axis to revolve around. |
| `angle` | `float` | Revolve angle in degrees. |
| `sketch_plane` | `Plane` | Plane of the original sketch (used for plane tracking). |
| `label` | `str` | Optional label. |

Use this when the face comes from somewhere other than a Pencil (e.g., a build123d `Rectangle` or imported face).

## Retrieving cross-section planes with `create_plane_at()`

Returns the sketch plane rotated to any position along the revolve. Correctly accounts for any transformations (move, rotate, orient) applied to the solid.

```python
revolve.create_plane_at(t)
```

| Parameter | Type | Description |
|-----------|------|-------------|
| `t` | `float` | Position along the revolve: `0.0` = start, `1.0` = end. |

```python
shape = pencil.revolve(180, Axis.Y)

# Get plane at the start (original sketch position)
start_plane = shape.create_plane_at(0.0)

# Get plane at the halfway point (90 degrees)
mid_plane = shape.create_plane_at(0.5)

# Get plane at the end (180 degrees)
end_plane = shape.create_plane_at(1.0)
```

This is useful for positioning other objects relative to points along the revolve, or for creating new sketches at specific angular positions.

## Transformations

SmartRevolve inherits all SmartSolid transformations. The tracked sketch plane and axis stay in sync through moves, rotations, and orientations — `create_plane_at()` always returns correct results.

```python
shape = pencil.revolve(270, Axis.Z)

# Move — plane tracking follows
shape.move(10, 20, 0)

# Rotate — planes reorient correctly
shape.rotate(Axis.Z, 45)

# Copy preserves all tracking state
shape_copy = shape.copy()
```

See [smartsolid.md](smartsolid.md) for the full list of inherited methods (alignment, booleans, filleting, bound box, etc.).
