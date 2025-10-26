from build123d import Location, loft, Face, fillet, Wire

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
