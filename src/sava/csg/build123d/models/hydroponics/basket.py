from copy import copy
from dataclasses import dataclass
from math import radians, degrees, atan, cos, tan
from typing import Tuple

from build123d import Solid, Vector, Plane, Axis, VectorLike, Wire, Edge, loft, Location, Face

from sava.common.common import flatten
from sava.csg.build123d.common.exporter import export, save_3mf, save_stl, clear
from sava.csg.build123d.common.geometry import Alignment, to_vector, rotate_vector, create_vector, get_angle
from sava.csg.build123d.common.pencil import Pencil
from sava.csg.build123d.common.primitives import create_cone_with_angle_and_height
from sava.csg.build123d.common.smartbox import SmartBox
from sava.csg.build123d.common.smartcone import SmartCone
from sava.csg.build123d.common.smartercone import SmarterCone
from sava.csg.build123d.common.smartsolid import SmartSolid


@dataclass
class BasketDimensions:
    sponge_diameter_top: float = 23
    inner_diameter_bottom: float = 11
    height: float = 65
    window_angle: float = 30
    window_count: int = 8
    thickness: float = 1.6
    floor_count: int = 2
    floor_gap_height: float = 5

    cap_diameter_outer_wide: float = 38
    cap_diameter_outer_middle: float = 33
    cap_angle: float = 45
    cap_leg_width: float = 1.5
    cap_leg_count: int = 4
    leg_depth: float = 5.3

    cap_thickness: float = 3
    cap_latch_thickness: float = 2
    cap_foundation_depth: float = 2.5

    cap_handle_height: float = 1
    cap_handle_width: float = 2.6
    cap_handle_arc_angle: float = 45

    cap_foundation_angle: float = -97
    cap_foundation_offset: float = 0.1
    cap_foundation_support_thickness: float = 1.5
    cap_foundation_hook_depth: float = 1.2

    cap_notch_height: float = 1
    cap_notch_width: float = 1.5
    cap_notch_arc_angle: float = 30

    @property
    def foundation_thickness(self) -> float:
        return self.thickness * 2 / 3

    @property
    def foundation_hook_outer_radius(self) -> float:
        return self.basket_cap_radius_narrow + self.cap_foundation_offset

    @property
    def foundation_hook_inner_radius(self) -> float:
        return self.foundation_hook_outer_radius - self.foundation_thickness

    @property
    def foundation_hook_arc_angle(self) -> float:
        return self.window_angle * 2 / 3

    @property
    def cap_angle_radians(self) -> float:
        return radians(self.cap_angle)

    @property
    def window_angle_radians(self) -> float:
        return radians(self.window_angle)

    def cap_radius_outer(self, offset_z_towards_basket: float = 0) -> float:
        return self.cap_diameter_outer_wide / 2 - offset_z_towards_basket * tan(self.cap_angle_radians)

    def cap_radius_inner(self, offset_z_towards_basket: float = 0) -> float:
        return self.cap_radius_outer(offset_z_towards_basket) - self.thickness

    @property
    def basket_cap_radius_wide(self) -> float:
        return self.cap_radius_inner(self.cap_depth - self.cap_thickness)

    @property
    def basket_cap_radius_narrow(self) -> float:
        return self.cap_radius_inner(self.cap_depth)

    @property
    def outer_radius_top(self):
        return self.inner_radius_top + self.thickness

    @property
    def cap_depth(self):
        return (self.cap_diameter_outer_wide / 2 - self.outer_radius_top) / tan(self.cap_angle_radians)

    @property
    def inner_radius_top(self):
        return self.sponge_diameter_top / 2

    @property
    def outer_radius_bottom(self) -> float:
        return self.inner_diameter_bottom / 2 + self.thickness

    @property
    def triangle_height_at_cap(self) -> float:
        """Height of the triangular window top at the cap level."""
        radius_at_cap = self.outer_radius_bottom
        arc_length_at_cap = radius_at_cap * self.window_angle_radians
        return arc_length_at_cap / 2

    @property
    def gap_between_levels(self) -> float:
        """Gap height between window levels (reduced by triangle height)."""
        return self.floor_gap_height - self.triangle_height_at_cap

    @property
    def window_height(self) -> float:
        """Height of each window."""
        num_gaps_between = self.floor_count - 1
        total_gap_height = num_gaps_between * self.gap_between_levels
        remaining_height = self.height - total_gap_height + self.triangle_height_at_cap
        return remaining_height / self.floor_count

    @property
    def cone_slope_angle(self) -> float:
        """Cone slope angle from vertical (in degrees)."""
        radius_diff = self.outer_radius_top - self.outer_radius_bottom
        return degrees(atan(radius_diff / self.height))


