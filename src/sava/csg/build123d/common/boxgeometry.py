"""Geometry construction for SmartBox.

This module holds the math-heavy internals behind SmartBox: resolving high-level
tapering parameters into a concrete top rectangle, building the OCC solid, and computing
offset boxes. SmartBox itself stays focused on the user-facing API and delegates the
"how" to the functions here.

The box base is always a (length × width) rectangle centred on the origin, spanning
[-length/2, length/2] × [-width/2, width/2]. The top is an axis-aligned rectangle at
``height`` described by a :class:`TopRect`; its four edges may be displaced independently,
so any frustum/wedge with planar walls is expressible.
"""

from dataclasses import dataclass
from math import radians, tan

from build123d import Face, Location, Plane, Solid, Wire, loft

from sava.common.advanced_math import advanced_mod
from sava.csg.build123d.common.geometry import are_numbers_too_close


@dataclass(frozen=True)
class TopRect:
    """The top rectangle of a box, as absolute edge coordinates in the base-centred frame."""
    x_min: float
    x_max: float
    y_min: float
    y_max: float

    @property
    def length(self) -> float:
        return self.x_max - self.x_min

    @property
    def width(self) -> float:
        return self.y_max - self.y_min

    @property
    def center_x(self) -> float:
        return (self.x_min + self.x_max) / 2

    @property
    def center_y(self) -> float:
        return (self.y_min + self.y_max) / 2


@dataclass(frozen=True)
class OffsetBox:
    """Result of :func:`offset_box_geometry`: dimensions and top rectangle of the offset
    box (with the top expressed relative to its own centred base) plus the X/Y centre at
    which that base must be placed relative to the source box's base centre."""
    length: float
    width: float
    height: float
    top: 'TopRect'
    center_x: float
    center_y: float


def _top_edge_displacement(angle: float | None, tapered_dim: float | None, base_dim: float, height: float) -> float:
    """Outward displacement of one top edge from its base edge, in the base plane.

    Positive moves the edge away from the box centre (the wall flares outward toward
    the top); negative draws it inward. Resolution priority for a single side:
      1. ``angle`` (measured from horizontal: 90° = vertical, <90° = inward taper,
         >90° = outward flare). Takes precedence when given.
      2. ``tapered_dim`` — the symmetric top dimension for this edge's pair; each of
         the two edges moves inward/outward by half the (tapered_dim - base_dim) change.
      3. Neither given -> 0 (vertical wall).
    """
    if angle is not None:
        reduced = advanced_mod(angle, 180, -90, 90)
        assert not are_numbers_too_close(reduced, 0), f"Wall angle {angle} is horizontal (invalid)"
        if are_numbers_too_close(abs(reduced), 90):
            return 0.0
        return -height / tan(radians(angle))
    if tapered_dim is not None:
        return (tapered_dim - base_dim) / 2
    return 0.0


def resolve_top_rect(length: float, width: float, height: float, tapered_length: float | None, tapered_width: float | None, angle_east: float | None, angle_west: float | None, angle_north: float | None, angle_south: float | None) -> TopRect:
    """Resolve the constructor's tapering parameters into a top rectangle. A per-side
    ``angle_*`` overrides ``tapered_length`` / ``tapered_width`` for that wall only."""
    assert not (tapered_length is not None and angle_east is not None and angle_west is not None), "tapered_length is redundant when both angle_east and angle_west are given"
    assert not (tapered_width is not None and angle_north is not None and angle_south is not None), "tapered_width is redundant when both angle_north and angle_south are given"

    d_e = _top_edge_displacement(angle_east, tapered_length, length, height)
    d_w = _top_edge_displacement(angle_west, tapered_length, length, height)
    d_n = _top_edge_displacement(angle_north, tapered_width, width, height)
    d_s = _top_edge_displacement(angle_south, tapered_width, width, height)

    return TopRect(-length / 2 - d_w, length / 2 + d_e, -width / 2 - d_s, width / 2 + d_n)


def is_tapered(length: float, width: float, top: TopRect) -> bool:
    """True when the top rectangle differs from the base rectangle in any edge."""
    return not (are_numbers_too_close(top.x_min, -length / 2) and are_numbers_too_close(top.x_max, length / 2) and are_numbers_too_close(top.y_min, -width / 2) and are_numbers_too_close(top.y_max, width / 2))


def build_box_solid(length: float, width: float, height: float, top: TopRect, plane: Plane = Plane.XY) -> Solid:
    """Build the OCC solid: an efficient make_box() when untapered, otherwise a loft
    between the centred base rectangle and the (possibly asymmetric) top rectangle."""
    assert top.length > 0, f"Top length is non-positive: {top.length}"
    assert top.width > 0, f"Top width is non-positive: {top.width}"

    if is_tapered(length, width, top):
        base = Face(Wire.make_rect(length, width))
        top_face = Face(Wire.make_rect(top.length, top.width)).move(Location((top.center_x, top.center_y, height)))
        solid = loft([base, top_face])
    else:
        # Build the box already centered in XY (and base-aligned in Z) by constructing on
        # a shifted plane, so the resulting Solid keeps an identity Location. Building via
        # `.move(Location((-L/2, -W/2, 0)))` would leave the Location at (-L/2, -W/2, 0),
        # and build123d's `.orientation` setter rotates around the Location's position —
        # so subsequent .rotate_z calls would pivot around a box edge instead of its centre.
        solid = Solid.make_box(length, width, height, plane=Plane(origin=(-length / 2, -width / 2, 0)))

    if plane != Plane.XY:
        solid = solid.locate(Location(plane))

    return solid


def offset_box_geometry(length: float, width: float, height: float, top: TopRect, north: float, south: float, east: float, west: float, up: float, down: float) -> OffsetBox:
    """Compute the geometry of a per-direction offset box.

    Each wall is extrapolated along its own slope to the new base (z = -down) and new top
    (z = height + up), then displaced horizontally by its directional offset. The result's
    base is re-centred on the origin, so the top rectangle is returned relative to that new
    centre together with the X/Y placement of the new base centre.
    """
    half_l = length / 2
    half_w = width / 2

    # Per-side outward slope: edge displacement per unit height for each wall.
    slope_e = (top.x_max - half_l) / height
    slope_w = (top.x_min + half_l) / height
    slope_n = (top.y_max - half_w) / height
    slope_s = (top.y_min + half_w) / height

    # East/north face +x/+y so their offset adds; west/south face the opposite way.
    base_e = half_l - slope_e * down + east
    base_w = -half_l - slope_w * down - west
    base_n = half_w - slope_n * down + north
    base_s = -half_w - slope_s * down - south
    top_e = top.x_max + slope_e * up + east
    top_w = top.x_min + slope_w * up - west
    top_n = top.y_max + slope_n * up + north
    top_s = top.y_min + slope_s * up - south

    center_x = (base_e + base_w) / 2
    center_y = (base_n + base_s) / 2

    return OffsetBox(length=base_e - base_w, width=base_n - base_s, height=height + down + up, top=TopRect(top_w - center_x, top_e - center_x, top_s - center_y, top_n - center_y), center_x=center_x, center_y=center_y)
