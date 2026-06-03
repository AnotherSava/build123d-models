---
name: Idiomatic emit/hand-written CAD style
description: For both reconstruction-emitted code and hand-written CAD, build in default Plane.XY, transform once at end, mirror emit style in hand-written code
type: feedback
---
When emitting CAD code (e.g. `sava.csg.build123d.reconstruct`) or hand-writing equivalents (e.g. `models/other/iris.py`):

1. **Build in default `Plane.XY`** — every `Pencil()`, `SmarterCone.cylinder(r, h)`, `.move(x, y, z)` operates in clean local coords. Avoid passing `plane=tilted_plane` to every operation.

2. **Apply a single transform at the end** if world placement matters: `blade = SmartSolid(target_plane * blade.solid, label='blade')`. Drop it entirely when orientation/position is irrelevant.

3. **Use the project's idiomatic constructors** — `SmarterCone.cylinder(r, h)` over `SmartSolid(Cylinder(r, h))`; `.fuse()` / `.cut()` over `+` / `-` (SmartSolid doesn't define those operators anyway).

4. **Hand-written code mirrors emit format** — when reconstruction emits Pencil ops directly (`body.jump(...)`, `body.draw(L, angle)`, `body.left(...)`, `body.down()`), the hand-written equivalent uses those same ops inline. Don't abstract into polygon-tuple + helper.

**Why:** the user iterated through every alternative across the iris-blade session and pulled the emit toward this form. The clean local frame keeps operations readable; a single end-transform makes world-frame placement optional; matching styles means generated and hand-written code can be copy-pasted back and forth.

**How to apply:** every time you touch `reconstruct/api.py::_emit_code`, `reconstruct/pencil_emit.py`, or any hand-written model that mirrors reconstructed geometry. Don't reintroduce `plane=cross_section` on every operation, raw `Cylinder(...)` wrapped in `SmartSolid(...)`, or polygon-tuple indirection.