class BasketFactory:
    def __init__(self, dim: BasketDimensions):
        self.dim = dim

    def _create_basket(self) -> Tuple[SmartSolid, SmartSolid]:
        """Create the basic basket shape (outer cone, inner cone, cap)."""
        outer = SmartSolid(Solid.make_cone(self.dim.outer_radius_bottom, self.dim.outer_radius_top, self.dim.height))

        inner = SmartSolid(Solid.make_cone(self.dim.inner_diameter_bottom / 2, self.dim.inner_radius_top, self.dim.height))
        inner.align_zxy(outer, Alignment.LR)

        cap_outer = SmartCone.create_empty(-45, self.dim.outer_radius_bottom, self.dim.thickness * cos(radians(45)))
        cap_outer.align_zxy(outer, Alignment.LL)

        # Create all window cutouts
        windows = SmartSolid(self._create_all_windows()).align_z(outer, Alignment.RL)

        return outer.fuse(cap_outer).cut(windows), inner

    def _create_window_shape(self, distance: float) -> Face:
        width = distance * self.dim.window_angle_radians

        # Create half of pentagonal window to mirror across "Y" axis
        # Start at top middle, trace right side down to triangle tip
        pencil = Pencil(plane=Plane.YZ)
        pencil.right(width / 2)
        pencil.down(self.dim.window_height - width / 2)
        pencil.jump((-width / 2, -width / 2))

        return pencil.create_mirrored_face(Axis.Y).move(Location((distance, 0, 0)))

    def _create_window(self) -> SmartSolid:
        inner_face = self._create_window_shape(self.dim.inner_diameter_bottom / 3)
        outer_face = self._create_window_shape(self.dim.inner_radius_top * 1.5)

        return SmartSolid(loft([inner_face, outer_face]))

    def _create_all_windows(self) -> list[SmartSolid]:
        """Create all window cutouts for all levels.

        Returns:
            list[SmartSolid]: List of all window cutout solids
        """
        windows = []
        template_window = self._create_window()

        for level in range(self.dim.floor_count):
            current_offset_from_top = (self.dim.window_height + self.dim.gap_between_levels) * level # offset from basket's wide top

            # Create copies rotated around the circumference
            angle_step = 360 / self.dim.window_count
            for i in range(self.dim.window_count):
                # Create a copy and rotate it around Z axis at origin
                windows.append(template_window.copy().move_z(-current_offset_from_top).solid.rotate(Axis.Z, (i + 0.5) * angle_step))

        return windows

    def create_handle_wire(self, centre: VectorLike, start: VectorLike, angle: float, width: float) -> Wire:
        """Create a curved handle wire as a spline arc.

        Args:
            centre: Center point of the circular arc
            start: Start vector relative to centre (radial direction)
            angle: Angular span in degrees (CCW rotation around Z axis)
            width: Additional radial distance for the middle point (creates outward bulge)

        Returns:
            Wire: Spline wire forming the handle curve
        """
        offset = 1.0001
        centre = to_vector(centre)
        start = to_vector(start) / offset

        # Calculate the three points
        start_point = centre + start

        # Rotate start vector by angle around Z axis to get end point
        start_rotated = rotate_vector(start, Axis.Z, angle)
        end_point = centre + start_rotated

        # Rotate start vector by angle/2 and increase length by width for middle point
        start_rotated_half = rotate_vector(start, Axis.Z, angle / 2)
        middle_direction = start_rotated_half.normalized()
        middle_point = centre + middle_direction * (start.length + width)

        # Calculate tangents perpendicular to radial directions (CCW in XY plane)
        # For a radial vector (x, y, z), the tangent for CCW motion is (-y, x, 0)
        start_tangent = Vector(-start.Y, start.X, 0).normalized()
        end_tangent = Vector(-start_rotated.Y, start_rotated.X, 0).normalized()

        # Middle tangent is the average of start and end tangents in terms of direction, but twice as long
        middle_tangent = start_tangent + end_tangent

        # Create spline through the three points with specified tangents at each point
        points = [start_point, middle_point, end_point]
        tangents = [start_tangent, middle_tangent, end_tangent]

        edge = Edge.make_spline(points, tangents, scale=False)

        # return edge along the circle
        back = Edge.make_circle(start.length * offset, start_angle = get_angle(start) + 90, end_angle = get_angle(start) + angle + 90).move(Location(centre))

        # At least a minimal offset is needed for a shape to be valid
        offset_a = Edge.make_line(centre + start_rotated, centre + start_rotated * offset)
        offset_b = Edge.make_line(centre + start * offset, start_point)

        return Wire([edge, offset_a, back, offset_b])

    def create_handle(self, cap_45_inner: SmartSolid, middle_angle: float) -> SmartSolid:
        centre = Vector(cap_45_inner.x_mid, cap_45_inner.y_mid, cap_45_inner.z_max)
        radius = cap_45_inner.x_size / 2
        start_angle = middle_angle - self.dim.cap_handle_arc_angle / 2
        start = create_vector(radius, start_angle)

        top = self.create_handle_wire(centre, start, self.dim.cap_handle_arc_angle, -self.dim.cap_handle_width)
        bottom = self.create_handle_wire(centre - (0, 0, self.dim.cap_handle_height), create_vector(radius - self.dim.cap_handle_height, start_angle), self.dim.cap_handle_arc_angle, self.dim.cap_handle_height - self.dim.cap_handle_width)

        handle = SmartSolid(loft([Face(top), Face(bottom)]))
        handle.align_z(cap_45_inner, Alignment.RL)
        return handle

    def create_basket(self, with_handles: bool = False) -> SmartSolid:
        basket_outer, basket_inner = self._create_basket()
        for item in [basket_outer, basket_inner]:
            item.align_xy()

        cap_45_outer = create_cone_with_angle_and_height(self.dim.cap_radius_outer(self.dim.cap_depth), self.dim.cap_depth, self.dim.cap_angle)
        cap_45_outer.align_zxy(basket_outer, Alignment.RR)

        cap_45_inner = create_cone_with_angle_and_height(self.dim.cap_radius_inner(self.dim.cap_depth), self.dim.cap_depth, self.dim.cap_angle)
        cap_45_inner.align(cap_45_outer)

        ribs = self.create_ribs(basket_outer)

        basket = SmartSolid(basket_outer, cap_45_outer, ribs, label="basket_with_handles" if with_handles else "basket").cut(basket_inner, cap_45_inner)

        if with_handles:
            handles = [self.create_handle(cap_45_inner, angle) for angle in [90, -90]]
            basket.fuse(handles)

        return basket

    def create_ribs(self, basket_outer: SmartSolid) -> SmartSolid:
        leg_holder_boundary = SmartSolid(Solid.make_cylinder(self.dim.cap_diameter_outer_middle / 2, self.dim.leg_depth))
        leg_holder_boundary.align_zxy(basket_outer, Alignment.RL, self.dim.cap_depth)

        upper_rib_boundary = basket_outer.padded(self.dim.thickness * 2).align_zxy(basket_outer, Alignment.LR)

        rib = SmartBox(leg_holder_boundary.x_size, self.dim.cap_leg_width, leg_holder_boundary.z_size + basket_outer.z_size + self.dim.thickness * 2)
        ribs = [rib.oriented((0, 0, 180 / self.dim.cap_leg_count * i)).align_zxy(leg_holder_boundary, Alignment.RL) for i in range(self.dim.cap_leg_count)]

        return upper_rib_boundary.fuse(leg_holder_boundary).intersect(ribs)

    def create_cap_notch(self, cap: SmarterCone) -> SmartSolid:
        centre = Vector(cap.x_mid, cap.y_mid, cap.z_max)
        radius = cap.top_radius
        start_angle = -self.dim.cap_notch_arc_angle / 2
        start = create_vector(radius, start_angle)

        top = self.create_handle_wire(centre, start, self.dim.cap_notch_arc_angle, -self.dim.cap_notch_width)
        middle = self.create_handle_wire(centre - (0, 0, self.dim.cap_notch_height), create_vector(radius - self.dim.cap_notch_height, start_angle), self.dim.cap_notch_arc_angle, -self.dim.cap_notch_width)
        bottom = copy(middle).move(Location((0, 0, -self.dim.cap_notch_width)))

        notch_top = SmartSolid(loft([Face(top), Face(middle)]))
        notch_bottom = SmartSolid(loft([Face(middle), Face(bottom)]))
        return notch_top.fuse(notch_bottom)

    def create_basket_cap_and_latch(self, basket: SmartSolid, hole_diameter: float, with_legs: bool) -> Tuple[SmartSolid, SmartSolid]:
        cap_label = f"cap_{hole_diameter}mm{'_legs' if with_legs else ''}"
        cap = SmarterCone(self.dim.basket_cap_radius_narrow, self.dim.basket_cap_radius_wide, self.dim.cap_thickness, label=cap_label)
        cap.align_zxy(basket, Alignment.RL, self.dim.cap_thickness - self.dim.cap_depth)

        hole = SmarterCone.with_base_angle_and_height(hole_diameter / 2, self.dim.cap_thickness, 135).align(cap)

        latch_cut = self.create_latch(cap, hole.top_radius * 2, hole, 0)
        latch = self.create_latch(cap, hole.top_radius * 2, hole, 0.05, f"latch_{hole_diameter}mm")

        foundation = self._create_cap_foundation(cap, hole, with_legs)

        notch = self.create_cap_notch(cap)
        notch.align_y(cap, Alignment.RL, 0.01)

        return cap.fuse(foundation).cut(hole, latch_cut, notch), latch

    def create_foundation_support_triangle(self, radius: float, thickness: float) -> Face:
        pencil = Pencil()
        pencil.arc_with_radius(radius, 90, self.dim.foundation_hook_arc_angle / 3)
        pencil.jump_from_start((-thickness, 0))
        return pencil.create_mirrored_face(Axis.X)

    def create_foundation_support(self, foundation_inner: SmarterCone) -> SmartSolid:
        top = self.create_foundation_support_triangle(foundation_inner.top_radius, self.dim.cap_foundation_support_thickness).move(Location((0, 0, foundation_inner.z_size)))
        bottom = self.create_foundation_support_triangle(foundation_inner.base_radius, 0.001)
        return SmartSolid(loft([top, bottom]))

    def _create_cap_foundation(self, cap: SmartSolid, hole: SmarterCone, with_hooks: bool) -> SmartSolid | list[SmartSolid]:
        segment_angle = self.dim.foundation_hook_arc_angle if with_hooks else 360
        segment_height = self.dim.cap_foundation_hook_depth if with_hooks else self.dim.cap_foundation_depth
        base_angle = self.dim.cap_foundation_angle if with_hooks else -90 + self.dim.cone_slope_angle / 2

        foundation_outer = SmarterCone.with_base_angle_and_height(self.dim.foundation_hook_outer_radius, segment_height, base_angle, angle=segment_angle)
        foundation_outer.align_z(cap, Alignment.LL, self.dim.cap_foundation_offset)

        foundation_inner = SmarterCone.with_base_angle_and_height(self.dim.foundation_hook_inner_radius, segment_height, base_angle, angle=segment_angle)
        foundation_inner.align_z(foundation_outer)

        foundation = foundation_outer.cut(foundation_inner).rotate_with_axis(Axis.Z, -segment_angle / 2)

        if with_hooks:
            foundation_support = self.create_foundation_support(foundation_inner).align_z(foundation).align_x(foundation, Alignment.RL, -self.dim.foundation_thickness)
            foundation.fuse(foundation_support)
            foundation_hooks = [foundation.rotated_with_axis(Axis.Z, 360 / self.dim.window_count * (index + 0.5)) for index in [-1, 0, 3, 4]]
            return foundation_hooks
        else:
            foundation_cut = SmartBox(hole.top_radius * 2, self.dim.basket_cap_radius_wide, foundation_outer.z_size)
            foundation_cut.align_xz(foundation_outer).align_y(foundation_outer, Alignment.CL)
            return foundation.cut(foundation_cut)

    def create_latch(self, cap: SmartSolid, latch_width: float, hole: SmarterCone, gap: float, label=None) -> SmartSolid:
        pencil = Pencil()
        pencil.right(latch_width / 2 - gap)
        pencil.up((self.dim.cap_thickness - self.dim.cap_latch_thickness) / 2 + gap)
        pencil.jump((self.dim.cap_latch_thickness / 2 - gap, self.dim.cap_latch_thickness / 2 - gap))
        pencil.jump((-self.dim.cap_latch_thickness / 2 + gap, self.dim.cap_latch_thickness / 2 - gap))
        pencil.up((self.dim.cap_thickness - self.dim.cap_latch_thickness) / 2 + gap)
        latch = SmartSolid(pencil.extrude_mirrored(self.dim.basket_cap_radius_wide, Axis.Y), label=label).rotate((90, 0, 0))
        latch.align_zxy(cap, Alignment.C, 0, Alignment.C, 0, Alignment.CL, 0)

        return latch.cut(hole).intersect(cap)

def export_3mf(*solids, suffix: str = ""):
    for solid in solids:
        export(solid)
    save_3mf(f"models/hydroponic/basket/export{suffix}.3mf")
    if not suffix: # default model
        save_3mf()

def export_stl(*solids):
    for solid in solids:
        if not solid.label.startswith("latch_"):
            solid.mirror(Plane.XY)
        export(solid)
    save_stl("models/hydroponic/basket/stl")

def export_basket():
    dimensions = BasketDimensions()
    basket_factory = BasketFactory(dimensions)
    basket_solid = basket_factory.create_basket()
    basket_with_handles_solid = basket_factory.create_basket(True)
    basket_cap_solid, basket_latch_solid = basket_factory.create_basket_cap_and_latch(basket_solid, 10, False)

    cap_and_latch_variety = flatten(basket_factory.create_basket_cap_and_latch(basket_solid, diameter, hooks) for diameter in [4, 6, 8, 10, 12] for hooks in [True, False])

    export_3mf(basket_with_handles_solid, basket_cap_solid, basket_latch_solid)
    clear()
    export_stl(basket_solid, basket_with_handles_solid, *cap_and_latch_variety)

if __name__ == "__main__":
    export_basket()
