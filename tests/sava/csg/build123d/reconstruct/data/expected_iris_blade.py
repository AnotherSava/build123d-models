# Iris blade as a stepped 2.5D extrusion, datum-aligned.
# Extrusion axis  z_dir = (0.683, -0.731, 0)
# Datum plane     y_dir = (0, 0, 1)
#   (= 1 along world Z, the floor — contact area 74.87 mm²)
# In-plane right  x_dir = (0.731, 0.683, 0)

from build123d import Plane, Vector, Cylinder, Axis
from sava.csg.build123d.common.pencil import Pencil

cross_section = Plane(
    origin=Vector(196.563, 183.584, 0),
    x_dir=Vector(0.731, 0.683, 0),
    z_dir=Vector(0.683, -0.731, 0),
)

# Main silhouette (front cap, the 6-gon)
body = Pencil(cross_section, start=(15.637, 0))
body.draw(10.95, 51.22)
body.draw(20.743, 120)
body.left(0.577)
body.draw(23.094, -120)
body.down(6.5)
main_body = body.extrude(3)  # thickness = depth(front) - depth(back)

# Recess on the back side (depth -0.611 → 0.889, 1.5 mm)
recess = Pencil(cross_section, start=(0.836, 1.7))
recess.right(16.167)
recess.draw(2.181, -128.78)
recess.left(14.802)
recess_body = recess.extrude(1.5)

# Pivot pin (cylinder, π·r² ≈ 10.17 ≈ π·1.82² = 10.4 mm²)
# Extrudes 4 mm forward from the front face
pivot_pin = Cylinder(radius=1.82, height=4)
# Position: at the centroid of pivot_tip face along the extrusion axis

blade = main_body - recess_body + pivot_pin