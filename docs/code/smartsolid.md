# SmartSolid — Fluent API Guide

Primary wrapper around build123d shapes. Provides a fluent API for alignment, transformations, boolean operations, filleting, and bound box queries. All other smart classes (SmartBox, SmarterCone, SmartSphere, etc.) inherit from SmartSolid.

## Quick start

```python
from sava.csg.build123d.common.smartbox import SmartBox
from sava.csg.build123d.common.smartsolid import SmartSolid
from sava.csg.build123d.common.exporter import export, save_3mf

# Create a box, fillet its vertical edges, export
box = SmartBox(100, 50, 30)
box.fillet_z(5)
export(box)
save_3mf()

# Combine multiple solids
base = SmartBox(100, 100, 10)
pillar = SmartBox(20, 20, 50).align(base).z(Alignment.LR)
result = SmartSolid(base, pillar)
```

## Mutating vs non-mutating convention

Most methods come in pairs:

| Mutating (modifies self) | Non-mutating (returns copy) |
|---|---|
| `move()` | `moved()` |
| `rotate()` | `rotated()` |
| `cut()` | `cutted()` |
| `fuse()` | `fused()` |
| `mirror()` | `mirrored()` |
| `scale()` | `scaled()` |
| `pad()` | `padded()` |
| `align()` | `aligned()` |
| `orient()` | `oriented()` |
| `intersect()` | `intersected()` |

Mutating methods return `self` for chaining. Non-mutating methods call `.copy()` first.

## Alignment

Alignment is the primary way to position solids relative to each other (or to the origin). Use `.align()` to get an `AlignmentBuilder`, then chain `.x()`, `.y()`, `.z()` calls.

### The Alignment enum

Each alignment value is a two-letter code `[reference position][direction]`:
- First letter: where on the **reference** to anchor (L=Left/min, C=Center, R=Right/max)
- Second letter: which way **self** extends from that anchor (L=leftward, C=centered, R=rightward)

| Code | Meaning | Result |
|------|---------|--------|
| `LL` | at ref's left edge, self extends leftward | `self.max = ref.min` |
| `L`  | at ref's left edge, self centered | `self.center = ref.min` |
| `LR` | at ref's left edge, self extends rightward | `self.min = ref.min` |
| `CL` | at ref's center, self extends leftward | `self.max = ref.center` |
| `C`  | at ref's center, self centered (default) | `self.center = ref.center` |
| `CR` | at ref's center, self extends rightward | `self.min = ref.center` |
| `RL` | at ref's right edge, self extends leftward | `self.max = ref.max` |
| `R`  | at ref's right edge, self centered | `self.center = ref.max` |
| `RR` | at ref's right edge, self extends rightward | `self.min = ref.max` |

When the reference is `None`, "left" = 0 and "right" = 0 (align to origin).

### The `.align()` builder

```python
# Center on reference (all axes) — the starting point
cutout.align(box)

# Customize specific axes after centering
cutout.align(box).x(Alignment.LL).z(Alignment.LR)

# Shift: pass a number instead of alignment (keeps center alignment, shifts by amount)
cutout.align(box).y(10)  # centered on Y, then shifted +10

# Shift with alignment
cutout.align(box).z(Alignment.RL, -2)  # top-aligned, then shifted down by 2

# Multi-axis shortcuts
cutout.align(box).xy(Alignment.LR)     # same alignment on X and Y
cutout.align(box).xz(Alignment.C, shift_x=5, shift_z=10)

# Continue chaining after alignment
cutout.align(box).x(Alignment.LR).then().fillet_z(3)
# Or equivalently:
cutout.align(box).x(Alignment.LR).done().fillet_z(3)
```

### Convenience methods

For simple cases where you only need one or two axes:

```python
solid.align_x(ref, Alignment.LR)
solid.align_y(ref, Alignment.C, shift=5)
solid.align_z(ref, Alignment.RL)
solid.align_xy(ref, Alignment.C)
solid.align_xz(ref, Alignment.LR, shift_x=2)
solid.align_yz(ref, Alignment.C, shift_z=-3)
solid.align_zxy(ref, Alignment.LR)  # Z first, then X and Y
```

