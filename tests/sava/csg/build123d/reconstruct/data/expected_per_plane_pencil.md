# Pencil sketches for each plane of `obj_1.off`

Total surface area: **1047.19 mm²**
Significant planes (≥1% of surface area): **9**

Each Pencil sketch is in the plane's **local 2D coordinates**. The plane's 3D embedding is given by `origin`, `x_dir`, and `z_dir` (= plane normal). After Pencil draws the closed polygon, `create_face()` yields the planar face; `extrude(thickness)` would lift it to a 3D slab.

## Simplest planes (ranked by stroke count)

| Rank | Area (mm²) | Strokes | Shape |
|:----:|----------:|:-------:|-------|
| 4 | 69.28 | 4 | rectangle |
| 5 | 62.23 | 4 | rectangle |
| 7 | 26.32 | 4 | quad |
| 8 | 24.25 | 4 | rectangle |
| 9 | 19.50 | 4 | rectangle |
| 1 | 347.97 | 6 | 6-gon |
| 6 | 36.12 | 6 | 6-gon |
| 2 | 331.92 | 8 | 8-gon |
| 3 | 74.87 | 10 | 10-gon |

---

## Per-plane Pencil programs

## Plane 1 (area 347.97 mm², normal=(+0.683, -0.731, +0.000), d=+3.889)

- Shape: **6-gon** (6 vertices after collinear-merge, from 76 raw boundary edges)
- 2D bbox: 22.50 × 26.50 mm  (polygon area: 358.24 mm²)
- Number of Pencil strokes: **6**

```python
plane = Plane(
    origin=Vector(206.973, 187.985, 0.481),
    x_dir=Vector(0.731, 0.683, 0),
    z_dir=Vector(0.683, -0.731, 0),
)
pencil = Pencil(plane, start=(5.026, -0.481))
pencil.draw(10.95, 51.22)
pencil.draw(20.743, 120)
pencil.left(0.577)
pencil.draw(23.094, -120)
pencil.down(6.5)
pencil.right(15.637)
face = pencil.create_face()
```

## Plane 2 (area 331.92 mm², normal=(+0.683, -0.731, -0.000), d=+0.889)

- Shape: **8-gon** (8 vertices after collinear-merge, from 8 raw boundary edges)
- 2D bbox: 22.50 × 26.50 mm  (polygon area: 331.92 mm²)
- Number of Pencil strokes: **8**

```python
plane = Plane(
    origin=Vector(197.781, 183.505, 1.7),
    x_dir=Vector(0.731, 0.683, 0),
    z_dir=Vector(0.683, -0.731, 0),
)
pencil = Pencil(plane, start=(0, 0))
pencil.down(1.7)
pencil.left(0.836)
pencil.up(6.5)
pencil.draw(23.094, 60)
pencil.right(0.577)
pencil.draw(20.743, -60)
pencil.draw(8.769, -128.78)
pencil.left(16.167)
face = pencil.create_face()
```

## Plane 3 (area 74.87 mm², normal=(+0.000, -0.000, +1.000), d=+0.000)

- Shape: **10-gon** (10 vertices after collinear-merge, from 10 raw boundary edges)
- 2D bbox: 14.37 × 13.96 mm  (polygon area: 74.87 mm²)
- Number of Pencil strokes: **10**

```python
plane = Plane(
    origin=Vector(207.574, 194.704, 0),
    x_dir=Vector(1, 0, 0),
    z_dir=Vector(0, 0, 1),
)
pencil = Pencil(plane, start=(0, 0))
pencil.draw(4.5, -46.96)
pencil.draw(3.082, -136.96)
pencil.draw(4, -46.96)
pencil.draw(1.44, -136.96)
pencil.draw(4, 133.04)
pencil.draw(11.116, -136.96)
pencil.draw(3, 133.04)
pencil.draw(0.836, 43.04)
pencil.draw(1.5, 133.04)
pencil.draw(14.802, 43.04)
face = pencil.create_face()
```

## Plane 4 (area 69.28 mm², normal=(+0.633, +0.591, -0.500), d=+229.678)

- Shape: **rectangle** (4 vertices after collinear-merge, from 4 raw boundary edges)
- 2D bbox: 3.00 × 23.09 mm  (polygon area: 69.28 mm²)
- Number of Pencil strokes: **4**

