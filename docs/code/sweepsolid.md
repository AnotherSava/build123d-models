# SweepSolid — Swept Shapes

Creates 3D shapes by sweeping a 2D profile along a wire path. Tracks the path plane through transformations, allowing retrieval of planes at the start, end, or any position along the path.

## Quick start

```python
from build123d import Edge, Wire, Circle, Plane, Polyline
from sava.csg.build123d.common.sweepsolid import SweepSolid

# Sweep a circle along a straight line to make a tube
edge = Edge.make_line((0, 0, 0), (0, 0, 50))
wire = Wire([edge])
tube = SweepSolid(Circle(5), wire, Plane.XZ)

# Sweep along a multi-segment path
path = Polyline((0, 0, 0), (20, 0, 0), (20, 0, 20))
tube = SweepSolid(Circle(3), path, Plane.XZ)

# Use Pencil for curved paths
from sava.csg.build123d.common.pencil import Pencil

pencil = Pencil(Plane.XZ)
pencil.up(15)
pencil.arc_with_radius(20, -90, -60)
pencil.draw(10, -60)
wire = pencil.create_wire(False)
pipe = SweepSolid(Circle(4), wire, Plane.XZ)
```

## Constructor

```python
SweepSolid(sketch, path, path_plane, label=None)
```

| Parameter | Type | Description |
|-----------|------|-------------|
| `sketch` | `SweepType` | 2D profile to sweep (e.g., `Circle`, `Face`). |
| `path` | `Wire` | Wire path to sweep along. |
| `path_plane` | `Plane` | Plane containing the wire path — used for plane tracking through transformations. |
| `label` | `str` | Optional label for the solid. |

The `path_plane` should be the plane in which the wire path was drawn. This is critical for correct behavior of `create_path_plane()`, `create_plane_start()`, and `create_plane_end()` after transformations.

## Retrieving planes along the path

SweepSolid tracks the path plane through all transformations (move, rotate, orient). These methods return planes that stay in sync with the object's current position and orientation.

### `create_path_plane()`

Returns the path plane, transformed with the object. Useful for drawing new profiles relative to the sweep path.

```python
pipe = SweepSolid(Circle(4), wire, Plane.XZ)
pipe.move(10, 20, 0)

# Path plane origin has moved with the object
path_plane = pipe.create_path_plane()
```

### `create_plane_start()` / `create_plane_end()`

Returns a plane tangent to the wire at the start or end, with x-axis aligned to the path plane. These are useful for attaching other objects at the endpoints of the sweep.

```python
pipe = SweepSolid(Circle(4), wire, plane)

# Attach a connector at the end of the pipe
end_plane = pipe.create_plane_end()
connector.solid.location = Location(end_plane)

# Get the starting plane
start_plane = pipe.create_plane_start()
```

Real-world usage — position a connector at the pipe end:

```python
pipe_outer = SweepSolid(Circle(dim.radius_outer), wire, plane)
end_plane = pipe_outer.create_plane_end()

connector.solid.location = Location(end_plane)
connector.rotate_multi((180, 0, 0), end_plane)
connector.align_z(pipe_outer, Alignment.RR, 0, end_plane)
```

## Typical workflow

1. Create the wire path (straight edges, polylines, or Pencil-drawn curves)
2. Create a 2D profile sketch (Circle, Face, etc.)
3. Construct the SweepSolid with the sketch, path, and the plane the path lives in
4. Use plane methods to attach other objects at endpoints

```python
# Bent pipe with connectors at both ends
dim = PipeDimensions()
plane = Plane.XZ

# Draw the path with Pencil
path = Pencil(plane)
path.up(dim.length_straight)
path.arc_with_radius(dim.bend_radius, -90, -dim.bend_angle)
path.draw(dim.extra_distance, -dim.bend_angle)
wire = path.create_wire(False)

# Create outer and inner pipes
pipe_outer = SweepSolid(Circle(dim.radius_outer), wire, plane)
pipe_inner = SweepSolid(Circle(dim.radius_inner), wire, plane)
pipe_inner.solid.position = pipe_outer.solid.position
```

## Transformations

SweepSolid inherits all SmartSolid transformations. The tracked path, path plane, and endpoint planes stay in sync through moves, rotations, and orientations.

```python
pipe = SweepSolid(Circle(4), wire, Plane.XZ)

# Move — path and planes follow
pipe.move(10, 20, 0)

# Rotate — path and planes reorient correctly
pipe.rotate(Axis.Z, 45)

# Copy preserves all tracking state
pipe_copy = pipe.copy()
```

See [smartsolid.md](smartsolid.md) for the full list of inherited methods (alignment, booleans, filleting, bound box, etc.).
