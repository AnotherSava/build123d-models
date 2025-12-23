from dataclasses import dataclass
from math import sin, radians, tan
from typing import Tuple

from bd_warehouse.thread import IsoThread
from build123d import Solid, Vector, Axis, Plane

from sava.csg.build123d.common.exporter import export, save_3mf, save_stl, clear
from sava.csg.build123d.common.geometry import Alignment
from sava.csg.build123d.common.pencil import Pencil
from sava.csg.build123d.common.primitives import create_cone_with_angle, create_cone_with_angle_and_height
from sava.csg.build123d.common.smartbox import SmartBox
from sava.csg.build123d.common.smartsolid import SmartSolid, fuse, PositionalFilter


@dataclass
class TrayDimensions:
    inner_length: float = 299
    inner_width: float = 165
    inner_height: float = 3
    inner_fillet_radius: float = 34
    outer_height: float = 1.2
    outer_padding: float = 2.5

    basket_width: float = 38.3
    basket_outer_diameter: float = 43.35
    basket_cap_angle: float = 45
    basket_cap_depth: float = 1.5
    basket_padding: float = 1.2
    basket_handle_width: float = 12
    basket_handle_length: float = 2

    cutout_angle: float = 5.9
    cutout_diameter: float = 52.6
    cutout_length: float = 38.7
    cutout_shift: float = 1

    watering_hole_bevel: float = 1.5
    watering_hole_radius_wide: float = 8
    watering_hole_radius_narrow: float = 7.5
    watering_hole_angle: float = 4

    peg_hole_diameter: float = 10
    peg_hole_thread_diameter_delta = 0.8
    peg_hole_pitch: float = 1

    peg_height: float = 23
    peg_fillet_radius: float = 0.2

    peg_base_height: float = 2
    peg_base_width_delta: float = 2
    peg_base_fillet_radius: float = 0.5

    peg_cap_hole_diameter: float = 5
    peg_cap_hole_height: float = 5
    peg_cap_hole_height_delta: float = 0.5
    peg_cap_hole_pitch: float = 0.85
    peg_cap_thread_diameter_delta = 0.2
    peg_cap_handle_height: float = 5
    peg_cap_fillet_radius: float = 0.2

    holder_thickness: float = 0.4

    columns: int = 7

    @property
    def tray_height(self) -> float:
        return self.inner_height + self.outer_height

    @property
    def outer_width(self) -> float:
        return self.inner_width + self.outer_padding * 2

    @property
    def outer_length(self) -> float:
        return self.inner_length + self.outer_padding * 2

    @property
    def basket_external_diameter(self) -> float:
        return self.basket_outer_diameter + self.basket_padding * 4

    @property
    def basket_distance_y(self) -> float:
        # Calculate to fit 4 holes in odd columns (3-4-3 pattern)
        return (self.outer_width - self.basket_width * 4) / 5

    @property
    def basket_bottom_diameter(self) -> float:
        return self.basket_outer_diameter - 2 * self.inner_height * tan(radians(self.basket_cap_angle))

    @property
    def watering_hole_offset_y(self) -> float:
        # Position in 3rd column (index 2), middle between first basket_hole and wall
        return (self.outer_width / 2 + self.basket_width * 1.5 + self.basket_distance_y) / 2

    @property
    def watering_hole_offset_x(self) -> float:
        # Position in 3rd column (index 2), middle between first basket_hole and wall
        return self.get_hole_offset(0, 2).X

    @property
    def peg_hole_offset_y(self) -> float:
        return self.watering_hole_offset_y

    @property
    def peg_hole_offset_x(self) -> float:
        return self.get_hole_offset(0, 0).X

    def get_hole_offset(self, row: int, column: int) -> Vector:
        step_y = self.basket_width + self.basket_distance_y
        step_x = (self.inner_length - self.basket_external_diameter) / (self.columns - 1)
        rows = 3 if column % 2 == 0 else 4
        shift_x = (column - (self.columns - 1) / 2) * step_x
        shift_y = (row - (rows - 1) / 2) * step_y
        return Vector(shift_x, shift_y)


