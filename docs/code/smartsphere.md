# SmartSphere — Sphere Primitives Guide

Sphere primitive with optional hollow interior and partial sweep support. Inherits all fluent API methods from SmartSolid (see `smartsolid.md`).

## Quick start

```python
from sava.csg.build123d.common.smartsphere import SmartSphere

# Solid sphere with radius 50
sphere = SmartSphere(50)

# Hollow sphere (outer radius 50, inner radius 40)
hollow = SmartSphere(50, internal_radius=40)

# Hemisphere
half = SmartSphere(50, angle=180)
```

## Constructor

```python
SmartSphere(radius, internal_radius=None, angle=360, plane=Plane.XY, label=None)
```

| Parameter | Description |
|-----------|-------------|
| `radius` | External radius of the sphere |
| `internal_radius` | Internal radius (`None` = solid sphere) |
| `angle` | Longitude sweep angle in degrees (360 = full, 180 = hemisphere) |
| `plane` | Plane to create the sphere in, centered at plane origin (default: XY) |
| `label` | Optional label for export |

The sphere is centered at the origin of the given plane.

## Class methods

### `create_hollow`

Creates a hollow sphere from two radii — automatically picks the larger as the external radius.

```python
SmartSphere.create_hollow(radius1, radius2, angle=360, plane=Plane.XY, label=None)
```

```python
# Order doesn't matter — outer=50, inner=40 either way
sphere = SmartSphere.create_hollow(40, 50)
sphere = SmartSphere.create_hollow(50, 40)
```

## `create_offset`

Creates a new sphere with one radius adjusted by an offset. The new sphere is colocated with the original.

```python
sphere.create_offset(offset, external=True, label=None)
```

| Parameter | Description |
|-----------|-------------|
| `offset` | Amount to adjust (positive = larger, negative = smaller) |
| `external` | If `True` (default), adjusts external radius; if `False`, adjusts internal radius |

```python
sphere = SmartSphere(50, internal_radius=40)

# Expand outer radius by 5mm
bigger = sphere.create_offset(5)            # outer=55, inner=40

# Shrink inner radius by 5mm (thicker wall)
thicker = sphere.create_offset(-5, external=False)  # outer=50, inner=35
```

## `create_shell`

Creates a shell (thin-walled sphere) from a surface of the sphere.

```python
sphere.create_shell(offset, external=True, label=None)
```

| Parameter | Description |
|-----------|-------------|
| `offset` | Shell thickness (positive = outward from surface, negative = inward) |
| `external` | If `True` (default), shell on external surface; if `False`, shell on internal surface |

```python
sphere = SmartSphere(50)

# 5mm shell outside the sphere surface (radius 50–55)
outer_shell = sphere.create_shell(5)

# 5mm shell inside the sphere surface (radius 45–50)
inner_shell = sphere.create_shell(-5)

# For hollow spheres, shell on the internal surface
hollow = SmartSphere(50, internal_radius=40)
inner_wall_shell = hollow.create_shell(5, external=False)  # radius 40–45
```

## `create_sphere`

Creates a new solid sphere with a given radius, colocated with the current sphere (same center and plane).

```python
sphere.create_sphere(radius, angle=None, label=None)
```

If `angle` is not specified, the current sphere's angle is used.

```python
sphere = SmartSphere(50, plane=Plane.YZ)
smaller = sphere.create_sphere(30)  # solid sphere radius 30, same plane and position
```

## `create_inner_sphere` / `create_outer_sphere`

Extract a solid sphere matching one of the radii of a hollow sphere.

```python
hollow = SmartSphere(50, internal_radius=40)

inner = hollow.create_inner_sphere()  # solid sphere, radius 40
outer = hollow.create_outer_sphere()  # solid sphere, radius 50
```

`create_inner_sphere` raises `ValueError` on a solid sphere (no internal radius).

## Inherited from SmartSolid

SmartSphere inherits the full SmartSolid API. See `smartsolid.md` for:

- Alignment (`.align()` builder, `align_x/y/z`, Alignment enum)
- Transformations (move, rotate, scale, mirror)
- Boolean operations (cut, fuse, intersect)
- Cutting helpers (cut_x/y/z)
- Filleting (fillet_x/y/z, fillet_by)
- Bound box properties (x_min/mid/max, x_size, etc.)
- Clone, pad, color