```python
plane = Plane(
    origin=Vector(197.17, 182.934, 6.5),
    x_dir=Vector(-0.683, 0.731, 0),
    z_dir=Vector(0.633, 0.591, -0.5),
)
pencil = Pencil(plane, start=(0, 0))
pencil.left(3)
pencil.up(23.094)
pencil.right(3)
pencil.down(23.094)
face = pencil.create_face()
```

## Plane 5 (area 62.23 mm², normal=(+0.633, +0.591, +0.500), d=+256.677)

- Shape: **rectangle** (4 vertices after collinear-merge, from 4 raw boundary edges)
- 2D bbox: 3.00 × 20.74 mm  (polygon area: 62.23 mm²)
- Number of Pencil strokes: **4**

```python
plane = Plane(
    origin=Vector(208.079, 189.018, 26.5),
    x_dir=Vector(-0.683, 0.731, 0),
    z_dir=Vector(0.633, 0.591, 0.5),
)
pencil = Pencil(plane, start=(0, 0))
pencil.down(20.743)
pencil.right(3)
pencil.up(20.743)
pencil.left(3)
face = pencil.create_face()
```

## Plane 6 (area 36.12 mm², normal=(+0.570, +0.532, -0.626), d=+221.864)

- Shape: **6-gon** (6 vertices after collinear-merge, from 6 raw boundary edges)
- 2D bbox: 4.50 × 10.95 mm  (polygon area: 36.12 mm²)
- Number of Pencil strokes: **6**

```python
plane = Plane(
    origin=Vector(209.597, 194.54, 1.7),
    x_dir=Vector(-0.683, 0.731, 0),
    z_dir=Vector(0.57, 0.532, -0.626),
)
pencil = Pencil(plane, start=(0, 0))
pencil.up(8.769)
pencil.left(3)
pencil.down(10.95)
pencil.right(4.5)
pencil.up(2.181)
pencil.left(1.5)
face = pencil.create_face()
```

## Plane 7 (area 26.32 mm², normal=(+0.683, -0.731, -0.000), d=-0.611)

- Shape: **quad** (4 vertices after collinear-merge, from 4 raw boundary edges)
- 2D bbox: 16.17 × 1.70 mm  (polygon area: 26.32 mm²)
- Number of Pencil strokes: **4**

```python
plane = Plane(
    origin=Vector(196.757, 184.601, 1.7),
    x_dir=Vector(0.731, 0.683, 0),
    z_dir=Vector(0.683, -0.731, 0),
)
pencil = Pencil(plane, start=(0, 0))
pencil.right(16.167)
pencil.draw(2.181, -128.78)
pencil.left(14.802)
pencil.up(1.7)
face = pencil.create_face()
```

## Plane 8 (area 24.25 mm², normal=(-0.000, -0.000, +1.000), d=+1.700)

- Shape: **rectangle** (4 vertices after collinear-merge, from 4 raw boundary edges)
- 2D bbox: 12.84 × 12.13 mm  (polygon area: 24.25 mm²)
- Number of Pencil strokes: **4**

```python
plane = Plane(
    origin=Vector(208.573, 195.636, 1.7),
    x_dir=Vector(1, 0, 0),
    z_dir=Vector(0, 0, 1),
)
pencil = Pencil(plane, start=(0, 0))
pencil.draw(16.167, -136.96)
pencil.draw(1.5, -46.96)
pencil.draw(16.167, 43.04)
pencil.draw(1.5, 133.04)
face = pencil.create_face()
```

## Plane 9 (area 19.50 mm², normal=(+0.731, +0.683, +0.000), d=+268.962)

- Shape: **rectangle** (4 vertices after collinear-merge, from 4 raw boundary edges)
- 2D bbox: 3.00 × 6.50 mm  (polygon area: 19.50 mm²)
- Number of Pencil strokes: **4**

```python
plane = Plane(
    origin=Vector(197.17, 182.934, 0),
    x_dir=Vector(-0.683, 0.731, 0),
    z_dir=Vector(0.731, 0.683, 0),
)
pencil = Pencil(plane, start=(0, 0))
pencil.left(3)
pencil.up(6.5)
pencil.right(3)
pencil.down(6.5)
face = pencil.create_face()
```