Pass `None` as reference to align to the origin:

```python
solid.align_x(None, Alignment.LR)  # left edge at x=0, extends right
```

### Real-world alignment patterns

```python
# Position a lid on top of a basket
lid.align(basket).y(Alignment.CR).z(Alignment.RL, dim.lid_thickness - dim.rim_depth)

# Position a connector cutout inside a box
connector_cut.align(box).x(dim.cable_hole_x_alignment, x_offset).z(Alignment.RL)

# Position a tooth relative to a canal
tooth.align(cable_canal).x(align_x).y(Alignment.RL).z(align_z, align_z.shift_towards_centre(dim.ball_tooth_offset))
```

## Transformations

### Move

```python
solid.move(10, 20, 5)           # move by (x, y, z)
solid.move(10)                   # move by x only (y=0, z=0)
solid.move_x(10)                 # move along X
solid.move_y(-5)                 # move along Y
solid.move_z(3)                  # move along Z
solid.move_vector(Vector(1,2,3)) # move by vector

# Move in a custom plane's coordinate system
solid.move(10, 0, 0, plane=tilted_plane)
```

### Rotate

```python
# Rotate around global axes (fixed coordinate system)
solid.rotate(Axis.Z, 45)        # 45 degrees around Z
solid.rotate_x(90)              # shorthand for rotate(Axis.X, 90)
solid.rotate_y(90)
solid.rotate_z(90)

# Non-mutating variants return a copy
solid.rotated_z(45)             # shorthand for rotated(Axis.Z, 45)
solid.rotated_x(90)
solid.rotated_y(90)

# Rotate around multiple axes sequentially (fixed axes, incremental)
solid.rotate_multi((90, 0, 45))
solid.rotate_multi((90, 0, 45), plane=Plane.XY)
```

### Orient

Sets absolute orientation using build123d's object-attached axis convention (non-incremental):

```python
solid.orient((90, 0, 0))        # set orientation to 90° around X
```

**Key difference:** `rotate()` uses fixed global axes and is incremental. `orient()` uses object-attached axes and sets absolute orientation.

### Print orientation (`bed_orientation`)

Build parts in **scene (visualization) orientation** — how they sit in the assembled model. When a part prints better in a different pose, set its `bed_orientation` rotation; export applies it **only when writing STL**, so the part still visualizes in scene pose:

```python
lid.bed_orientation = (180, 0, 0)   # flipped flat on the bed for printing, upright in the scene
```

`bed_orientation` defaults to `None` (scene pose prints as-is) and is preserved by `copy()`.

The typical export flow saves the assembled scene as 3MF first, then re-exports as STL (which is where `bed_orientation` is applied):

```python
from sava.csg.build123d.common.exporter import export, save_3mf, save_stl, clear

# 1. Assembled visualization scene (colors, parts posed together)
export(channel, cap)
save_3mf("models/.../export.3mf", current=True)

# 2. Slicer-ready STLs (bed_orientation applied; clear() avoids duplicating shapes)
clear()
export(channel, cap)
save_stl("models/.../stl")
```

### Scale

```python
solid.scale(2)                   # uniform scale
solid.scale(2, 1, 0.5)          # non-uniform scale (x, y, z)
```

### Mirror

```python
solid.mirror(Plane.XZ)          # mirror across XZ plane (flip Y)
solid.mirror(Plane.YZ)          # mirror across YZ plane (flip X)
solid.mirror(Plane.XY)          # mirror across XY plane (flip Z)
```

### Copy

```python
new_solid = solid.copy()              # deep copy
new_solid = solid.copy("my_label")    # copy with new label
```

## Boolean operations

```python
solid.cut(other)              # subtract other from solid
solid.cut(a, b, c)            # subtract multiple at once
solid.fuse(other)             # union
solid.fuse(a, b, c)           # union multiple
solid.intersect(other)        # intersection

# Non-mutating versions
result = solid.cutted(other)
result = solid.fused(other)
result = solid.intersected(other)

# Combine multiple solids in constructor
combined = SmartSolid(solid_a, solid_b, solid_c)
```

