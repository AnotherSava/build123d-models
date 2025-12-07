from math import tan, radians

from build123d import Location, loft, Face, fillet, Wire, Solid

from sava.csg.build123d.common.smartsolid import SmartSolid


def create_tapered_box(bottom_length: float, bottom_width: float, height: float, top_length: float, top_width: float, radius = None) -> SmartSolid:
    bottom = create_filleted_rect(bottom_length, bottom_width, radius)
    top = create_filleted_rect(top_length, top_width, radius).move(Location((0, 0, height)))

    return SmartSolid(loft([bottom, top]))

def create_filleted_rect(length: float, width: float, radius: float) -> Face:
    wire = Wire.make_rect(length, width)
    if radius:
        wire = fillet(wire.vertices(), radius)
    return Face(wire)

def create_cone_with_angle(bottom_radius: float, top_radius: float, angle: float) -> SmartSolid:
    height = (top_radius - bottom_radius) / tan(radians(angle))
    return SmartSolid(Solid.make_cone(bottom_radius, top_radius, height))

def create_cone_with_angle_and_height(bottom_radius: float, height: float, angle: float) -> SmartSolid:
    top_radius = height * tan(radians(angle)) + bottom_radius
    return SmartSolid(Solid.make_cone(bottom_radius, top_radius, height))
