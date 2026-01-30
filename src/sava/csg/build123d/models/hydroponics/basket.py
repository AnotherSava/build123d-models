from dataclasses import dataclass
from math import radians, degrees, atan, tan, cos
from typing import Tuple

from build123d import Plane, Axis, Location, Face

from sava.common.common import flatten
from sava.csg.build123d.common.exporter import export, save_3mf, save_stl, clear, show_red, show_green
from sava.csg.build123d.common.geometry import Alignment
from sava.csg.build123d.common.pencil import Pencil
from sava.csg.build123d.common.primitives import create_handle_solid, create_handle_wire
from sava.csg.build123d.common.smartbox import SmartBox
from sava.csg.build123d.common.smartercone import SmarterCone
from sava.csg.build123d.common.smartloft import SmartLoft
from sava.csg.build123d.common.smartsolid import SmartSolid


@dataclass
class BasketDimensions:
    sponge_diameter_top: float = 23
    inner_diameter_bottom: float = 11
    height: float = 65 # middle part of the basket
    window_angle: float = 30
    window_count: int = 8
    thickness: float = 1.6
    floor_count: int = 2
    floor_gap_height: float = 5

    rim_diameter_outer_wide: float = 38
    rim_diameter_outer_middle: float = 33
    rim_angle: float = 45
    rim_leg_width: float = 1.5
    rim_leg_count: int = 4
    leg_depth: float = 5.3

    lid_thickness: float = 3
    lid_latch_thickness: float = 2
    lid_foundation_depth: float = 2.5

    rim_handle_height: float = 1
    rim_handle_width: float = 2.6
    rim_handle_arc_angle: float = 45

    lid_foundation_angle: float = -94
    lid_foundation_offset: float = 0.1
    lid_foundation_support_thickness: float = 1.5
    lid_foundation_hook_depth: float = 1.2

    lid_notch_height: float = 1
    lid_notch_width: float = 1.5
    lid_notch_arc_angle: float = 30

    lid_support_handle_height: float = 1
    lid_support_wall_thickness: float = 1.5
    lid_support_wall_thickness_delta: float = 0.3
    lid_support_handle_width: float = 5.1
    lid_support_handle_width_delta: float = 0.2
    # lid_support_handle_width_delta: float = 0.05
    lid_support_handle_z_offset: float = 1.3
    lid_support_arc_angle: float = 25

    @property
    def foundation_thickness(self) -> float:
        return self.thickness * 2 / 3

    @property
    def foundation_hook_inner_radius(self) -> float:
        return self.lid_radius_narrow + self.lid_foundation_offset - self.foundation_thickness

    @property
    def foundation_hook_arc_angle(self) -> float:
        return self.window_angle * 2 / 3

    @property
    def rim_angle_radians(self) -> float:
        return radians(self.rim_angle)

    @property
    def window_angle_radians(self) -> float:
        return radians(self.window_angle)

    def radius_outer(self, offset_z: float = 0) -> float:
        """Outer radius of the rim at a given Z offset from the wide end.

        At offset 0, returns the widest radius. As offset increases (moving towards
        the basket body), the radius decreases based on the rim angle.
        """
        return self.rim_diameter_outer_wide / 2 - offset_z * tan(self.rim_angle_radians)

    def radius_inner(self, offset_z_towards_basket: float = 0) -> float:
        return self.radius_outer(offset_z_towards_basket) - self.thickness

    @property
    def lid_radius_wide(self) -> float:
        return self.radius_inner(self.rim_depth - self.lid_thickness)

    @property
    def lid_radius_narrow(self) -> float:
        return self.radius_inner(self.rim_depth)

    @property
    def outer_radius_top(self):
        return self.inner_radius_top + self.thickness

    @property
    def rim_depth(self):
        return (self.rim_diameter_outer_wide / 2 - self.outer_radius_top) / tan(self.rim_angle_radians)

    @property
    def inner_radius_top(self):
        return self.sponge_diameter_top / 2

    @property
    def outer_radius_bottom(self) -> float:
        return self.inner_diameter_bottom / 2 + self.thickness

    @property
    def triangle_height_at_rim(self) -> float:
        """Height of the triangular window top at the rim level."""
        radius_at_rim = self.outer_radius_bottom
        arc_length_at_rim = radius_at_rim * self.window_angle_radians
        return arc_length_at_rim / 2

    @property
    def gap_between_levels(self) -> float:
        """Gap height between window levels (reduced by triangle height)."""
        return self.floor_gap_height - self.triangle_height_at_rim

    @property
    def window_height(self) -> float:
        """Height of each window."""
        num_gaps_between = self.floor_count - 1
        total_gap_height = num_gaps_between * self.gap_between_levels
        remaining_height = self.height - total_gap_height + self.triangle_height_at_rim
        return remaining_height / self.floor_count

    @property
    def cone_slope_angle(self) -> float:
        """Cone slope angle from vertical (in degrees)."""
        radius_diff = self.outer_radius_top - self.outer_radius_bottom
        return degrees(atan(radius_diff / self.height))