## Cutting helpers

Trim a solid along an axis. Exactly one parameter must be provided per call.

| Parameter | Meaning | Sign convention |
|-----------|---------|-----------------|
| `cut` | absolute amount to remove | positive = remove from -side, negative = remove from +side |
| `cut_fraction` | fraction of size to remove | positive = remove from -side, negative = remove from +side |
| `keep` | absolute amount to keep | positive = keep on +side, negative = keep on -side |
| `keep_fraction` | fraction of size to keep | positive = keep on +side, negative = keep on -side |

The sign always names the side that survives: positive keeps (or keeps more of) the +side, negative the -side.

```python
solid.cut_x(cut=10)               # remove 10mm from -X side
solid.cut_x(cut=-10)              # remove 10mm from +X side
solid.cut_y(cut_fraction=0.3)     # remove 30% from -Y side
solid.cut_y(cut_fraction=-0.3)    # remove 30% from +Y side
solid.cut_z(keep=20)              # keep only 20mm on +Z side
solid.cut_z(keep_fraction=0.5)    # keep 50% on +Z side
solid.cut_z(keep_fraction=-0.5)   # keep 50% on -Z side
```

Real-world examples:

```python
# Cut a sphere to create a partial holder
sphere.create_shell(dim.thickness).cut_z(cut_fraction=-dim.cut_fraction)

# Trim a connector to match another component's height
connector.cut_z(cut=connector.z_size - target.z_size)
```

## Bevel

Shave one side face with a planar cut. `side` is the world face to cut; `direction` is the (perpendicular) world axis the cut tilts along; `angle` is the wall angle from horizontal (90° = vertical = no cut, smaller = steeper bevel). The cut plane hinges on the side face's edge opposite to `direction`; `offset` slides it along the side's outward normal — negative cuts deeper, positive leaves material near the hinge. Works on any solid, not just boxes, and at any angle/height combination (a 45° bevel of a tall thin solid is fine).

```python
solid.bevel(side, direction, angle)                        # mutates in place, returns self
result = solid.beveled(side, direction, angle)             # non-mutating copy
solid.bevel(side, direction, angle, offset=-2)             # same plane, slid 2 deeper
```

```python
# Slant the east face so it leans inward toward the top
solid.bevel(Direction.E, Direction.U, 45)

# Miter the end of a channel for a right-angle corner join
channel.bevel(Direction.E, Direction.S, 45)

# Retreat a lap-joint seam: same plane, slid deeper into the part (see cablechannel.bend_right)
channel.bevel(Direction.E, Direction.S, 45, offset=-lap)
```