# Replacement tray for the Ahopegarden 10 Pods hydroponic growing system. Optimized for germination with capacity extended to 23 pods.
class TrayFactory:
    def __init__(self, dim: TrayDimensions):
        self.dim = dim

    def create_tray(self) -> SmartSolid:
        inner_tray = SmartBox(self.dim.inner_length, self.dim.inner_width, self.dim.inner_height)
        inner_tray.fillet_z(self.dim.inner_fillet_radius)

        outer_tray = SmartBox(self.dim.outer_length, self.dim.outer_width, self.dim.outer_height)
        outer_tray.fillet_z(self .dim.inner_fillet_radius + self.dim.outer_padding)
        outer_tray.align_zxy(inner_tray, Alignment.LL)

        tray = inner_tray.fuse(outer_tray)

        cutout = self.create_cutout().align_x(tray, Alignment.C, self.dim.cutout_shift).align_y(tray, Alignment.LR).align_z(tray)
        tray.cut(cutout)

        basket_hole = self.create_basket_hole().align(tray)

        holes = []
        for column in range(self.dim.columns):
            for row in range(3 if column % 2 == 0 else 4):
                if column != self.dim.columns // 2 or row != 0:  # skip top basket_hole in middle column
                    holes.append(basket_hole.copy().move_vector(self.dim.get_hole_offset(row, column)))
        tray.cut(fuse(holes))

        watering_hole, watering_hole_external = self.create_watering_hole_parts()
        watering_hole.align_xy(tray, Alignment.C, self.dim.watering_hole_offset_x, self.dim.watering_hole_offset_y).align_z(tray, Alignment.LR)
        watering_hole_external.align(watering_hole)

        tray.fuse(watering_hole_external).cut(watering_hole)

        peg_hole_inner, peg_hole_outer = self.create_peg_hole_parts()
        for direction_x in [-1, 1]:
            for direction_y in [-1, 1]:
                peg_hole_inner.align_xy(tray, Alignment.C, direction_x * self.dim.peg_hole_offset_x, direction_y * self.dim.watering_hole_offset_y).align_z(tray, Alignment.LR)
                peg_hole_outer.align(peg_hole_inner)

                tray.cut(peg_hole_inner).fuse(peg_hole_outer)

        return self.prepare_for_print(tray)

    def prepare_for_print(self, tray: SmartSolid):
        # return tray

        tray.orient((0, 0, 45))

        print_size_x = 300
        print_size_y = 300
        print_area = SmartBox(print_size_x, print_size_y, 60).align(tray)
        return tray.intersect(print_area)

    def create_basket_hole(self) -> SmartSolid:
        bottom = SmartSolid(Solid.make_cylinder(self.dim.basket_outer_diameter / 2, self.dim.basket_cap_depth))
        cone = create_cone_with_angle_and_height(self.dim.basket_outer_diameter / 2, self.dim.inner_height, -self.dim.basket_cap_angle)
        cone.align_zxy(bottom, Alignment.RR)
        cone.fuse(bottom)

        box = SmartBox(cone.x_size, self.dim.basket_width, cone.z_size).align(cone) # flatten holes from top and bottom a bit
        cone.intersect(box)

        holder_round = SmartSolid(Solid.make_cone((self.dim.basket_width + self.dim.basket_distance_y - self.dim.holder_thickness) / 2, self.dim.basket_bottom_diameter / 2, cone.z_size)).align(cone)
        holder_box = SmartBox(self.dim.basket_handle_width, holder_round.x_size, holder_round.z_size).align(cone)

        return holder_box.intersect(holder_round).fuse(cone)

    def create_cutout(self) -> SmartSolid:
        l = (self.dim.cutout_length - self.dim.cutout_diameter / 2 * (1 + sin(radians(self.dim.cutout_angle))))

        pencil = Pencil()
        pencil.draw(l, -self.dim.cutout_angle)
        pencil.arc_with_radius(self.dim.cutout_diameter / 2, 90 - self.dim.cutout_angle, 180 + 2 * self.dim.cutout_angle)
        pencil.draw(l, 180 + self.dim.cutout_angle)

        return SmartSolid(pencil.extrude(self.dim.tray_height))

    def create_watering_hole_parts(self) -> Tuple[SmartSolid, SmartSolid]:
        cone_outer = create_cone_with_angle(self.dim.watering_hole_radius_wide + self.dim.basket_padding, self.dim.watering_hole_radius_narrow + self.dim.basket_padding, -self.dim.watering_hole_angle)
        cone_inner = create_cone_with_angle(self.dim.watering_hole_radius_wide, self.dim.watering_hole_radius_narrow, -self.dim.watering_hole_angle)
        ring = create_cone_with_angle_and_height(self.dim.watering_hole_radius_wide + self.dim.watering_hole_bevel + self.dim.basket_padding, self.dim.tray_height, -self.dim.basket_cap_angle)
        ring.align_zxy(cone_inner, Alignment.LR)
        return cone_inner.fuse(ring), cone_outer

    def create_peg_hole_parts(self) -> Tuple[SmartSolid, SmartSolid]:
        return self.create_hole_parts(self.dim.peg_hole_diameter, self.dim.tray_height, self.dim.peg_hole_pitch)

    def create_hole_parts(self, major_diameter: float, height: float, pitch: float) -> Tuple[SmartSolid, SmartSolid]:
        hole = Solid.make_cylinder(major_diameter / 2, height)
        thread = IsoThread(
            major_diameter=major_diameter,
            pitch=pitch,
            length=height,
            external=False,
            end_finishes=("chamfer", "fade")
        )
        print("hole ", thread.min_radius * 2, thread.root_radius * 2, thread.major_diameter, self.dim.peg_hole_diameter)

        return SmartSolid(hole), SmartSolid(thread)

    def create_peg_thread(self, simple: bool = False) -> IsoThread:
        return IsoThread(
            major_diameter=self.dim.peg_hole_diameter - self.dim.peg_hole_thread_diameter_delta,
            pitch=self.dim.peg_hole_pitch,
            length=self.dim.tray_height,
            external=True,
            end_finishes=("fade", "fade")
        )

    def create_peg(self) -> SmartSolid:
        thread = self.create_peg_thread()

        core_screw = SmartSolid(Solid.make_cylinder(thread.min_radius, thread.length + self.dim.peg_height))
        core_screw.fillet_positional(self.dim.peg_fillet_radius, None, PositionalFilter(Axis.Z, core_screw.z_min))

        thread_screw_solid = SmartSolid(thread)
        thread_screw_solid.align_zxy(core_screw, Alignment.RL)

        peg_base = create_cone_with_angle(thread.min_radius, thread.min_radius + self.dim.peg_base_width_delta)
        peg_base.align_zxy(core_screw, Alignment.RL, -thread.length)

        cap_hole, cap_thread = self.create_hole_parts(self.dim.peg_cap_hole_diameter, self.dim.peg_cap_hole_height, self.dim.peg_cap_hole_pitch)
        cap_hole.align_zxy(core_screw, Alignment.LR)
        cap_thread.colocate(cap_hole)

        cap_hole_cone = create_cone_with_angle(self.dim.peg_cap_hole_diameter / 2)
        cap_hole_cone.align_zxy(cap_hole, Alignment.RR)

        return core_screw.cut(cap_hole, cap_hole_cone).fuse(thread_screw_solid, cap_thread, peg_base)


    def create_peg_cap(self) -> SmartSolid:
        thread = IsoThread(
            major_diameter=self.dim.peg_cap_hole_diameter - self.dim.peg_cap_thread_diameter_delta,
            pitch=self.dim.peg_cap_hole_pitch,
            length=self.dim.peg_cap_hole_height - self.dim.peg_cap_hole_height_delta,
            external=True,
            end_finishes=("fade", "fade")
        )

        core_screw = SmartSolid(Solid.make_cylinder(thread.min_radius, thread.length + self.dim.peg_cap_handle_height))

        thread_screw_solid = SmartSolid(thread)
        thread_screw_solid.align_zxy(core_screw, Alignment.RL, -0.1)

        peg_radius = self.create_peg_thread(True).min_radius
        cap_base = SmartSolid(Solid.make_cylinder(peg_radius, self.dim.peg_cap_handle_height))
        cap_base.fillet_positional(self.dim.peg_cap_fillet_radius, None, PositionalFilter(Axis.Z, cap_base.z_min))
        cap_base.align_zxy(core_screw, Alignment.LR)

        return core_screw.fuse(thread_screw_solid, cap_base)


