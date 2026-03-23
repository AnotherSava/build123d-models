# SmarterCone — Builder Guide

Builder for rotationally symmetric solids: cylinders, cones, and multi-section profiles. Shapes are built by defining a base cross-section and chaining `.extend()` calls to add sections upward (or downward). Each section is a circular cross-section at a given height with a given radius. The result is a solid of revolution created by connecting adjacent sections. Inherits all fluent API methods from SmartSolid (see `smartsolid.md`).

## Quick start

```python
from sava.csg.build123d.common.smartercone import SmarterCone, InnerMode

# Cylinder: radius 20, height 50
SmarterCone.base(20).extend(height=50)

# Cone: base radius 30, top radius 10, height 80
SmarterCone.base(30).extend(radius=10, height=80)

# Shortcut for cylinder
SmarterCone.cylinder(20, 50)
```

## Starting a cone

```python
SmarterCone.base(radius)              # base section at height 0
SmarterCone.base(radius, plane=...)   # build on a custom plane (default: XY)
SmarterCone.base(radius, angle=...)   # partial sector, e.g. angle=180 for half-cone
SmarterCone.cylinder(radius, height)  # shortcut for base + extend with same radius
```

## Extending with `.extend()`

Each `.extend()` adds a new section. The `height` parameter is relative (added to
the current height). Pick one of these parameter combinations:

| Call | Effect |
|------|--------|
| `.extend(radius=R, height=H)` | explicit radius and height |
| `.extend(height=H)` | same radius as previous (vertical wall) |
| `.extend(angle=A, height=H)` | compute radius from wall angle and height |
| `.extend(angle=A, radius=R)` | compute height from wall angle and radius |
| `.extend(radius=R)` | radius step at same height (sharp ledge) |
| `.extend()` | no-op step; chain `.inner()` to change only inner radius |

**`angle` convention:**
- Positive = wall slopes inward (radius decreases)
- Negative = wall slopes outward (radius increases)
- 90 = perfectly vertical wall (no radius change)
- The convention is the same regardless of whether height is positive or negative

**Multi-section example:**

```python
# Vase shape: wide base, narrow neck, flared rim
vase = (SmarterCone.base(40)
    .extend(radius=40, height=20)   # straight base wall
    .extend(radius=15, height=60)   # taper inward
    .extend(radius=20, height=20))  # flare outward
```

## Negative heights

Use negative height to build downward (in -Z direction). Once established,
all subsequent extends must continue in the same direction.

```python
SmarterCone.base(30).extend(radius=20, height=-50)
```

## Radius steps

Calling `.extend(radius=R)` without height creates an instant radius change
at the current height (a sharp ledge in the profile):

```python
# Step from radius 40 down to radius 20 at height 50, then continue
SmarterCone.base(40).extend(height=50).extend(radius=20).extend(height=30)
```

## Fillets

Add `fillet=R` to any `.extend()` to round the junction between the previous
segment and the new one:

```python
SmarterCone.base(40).extend(radius=40, height=50).extend(radius=20, height=50, fillet=5)
```

The fillet is computed in the (height, radius) profile space, so the rounding
appears in the silhouette of the shape.

## Hollow cones with `.inner()`

Call `.inner(radius)` to define an inner hole at the current (last) section.
Subsequent `.extend()` calls auto-propagate the inner surface.

```python
# Hollow cylinder: outer=30, inner=25, height=50
SmarterCone.base(30).inner(25).extend(height=50)
```

How `extend` propagates inner depends on the mode (`InnerMode`):

**THICKNESS (default)** — preserves wall thickness.
If outer radius changes, inner radius changes by the same amount.

```python
SmarterCone.base(30).inner(25).extend(radius=20, height=50)
# wall = 5, so inner = 20 - 5 = 15
```

**RADIUS** — preserves inner radius as-is.
Inner radius stays constant regardless of outer radius changes.

```python
SmarterCone.base(30).inner(25, mode=InnerMode.RADIUS).extend(radius=20, height=50)
# inner stays 25
```

Set the mode via `.inner(radius, mode=...)` or switch mode without changing
the radius: `.inner(mode=InnerMode.RADIUS)`. The mode can be changed at any
point in the chain and affects all subsequent `.extend()` calls.

- Stop the inner hole: `.inner(0)` clears inner_radius and stops propagation.
- Override auto-propagated inner: call `.inner(new_radius)` after `.extend()` to override the auto-computed value.

## Eccentric (off-axis) holes

Use `shift_x`/`shift_y` on `.inner()` to offset the hole from the outer axis:

```python
SmarterCone.base(50).extend(height=100).inner(20, shift_x=10)
```

In THICKNESS mode, the offset between inner and outer shifts is preserved.
In RADIUS mode, inner shifts are copied as-is.

## Shifted sections

Use `shift_x`/`shift_y` on `.extend()` to offset a section's center from the
cone axis. This creates bent or tilted shapes:

```python
# Cone that leans 30mm to the right at the top
SmarterCone.base(20).extend(radius=20, height=100, shift_x=30)
```

Note: `angle` cannot be combined with shift (the wall angle becomes ambiguous).

## Partial sectors

Set `angle` < 360 on `base()` to create a partial cone (wedge/sector):

```python
SmarterCone.base(30, angle=180)  # half-cone
SmarterCone.base(30, angle=90)   # quarter-cone
```

## Properties

| Property | Returns |
|----------|---------|
| `height` | Height of the last section (0 if only base) |
| `base_radius` | Radius of the first section |
| `top_radius` | Radius of the last section |
| `has_inner` | `True` if any section has an inner radius |

Interpolated queries by position (0 = base, 1 = first extend, 2 = second extend, etc.):

```python
cone = SmarterCone.base(30).extend(radius=20, height=50).extend(radius=10, height=100)
cone.radius(0.5)   # radius halfway through first segment
cone.center(1.0)    # center point at first extend junction
```

## Offset, shell, and extraction

```python
cone = SmarterCone.base(30).extend(radius=20, height=50)

# Grow or shrink all radii by a fixed amount
bigger = cone.create_offset(5)

# Create a hollow version (positive = outward shell, negative = inward shell)
shell = cone.create_shell(2)     # outer radius grows by 2, inner = original surface
shell = cone.create_shell(-2)    # outer stays, inner carved inward by 2
```

For hollow cones, extract inner or outer as standalone cones:

```python
hollow = SmarterCone.base(30).inner(20).extend(height=50)
outer = hollow.get_outer_cone()  # solid cone with outer radii only
inner = hollow.get_inner_cone()  # solid cone with inner radii only
```

## Inherited methods

See [smartsolid.md](smartsolid.md) for the full list of inherited methods (alignment, booleans, filleting, bound box, etc.).