`side` must be perpendicular to `direction` (you can't tilt a face along its own normal).

## Bevel edge

Cut a flat wedge off the bound-box edge where two faces meet — a chamfer-like corner break sized by its legs instead of an angle. Each size is the leg the cut spans on that face, measured from the edge (`size_a` lies on the `side_a` face); equal legs give a 45° break. `size_b` defaults to `size_a`.

```python
solid.bevel_edge(side_a, side_b, size)                     # mutates in place, returns self
result = solid.beveled_edge(side_a, side_b, size)          # non-mutating copy
solid.bevel_edge(side_a, side_b, size_a, size_b)           # asymmetric legs
```

```python
# Break the top-east corner 45°, 2 mm along each face
solid.bevel_edge(Direction.E, Direction.U, 2)

# Steeper break: 2 mm down the east face, 5 mm across the top
solid.bevel_edge(Direction.E, Direction.U, 2, 5)
```

The sides must be perpendicular (parallel faces share no edge). Unlike build123d's topological `chamfer`, this cuts relative to the bounding box, so it works on any solid regardless of its actual edges.

## Filleting

### Axis-based filleting

Fillets all edges parallel to a given axis:

```python
solid.fillet_x(3)                # fillet edges parallel to X
solid.fillet_y(3)                # fillet edges parallel to Y
solid.fillet_z(3)                # fillet edges parallel to Z
solid.fillet_xy(3)               # fillet X then Y edges (same radius)
solid.fillet_xz(3)               # fillet X then Z edges
solid.fillet_yz(3)               # fillet Y then Z edges
solid.fillet(3)                  # fillet all edges (X, Y, and Z)
solid.fillet(3, 2, 1)            # different radius per axis (X=3, Y=2, Z=1)
```

Restrict by position along another axis:

```python
# Fillet Z-parallel edges, but only where Y is between 10 and 20
solid.fillet_z(3, axis=Axis.Y, minimum=10, maximum=20)

# Fillet Z-parallel edges, excluding extremes (interior only)
solid.fillet_z(3, axis=Axis.Y, inclusive=(False, False))
```

### Filter-based filleting with `fillet_by`

For precise edge selection, use `fillet_by` with filter objects:

```python
from sava.csg.build123d.common.edgefilters import PositionalFilter, AxisFilter, SurfaceFilter, AXIS_X, AXIS_Y, AXIS_Z

# Fillet edges at the top face only
solid.fillet_by(3, PositionalFilter(Axis.Z, solid.z_max))

# Fillet Z-parallel edges at a specific Y position range
solid.fillet_by(3, AXIS_Z, PositionalFilter(Axis.Y, box.y_max), PositionalFilter(Axis.X))

# Fillet with angle-aware axis filter
solid.fillet_by(3, AxisFilter(Axis.Z, angle_tolerance=10))
```

**PositionalFilter(axis, minimum, maximum, inclusive)**: filter edges by position along an axis. Pass just `minimum` to match edges at that exact position.

**AxisFilter(axis, angle_tolerance)**: filter edges by their direction (parallel to axis within tolerance).

**AXIS_X, AXIS_Y, AXIS_Z**: pre-built AxisFilter constants.

**Debug modes** for troubleshooting fillet failures:

```python
from sava.csg.build123d.common.edgefilters import FilletDebug

solid.fillet_by(3, AXIS_Z, debug=FilletDebug.ALL)      # show all matched edges in red
solid.fillet_by(3, AXIS_Z, debug=FilletDebug.PARTIAL)   # test each edge individually
```

## Bound box properties

Quick access to bounding box dimensions:

| Property | Returns |
|----------|---------|
| `x_min`, `y_min`, `z_min` | minimum coordinate |
| `x_mid`, `y_mid`, `z_mid` | center coordinate |
| `x_max`, `y_max`, `z_max` | maximum coordinate |
| `x_size`, `y_size`, `z_size` | dimension (max - min) |

```python
height = box.z_size
center_x = box.x_mid
is_tall = box.z_max > 100
```

For bounds in a custom coordinate system:

```python
bb = solid.get_bound_box(plane=tilted_plane)
```

## Clone

Create multiple evenly-spaced copies fused into one solid:

```python
# 5 copies, each shifted 25mm along X
row = pillar.clone(5, (25, 0, 0))

# 2 copies, symmetric about center
pair = protrusion.clone(2, (dim.spacing, 0))
```

## Pad

Expand a solid's dimensions by absolute amounts (scales proportionally):

```python
solid.pad(2)              # expand by 2mm on all axes
solid.pad(2, 1, 0)        # expand X by 2, Y by 1, Z unchanged

# Common pattern: create an expanded boundary for boolean operations
boundary = solid.padded(dim.thickness * 2).align_zxy(solid, Alignment.LR)
```

## Color

Set a display color (for visualization in 3MF viewer):

```python
solid.color("red")
solid.color("blue")
solid.color(None)    # remove color
```

## Other methods

| Method | Description |
|--------|-------------|
| `molded(padding)` | Create a mold (padded shell with self subtracted) |
| `cut_off(x, y, z)` | Intersect with own bounding box shifted by offsets |
| `colocate(ref)` | Copy position and orientation from another solid |
| `wrap_solid()` | Convert ShapeList to Compound (for operations that need a single shape) |
| `create_bound_box()` | Create a SmartBox matching this solid's bounding box |
