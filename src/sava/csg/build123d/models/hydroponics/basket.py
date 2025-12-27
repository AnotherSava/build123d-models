from dataclasses import dataclass
from math import radians, degrees, atan, cos, tan
from typing import Tuple

from build123d import Solid, Vector, Plane, Axis

from sava.csg.build123d.common.exporter import export, save_3mf, save_stl, clear
from sava.csg.build123d.common.geometry import Alignment
from sava.csg.build123d.common.pencil import Pencil
from sava.csg.build123d.common.primitives import create_cone_with_angle_and_height
from sava.csg.build123d.common.smartbox import SmartBox
from sava.csg.build123d.common.smartcone import SmartCone
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

    basket_cover_thickness: float = 3
    basket_cover_hole_diameter: float = 6
    basket_cover_latch_thickness: float = 2
    basket_cover_foundation_depth: float = 2.5

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
    def basket_cover_radius_wide(self) -> float:
        return self.cap_radius_inner(self.cap_depth - self.basket_cover_thickness)

    @property
    def basket_cover_radius_narrow(self) -> float:
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
        outer = SmartSolid(Solid.make_cone(self.dim.outer_radius_top, self.dim.outer_radius_bottom, self.dim.height))

        inner = SmartSolid(Solid.make_cone(self.dim.inner_radius_top, self.dim.inner_diameter_bottom / 2, self.dim.height))
        inner.align_zxy(outer, Alignment.RL)

        cap_outer = SmartCone.create_empty(45, self.dim.outer_radius_bottom, self.dim.thickness * cos(radians(45)))
        cap_outer.align_zxy(outer, Alignment.RR)

        # Create all window cutouts
        windows = self._create_all_windows()

        return outer.fuse(cap_outer).cut(windows), inner

    def _create_window(self, window_z_bottom: float) -> SmartSolid:
        """Create a single window cutout at angle 0.

        Args:
            window_z_bottom: Bottom Z position of window

        Returns:
            SmartSolid: Window cutout solid
        """
        # Calculate derived positions
        window_z_top = window_z_bottom + self.dim.window_height
        window_z_center = window_z_bottom + self.dim.window_height / 2

        # Calculate radius at window bottom and top (for trapezoid shape)
        # Assumes outer cone z_min == 0
        z_param_bottom = window_z_bottom / self.dim.height
        z_param_top = window_z_top / self.dim.height

        radius_at_bottom = self.dim.outer_radius_top * (1 - z_param_bottom) + self.dim.outer_radius_bottom * z_param_bottom
        radius_at_top = self.dim.outer_radius_top * (1 - z_param_top) + self.dim.outer_radius_bottom * z_param_top
        radius_at_center = (radius_at_bottom + radius_at_top) / 2

        # Calculate arc lengths to maintain constant angular width
        arc_length_bottom = radius_at_bottom * self.dim.window_angle_radians
        arc_length_top = radius_at_top * self.dim.window_angle_radians

        # Window position at angle 0 (on positive X axis)
        x_pos = radius_at_center
        y_pos = 0

        # Create window with triangular top (45-45-90 triangle)
        window_depth = self.dim.thickness * 6  # Extra depth to ensure full cut through cap

        # For 45-45-90 triangle at top, height = base_width / 2
        triangle_height_top = arc_length_top / 2

        # Trapezoid height (total height minus only top triangle height)
        trapezoid_height = self.dim.window_height - triangle_height_top

        # Draw window profile in YZ plane (Y = arc width, Z = height)
        # Shape: trapezoid + top triangle (no bottom triangle)
        pencil = Pencil(start=(-arc_length_bottom / 2, 0), plane=Plane.YZ)
        pencil.jump_to(Vector(arc_length_bottom / 2, 0))  # Bottom right corner
        pencil.jump_to(Vector(arc_length_top / 2, trapezoid_height))  # Top right corner
        pencil.jump_to(Vector(0, trapezoid_height + triangle_height_top))  # Top peak
        pencil.jump_to(Vector(-arc_length_top / 2, trapezoid_height))  # Top left corner
        pencil.jump_to(Vector(-arc_length_bottom / 2, 0))  # Back to bottom left

        window = SmartSolid(pencil.extrude(window_depth))

        # Center the window at origin before rotating
        window.move(x=-window_depth / 2, z=-self.dim.window_height / 2)

        # Tilt to align perpendicular to cone wall
        window.rotate((0, -self.dim.cone_slope_angle, 0))

        # Move to final position
        window.move(x=x_pos - window.x_mid, y=y_pos - window.y_mid, z=window_z_center - window.z_mid)

        return window

    def _create_all_windows(self) -> list[SmartSolid]:
        """Create all window cutouts for all levels.

        Returns:
            list[SmartSolid]: List of all window cutout solids
        """
        windows = []
        current_z_offset = 0

        for level in range(self.dim.floor_count):
            # Z position for this window level (assumes cone z_min == 0)
            window_z_bottom = current_z_offset

            # Create one window at angle 0
            template_window = self._create_window(window_z_bottom)

            # Create copies rotated around the circumference
            angle_step = 360 / self.dim.window_count
            for i in range(self.dim.window_count):
                # Create a copy and rotate it around Z axis at origin
                windows.append(template_window.solid.rotate(Axis.Z, (i + 0.5) * angle_step))

            # Move to next level (use reduced gap between levels)
            current_z_offset += self.dim.window_height + self.dim.gap_between_levels

        return windows

    def create_basket(self) -> SmartSolid:
        """Create the complete basket with windows."""
        # Create the basic basket shell
        basket_outer, basket_inner = self._create_basket()
        for item in [basket_outer, basket_inner]:
            item.align_xy()

        cap_45_outer = create_cone_with_angle_and_height(self.dim.cap_radius_outer(), self.dim.cap_depth, -self.dim.cap_angle)
        cap_45_outer.align_zxy(basket_outer, Alignment.LL)

        cap_45_inner = create_cone_with_angle_and_height(self.dim.cap_radius_inner(), self.dim.cap_depth, -self.dim.cap_angle)
        cap_45_inner.align(cap_45_outer)

        cap_bottom = SmartSolid(Solid.make_cylinder(self.dim.cap_diameter_outer_middle / 2, self.dim.leg_depth))
        cap_bottom.align_zxy(cap_45_outer, Alignment.LR)

        leg = SmartBox(cap_bottom.x_size, self.dim.cap_leg_width, cap_bottom.z_size + basket_outer.z_size + self.dim.thickness * 2)

        legs = [leg.oriented((0, 0, 180 / self.dim.cap_leg_count * i)).align_zxy(cap_bottom, Alignment.LR) for i in range(self.dim.cap_leg_count)]
        cap_bottom.intersect(legs)

        legs_external = basket_outer.padded(self.dim.thickness * 2).align_zxy(basket_outer, Alignment.RL).intersect(legs)

        return SmartSolid(basket_outer, cap_bottom, cap_45_outer, legs_external, label="basket").cut(basket_inner, cap_45_inner)

    def create_basket_cover_and_latch(self, basket: SmartSolid) -> Tuple[SmartSolid, SmartSolid]:
        cover = SmartSolid(Solid.make_cone(self.dim.basket_cover_radius_wide, self.dim.basket_cover_radius_narrow, self.dim.basket_cover_thickness), label="cover")
        cover.align_zxy(basket, Alignment.LR, self.dim.cap_depth - self.dim.basket_cover_thickness)

        hole = create_cone_with_angle_and_height(self.dim.basket_cover_hole_diameter / 2, self.dim.basket_cover_thickness, 45).orient((180, 0, 0))
        hole.align(cover)

        latch_cut = self.create_latch(cover, hole, 0)
        latch = self.create_latch(cover, hole, 0.05)
        latch.label = "latch"

        foundation_outer = create_cone_with_angle_and_height(self.dim.basket_cover_radius_narrow, self.dim.basket_cover_foundation_depth, -self.dim.cone_slope_angle / 2)
        foundation_outer.align_zxy(cover, Alignment.RR)

        foundation_inner = create_cone_with_angle_and_height(self.dim.basket_cover_radius_narrow - self.dim.thickness / 2, self.dim.basket_cover_foundation_depth, -self.dim.cone_slope_angle / 2)
        foundation_inner.align(foundation_outer)

        foundation_cut = SmartBox(self.dim.basket_cover_hole_diameter, self.dim.basket_cover_radius_wide, foundation_outer.z_size)
        foundation_cut.align_xz(foundation_outer).align_y(foundation_outer, Alignment.CR)

        return cover.fuse(foundation_outer).cut(hole, latch_cut, foundation_inner, foundation_cut), latch

    def create_latch(self, cover: SmartSolid, hole: SmartSolid, gap: float = 0) -> SmartSolid:
        pencil = Pencil()
        pencil.right(self.dim.basket_cover_hole_diameter / 2 - gap / 2)
        pencil.up((self.dim.basket_cover_thickness - self.dim.basket_cover_latch_thickness) / 2 + gap / 2)
        pencil.jump((self.dim.basket_cover_latch_thickness / 2 - gap / 2, self.dim.basket_cover_latch_thickness / 2 - gap / 2))
        pencil.jump((-self.dim.basket_cover_latch_thickness / 2 + gap / 2, self.dim.basket_cover_latch_thickness / 2 - gap / 2))
        pencil.up((self.dim.basket_cover_thickness - self.dim.basket_cover_latch_thickness) / 2 + gap / 2)
        latch = SmartSolid(pencil.extrude_mirrored(self.dim.basket_cover_radius_wide, Axis.Y)).rotate((90, 0, 0))
        latch.align_zxy(cover, Alignment.C, 0, Alignment.C, 0, Alignment.CR, 0)
        return latch.cut(hole).intersect(cover)

def export_3mf(basket: SmartSolid, cover: SmartSolid, latch: SmartSolid):
    for item in [basket, cover, latch]:
        export(item.mirrored(Plane.XY))
    save_3mf()
    save_3mf("models/hydroponic/basket/export.3mf")

def export_stl(basket: SmartSolid, cover: SmartSolid, latch: SmartSolid):
    latch.mirror(Plane.XY)
    for item in [basket, cover, latch]:
        export(item)
    save_stl("models/hydroponic/basket/stl")

def export_basket():
    dimensions = BasketDimensions()
    basket_factory = BasketFactory(dimensions)
    basket_solid = basket_factory.create_basket()
    basket_cover_solid, basket_latch_solid = basket_factory.create_basket_cover_and_latch(basket_solid)

    export_3mf(basket_solid, basket_cover_solid, basket_latch_solid)
    clear()
    export_stl(basket_solid, basket_cover_solid, basket_latch_solid)

if __name__ == "__main__":
    export_basket()