class BasketFactory:
    def __init__(self, dim: BasketDimensions):
        self.dim = dim

    def _create_basket(self) -> Tuple[SmartSolid, SmarterCone]:
        outer = SmarterCone(self.dim.outer_radius_bottom, self.dim.outer_radius_top, self.dim.height)
        inner = outer.create_offset(-self.dim.thickness)

        point_end = SmarterCone(0, self.dim.outer_radius_bottom, self.dim.outer_radius_bottom).align_zxy(outer, Alignment.LL)
        point_end.create_shell(thickness_side=-self.dim.thickness)

        # Create all window cutouts
        windows = SmartSolid(self._create_all_windows()).align_z(outer, Alignment.RL)

        return outer.fuse(point_end).cut(windows), inner

    def _create_window_shape(self, distance: float) -> Face:
        width = distance * self.dim.window_angle_radians

        # Create half of pentagonal window to mirror across "Y" axis
        # Start at top middle, trace right side down to triangle tip
        pencil = Pencil(Plane.YZ)
        pencil.right(width / 2)
        pencil.down(self.dim.window_height - width / 2)
        pencil.jump((-width / 2, -width / 2))

        return pencil.create_mirrored_face_y(0).move(Location((distance, 0, 0)))

    def _create_window(self) -> SmartSolid:
        inner_face = self._create_window_shape(self.dim.inner_diameter_bottom / 3)
        outer_face = self._create_window_shape(self.dim.inner_radius_top * 1.5)

        return SmartLoft.create(inner_face, outer_face)

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

    def create_basket(self) -> SmartSolid:
        basket_outer, basket_inner = self._create_basket()

        rim_outer = SmarterCone.with_base_angle_and_height(self.dim.rim_diameter_outer_wide / 2, self.dim.rim_depth, -self.dim.rim_angle)
        rim_outer.align(basket_outer).z(Alignment.RR)

        rim_inner = rim_outer.create_offset(-self.dim.thickness)
        ribs = self._create_ribs(basket_outer)
        supports = [self._create_lid_supports(rim_inner, angle) for angle in [90, -90]]

        return SmartSolid(basket_outer, rim_outer, ribs, label=f"basket_{self.dim.height}mm").cut(basket_inner, rim_inner).fuse(supports)

    def _create_lid_supports(self, rim_inner: SmartSolid, angle: float) -> SmartSolid:
        lid_support_handle = create_handle_solid(self.dim.radius_inner(), self.dim.lid_support_arc_angle, self.dim.rim_depth, -self.dim.lid_support_handle_height)
        lid_support_handle.align_z(rim_inner, Alignment.RL)

        support_handle_shadow = SmartLoft.extrude(lid_support_handle.target_profile, -self.dim.rim_depth)
        wall = SmartBox(self.dim.lid_support_wall_thickness, self.dim.rim_diameter_outer_wide, self.dim.lid_thickness)
        wall.align(rim_inner).z(Alignment.LR)
        wall.intersect(rim_inner).intersect(support_handle_shadow)

        bottom = create_handle_wire(self.dim.radius_inner(), self.dim.lid_support_arc_angle - 4, -self.dim.rim_depth, (0, 0, lid_support_handle.target_profile.center().Z))
        smaller_bottom_face = Face(bottom) & lid_support_handle.target_profile

        top_wall_face = wall.solid.faces().sort_by(Axis.Z)[-1]
        transition_from_handle_to_wall = SmartLoft.create(top_wall_face, smaller_bottom_face)

        lid_support_handle.fuse(wall, transition_from_handle_to_wall)

        return lid_support_handle.rotate_z(angle)

    def _create_ribs(self, basket_outer: SmartSolid) -> SmartSolid:
        leg_holder_boundary = SmarterCone.cylinder(self.dim.rim_diameter_outer_middle / 2, self.dim.leg_depth)
        leg_holder_boundary.align_zxy(basket_outer, Alignment.RL, self.dim.rim_depth)

        upper_rib_boundary = basket_outer.padded(self.dim.thickness * 2).align_zxy(basket_outer, Alignment.LR)

        rib = SmartBox(leg_holder_boundary.x_size, self.dim.rim_leg_width, leg_holder_boundary.z_size + basket_outer.z_size + self.dim.thickness * 2)
        ribs = [rib.oriented((0, 0, 180 / self.dim.rim_leg_count * i)).align_zxy(leg_holder_boundary, Alignment.RL) for i in range(self.dim.rim_leg_count)]

        return upper_rib_boundary.fuse(leg_holder_boundary).intersect(ribs)

    def _create_pry_notch(self) -> SmartSolid:
        """Create a small notch on the lid edge for removal assistance.

        The notch provides a leverage point where a flat tool (knife tip, small
        screwdriver) can be inserted to pry the lid off the basket.
        """
        middle_wire = create_handle_wire(self.dim.lid_radius_wide - self.dim.lid_notch_height, self.dim.lid_notch_arc_angle, -self.dim.lid_notch_width)
        top_wire = create_handle_wire(self.dim.lid_radius_wide, self.dim.lid_notch_arc_angle, -self.dim.lid_notch_width)

        notch_top = SmartLoft.create(middle_wire, top_wire, self.dim.lid_notch_height)
        notch_bottom = SmartLoft.extrude(middle_wire, -self.dim.lid_notch_width)

        return notch_top.fuse(notch_bottom)

    def create_lid(self, basket: SmartSolid, hole_diameter: float) -> SmartSolid:
        lid_label = f"lid_{hole_diameter}mm"
        lid = SmarterCone(self.dim.lid_radius_narrow, self.dim.lid_radius_wide, self.dim.lid_thickness, angle=180, label=lid_label)
        lid.align(basket).y(Alignment.CR).z(Alignment.RL, self.dim.lid_thickness - self.dim.rim_depth)

        hole = SmarterCone.with_base_angle_and_height(hole_diameter / 2, self.dim.lid_thickness, 135)
        hole.align(lid).y(Alignment.L)

        for angle in [0, 180]:
            width = self.dim.lid_support_handle_width + self.dim.lid_support_handle_width_delta - self.dim.lid_support_handle_height - self.dim.lid_support_handle_z_offset
            support_cut = SmartBox(width, self.dim.lid_support_wall_thickness + self.dim.lid_support_wall_thickness_delta, self.dim.lid_thickness)
            support_cut.align(lid).xz(Alignment.RL).y(Alignment.L)
            lid.cut(support_cut.rotate_z(angle))

        foundation = self._create_lid_foundation(lid)
        notch = self._create_pry_notch().align_z(lid, Alignment.RL)

        return lid.fuse(foundation).cut(hole, notch)

    def _create_foundation_support_triangle(self, radius: float, thickness: float) -> Face:
        pencil = Pencil()
        pencil.arc_with_radius(radius, 90, self.dim.foundation_hook_arc_angle / 3)
        pencil.jump_to((-thickness, 0))
        return pencil.create_mirrored_face_x()

    def _create_foundation_support(self, foundation_inner: SmarterCone) -> SmartSolid:
        top = self._create_foundation_support_triangle(foundation_inner.top_radius, self.dim.lid_foundation_support_thickness)
        bottom = self._create_foundation_support_triangle(foundation_inner.base_radius, 0.001)

        return SmartLoft.create(bottom, top, foundation_inner.z_size)

    def _create_lid_foundation(self, lid: SmartSolid) -> list[SmartSolid]:
        dim = self.dim

        foundation_inner = SmarterCone.with_base_angle_and_height(dim.foundation_hook_inner_radius, dim.lid_foundation_hook_depth, dim.lid_foundation_angle, angle=dim.foundation_hook_arc_angle)
        foundation_inner.align_z(lid, Alignment.LL, dim.lid_foundation_offset)

        foundation = foundation_inner.create_shell(dim.foundation_thickness).rotate_z(-dim.foundation_hook_arc_angle / 2)

        foundation_support = self._create_foundation_support(foundation_inner)
        foundation_support.align(foundation).x(Alignment.RL, -dim.foundation_thickness)

        return [SmartSolid(foundation, foundation_support).rotate_z(360 / dim.window_count * (index + 0.5)) for index in [1, 2]]

def export_stl(*solids):
    clear()
    for solid in solids:
        if not solid.label.startswith("latch_"):
            solid.mirror(Plane.XY)
        export(solid)
    save_stl("models/hydroponic/basket/stl")

def create_basket(height: float) -> SmartSolid:
    dimensions = BasketDimensions()
    dimensions.height = height
    basket_factory = BasketFactory(dimensions)
    return basket_factory.create_basket()

def export_basket():
    dimensions = BasketDimensions()
    basket_factory = BasketFactory(dimensions)
    basket_solid = basket_factory.create_basket()
    lid_solid = basket_factory.create_lid(basket_solid, 10)

    export(lid_solid, label="lid_a")
    export(lid_solid.rotate_z(180), label="lid_b")
    export(basket_solid)
    save_3mf("models/hydroponic/basket/export.3mf", True)

    lid_variety = (basket_factory.create_lid(basket_solid, diameter) for diameter in [4, 6, 8, 10, 12])
    basket_variety = (create_basket(height) for height in [61, 63, 65])
    export_stl(*basket_variety, *lid_variety)

if __name__ == "__main__":
    export_basket()
