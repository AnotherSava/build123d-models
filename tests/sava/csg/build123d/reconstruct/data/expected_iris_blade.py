# Iris blade as a stepped 2.5D extrusion, datum-aligned.
# Extrusion axis  z_dir = (0.683, -0.731, 0)
# Datum plane     y_dir = (0, 0, 1)
#   (= 1 along world Z, the floor — contact area 74.87 mm²)
# In-plane right  x_dir = (0.731, 0.683, 0)
# Built in default Plane.XY (local frame); a final transform places the
# blade back into the source-mesh world frame. Drop that transform to use
# the blade as a clean, axis-aligned local-frame component.

from build123d import Axis, Plane, Vector
from sava.csg.build123d.common.pencil import Pencil
from sava.csg.build123d.common.smartbox import SmartBox
from sava.csg.build123d.common.smartercone import SmarterCone
from sava.csg.build123d.common.smartsolid import SmartSolid

# Main body (front-cap silhouette, the 6-gon)
body = Pencil()
body.jump((6.858, 8.536))
body.draw(20.743, 30)
body.left(0.577)
body.draw(23.094, 150)
body.down()
blade = body.extrude(3)

# Back protrusion (depth -0.611 → 0.889, 1.5 mm), fused below the body
back_protrusion = Pencil()
back_protrusion.jump((1.366, 1.7))
back_protrusion.left(16.167)
back_protrusion.down()
back_protrusion_body = back_protrusion.extrude(1.5)
back_protrusion_body.move(0, 0, -1.5)
blade.fuse(back_protrusion_body)

# Front protrusion (depth 3.889 → 7.889, 4 mm), fused above the body
front_protrusion = SmarterCone.cylinder(1.815, 4)
front_protrusion.move(-3.776, 1.701, 3)
blade.fuse(front_protrusion)

# Place the blade into the source-mesh world frame.
# Delete if object orientation and position are irrelevant.
cross_section = Plane(origin=Vector(208.598, 193.608, 0), x_dir=Vector(0.731, 0.683, 0), z_dir=Vector(0.683, -0.731, 0))
_parts = list(blade.solid) if hasattr(blade.solid, '__iter__') else [blade.solid]
blade = SmartSolid(*(cross_section * s for s in _parts), label='blade')
