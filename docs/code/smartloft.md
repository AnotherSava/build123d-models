# SmartLoft — Lofted & Extruded Shapes

Creates 3D shapes by lofting between two profiles or extruding a profile along a direction. Tracks base and target profiles through transformations, enabling further operations on the end faces.

## Quick start

```python
from build123d import Wire, Face
from sava.csg.build123d.common.pencil import Pencil
from sava.csg.build123d.common.smartloft import SmartLoft

# Loft between two faces at different heights
base_pencil = Pencil().right(40).up(20).left(40)
target_pencil = Pencil().right(30).up(15).left(30)
shape = SmartLoft.create(base_pencil.create_face(), target_pencil.create_face(), height=50)

# Extrude a face upward
face = Pencil().right(40).up(20).left(40).create_face()
box = SmartLoft.extrude(face, amount=30)

# Loft between two wires (auto-converted to faces)
shape = SmartLoft.create(base_wire, target_wire, height=20)
```

## Creating a loft with `SmartLoft.create()`

Lofts a solid between two profiles positioned at a given distance apart.

```python
SmartLoft.create(base, target, height=0)
```

| Parameter | Type | Description |
|-----------|------|-------------|
| `base` | `Wire \| Face` | Base profile. Stays in place. |
| `target` | `Wire \| Face` | Target profile. Gets repositioned if `height` is set. |
| `height` | `float` | Distance from base to target along the base face normal. If 0, target stays at its original position. |

The `height` parameter moves the target along the base face's normal so the two profiles are exactly `height` apart. Positive height goes toward +Z (the normal is flipped if it points more toward -Z).

```python
# Loft between two differently-shaped faces
inner_face = create_window_shape(small_radius)
outer_face = create_window_shape(large_radius)
window = SmartLoft.create(inner_face, outer_face)

# Loft with explicit height separation
bottom = create_handle_wire(radius, arc_angle, width)
top = create_handle_wire(radius + height, arc_angle, width + height)
handle = SmartLoft.create(bottom, top, height=30)
```

## Extruding with `SmartLoft.extrude()`

Creates an extruded solid from a profile, while tracking the base and target faces.

```python
SmartLoft.extrude(profile, amount, direction=(0, 0, 1))
```

| Parameter | Type | Description |
|-----------|------|-------------|
| `profile` | `Wire \| Face` | Profile to extrude. |
| `amount` | `float` | Extrusion distance. |
| `direction` | `VectorLike` | Extrusion direction. Defaults to +Z. |

Use `SmartLoft.extrude()` instead of raw `extrude()` when you need to access the end faces afterward (e.g., for alignment or further lofting).

```python
# Extrude a hex socket face
hex_face = hex_recess(socket_size)
hex_socket = SmartLoft.extrude(hex_face, depth)
hex_socket.align_zxy(cap, Alignment.RL)

# Extrude downward
notch = SmartLoft.extrude(wire, -notch_width)
```

## Profile tracking

SmartLoft stores `base_profile` and `target_profile` as `Face` objects. These profiles are kept in sync through transformations (move, rotate, copy), so you can always access the current end faces:

```python
loft = SmartLoft.create(base_face, target_face, height=50)

# Access end faces for further operations
loft.base_profile    # Face at the base
loft.target_profile  # Face at the target

# Use target profile to create a shadow/extension
shadow = SmartLoft.extrude(loft.target_profile, -depth)
```

## Transformations

SmartLoft overrides `move()`, `rotate()`, `rotate_multi()`, and `orient()` to keep profiles in sync with the solid. All SmartSolid transformation methods are available.

```python
# Move — profiles follow
loft.move(10, 20, 0)

# Rotate — profiles reposition and reorient
loft.rotate(Axis.Z, 45)

# Copy preserves profiles
loft_copy = loft.copy()
```

See [smartsolid.md](smartsolid.md) for the full list of inherited methods (alignment, booleans, filleting, bound box, etc.).