dimensions = TrayDimensions()
tray_factory = TrayFactory(dimensions)


def export_3mf(tray: SmartSolid, peg: SmartSolid, peg_cap: SmartSolid):
    clear()

    tray.mirror(Plane.XY)
    peg.mirror(Plane.XY)
    peg_cap.mirror(Plane.XY)

    export(tray, "tray")

    plane = Plane.XY.rotated((0, 0, 45))
    for direction_x in [-1, 1]:
        for direction_y in [-1, 1]:
            peg.align_xy(tray, Alignment.C, direction_x * dimensions.peg_hole_offset_x, direction_y * dimensions.watering_hole_offset_y, plane)
            peg.align_z(tray, Alignment.RR, -dimensions.tray_height)
            export(peg.copy(), "peg")

            peg_cap.align_zxy(peg, Alignment.RR, -dimensions.peg_cap_handle_height)
            export(peg_cap.copy(), "peg_cap")


    save_3mf()

tray_solid = tray_factory.create_tray()
peg_solid = tray_factory.create_peg()
peg_cap_solid = tray_factory.create_peg_cap()

export(tray_solid, "tray")
export(peg_solid, "peg")
export(peg_cap_solid, "peg_cap")
save_stl("models\\hydroponic\\tray")

export_3mf(tray_solid, peg_solid, peg_cap_solid)
