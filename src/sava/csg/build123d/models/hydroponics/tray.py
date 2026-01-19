from dataclasses import dataclass
from math import sin, radians, atan, sqrt, degrees
from typing import Tuple, Iterable

from bd_warehouse.fastener import hex_recess
from bd_warehouse.thread import IsoThread
from build123d import Solid, Vector, Axis, Plane, Wire, Face, loft, extrude

from sava.csg.build123d.common.exporter import export, save_3mf, clear, save_stl
from sava.csg.build123d.common.geometry import Alignment, create_vector
from sava.csg.build123d.common.modelcutter import cut_with_wires, CutSpec
from sava.csg.build123d.common.pencil import Pencil
from sava.csg.build123d.common.primitives import create_handle_wire
from sava.csg.build123d.common.smartbox import SmartBox
from sava.csg.build123d.common.smartercone import SmarterCone
from sava.csg.build123d.common.smartsolid import SmartSolid, fuse, PositionalFilter
from sava.csg.build123d.models.hydroponics.basket import BasketDimensions


@dataclass
class TrayDimensions:
    inner_length: float = 301
    inner_width: float = 167
    inner_height: float = 5
    inner_fillet_radius: float = 30
    outer_height: float = 1.2
    outer_padding: float = 2.5

    holder_width: float = 3
    holder_length: float = 4.8
    holder_offset: float = 1.2
    holder_depth: float = 2.5

    basket_gap: float = 0.2 # gap between basket and its hole
    basket_notch_angle: float = -37.5
    basket_notch_arc_angle: float = 40
    basket_notch_width: float = 3

    cutout_angle: float = 5.9
    cutout_diameter: float = 52.6
    cutout_length: float = 38.7

    watering_hole_bevel: float = 2.7
    watering_hole_radius_wide: float = 8
    watering_hole_angle: float = -86
    watering_hole_cap_handle_radius: float = 2
    watering_hole_cap_handle_height: float = 8
    watering_hole_cap_handle_ball_radius: float = 3
    watering_hole_cap_radius_delta: float = 0.1

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
    peg_cap_hex_socket_size: float = 4
    peg_cap_hex_socket_depth: float = 2.5

    basket_dimensions: BasketDimensions = None

    columns: int = 7

    @property
    def basket_hole_width(self) -> float:
        return self.basket_dimensions.cap_diameter_outer_wide + self.basket_gap

    def __post_init__(self):
        if self.basket_dimensions is None:
            self.basket_dimensions = BasketDimensions()

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
    def basket_distance_y(self) -> float:
        # Calculate to fit 4 holes in odd columns (3-4-3 pattern)
        return (self.outer_width - self.basket_hole_width * 4) / 5

    @property
    def basket_distance_x(self) -> float:
        # Calculate to fit 7 columns of holes
        return (self.outer_length - self.basket_hole_width * 7) / 8

    @property
    def watering_hole_offset_y(self) -> float:
        # Position in 3rd column (index 2), middle between first basket_hole and wall
        return -(self.inner_width / 2 + self.basket_hole_width * 1.5 + self.basket_distance_y * 1.25) / 2

    @property
    def watering_hole_offset_x(self) -> float:
        # Position in 3rd column (index 2), middle between first basket_hole and wall
        return self.get_hole_offset(2, 0).X

    @property
    def peg_hole_offset_y(self) -> float:
        return self.watering_hole_offset_y

    @property
    def peg_hole_offset_x(self) -> float:
        return self.get_hole_offset(0, 0).X

    @property
    def hole_step_x(self):
        return self.basket_hole_width + self.basket_distance_x

    @property
    def hole_step_y(self):
        return self.basket_hole_width + self.basket_distance_y

    def get_hole_offset(self, column: int, row: int) -> Vector:
        rows = 3 if column % 2 == 0 else 4
        shift_x = (column - (self.columns - 1) / 2) * self.hole_step_x
        shift_y = (row - (rows - 1) / 2) * self.hole_step_y
        return Vector(shift_x, shift_y)


# Replacement tray for the Ahopegarden 10 Pods hydroponic growing system. Optimized for germination with capacity extended to 23 pods.
class TrayFactory:
    def __init__(self, dim: TrayDimensions):
        self.dim = dim

    def create_tray(self, peg_holes: bool = True) -> list[SmartSolid]:
        inner_tray = SmartBox(self.dim.inner_length, self.dim.inner_width, self.dim.inner_height)
        inner_tray.fillet_z(self.dim.inner_fillet_radius)

        outer_tray = SmartBox(self.dim.outer_length, self.dim.outer_width, self.dim.outer_height)
        outer_tray.fillet_z(self.dim.inner_fillet_radius + self.dim.outer_padding)
        outer_tray.align_zxy(inner_tray, Alignment.RR)

        tray = SmartSolid(inner_tray, outer_tray, label=f"tray{'' if peg_holes else '_no_peg_holes'}")

        cutout = self.create_cutout()
        cutout.align_xz(tray).align_y(tray, Alignment.RL)
        tray.cut(cutout)

        holder_cutouts = self.create_holder_cutouts(inner_tray, cutout)
        tray.cut(holder_cutouts)

        basket_hole = self.create_basket_hole().align_zxy(tray, Alignment.RL)

        holes = []
        for column in range(self.dim.columns):
            for row in range(3 if column % 2 == 0 else 4):
                if column != self.dim.columns // 2 or row != 3:  # skip top basket_hole in middle column
                    holes.append(basket_hole.copy().move_vector(self.dim.get_hole_offset(column, row)))
        tray.cut(fuse(holes))

        watering_hole = self.create_watering_hole()
        watering_hole.align_xy(tray, Alignment.C, self.dim.watering_hole_offset_x, self.dim.watering_hole_offset_y).align_z(tray)

        tray.cut(watering_hole)

        if peg_holes:
            peg_hole_inner, peg_hole_outer = self.create_peg_hole_parts()
            for direction_x in [-1, 1]:
                for direction_y in [-1, 1]:
                    peg_hole_inner.align_xy(tray, Alignment.C, direction_x * self.dim.peg_hole_offset_x, direction_y * self.dim.watering_hole_offset_y).align_z(tray)
                    peg_hole_outer.align(peg_hole_inner)
                    tray.cut(peg_hole_inner).fuse(peg_hole_outer)

        # Cut tray between columns 2 and 3
        cutting_wire = self._create_cutting_wire(tray)
        return cut_with_wires(tray, CutSpec(cutting_wire, Plane.XZ, 0.2))

    def create_holder_cutouts(self, inner_tray: SmartSolid, light_cutout: SmartSolid) -> SmartSolid:
        cutout = SmartBox(self.dim.holder_length, self.dim.holder_width, self.dim.inner_height - self.dim.holder_depth)
        cutout.align_z(inner_tray, Alignment.RL, -self.dim.holder_depth)

        #tray orientation is with light cutout in the back

        return SmartSolid(
            cutout.copy().align_x(inner_tray, Alignment.LR, self.dim.holder_offset).align_y(inner_tray, Alignment.L, 71.5),  # left
            cutout.copy().align_x(inner_tray, Alignment.RL, -self.dim.holder_offset).align_y(inner_tray, Alignment.L, 72),  # right

            cutout.oriented((0, 0, 90)).align_x(light_cutout).align_y(light_cutout, Alignment.LL, -self.dim.holder_offset),  # back
            cutout.oriented((0, 0, 90)).align_x(inner_tray, Alignment.L, 70).align_y(inner_tray, Alignment.RL, -self.dim.holder_offset),  # back
            cutout.oriented((0, 0, 90)).align_x(inner_tray, Alignment.R, -70).align_y(inner_tray, Alignment.RL, -self.dim.holder_offset),  # back

            cutout.oriented((0, 0, 90)).align_x(inner_tray, Alignment.R, -70).align_y(inner_tray, Alignment.LR, self.dim.holder_offset),  # front
            cutout.oriented((0, 0, 90)).align_x(inner_tray, Alignment.R, -70 - 55.5).align_y(inner_tray, Alignment.LR, self.dim.holder_offset),  # front
            cutout.oriented((0, 0, 90)).align_x(inner_tray, Alignment.L, 71).align_y(inner_tray, Alignment.LR, self.dim.holder_offset),  # front
            cutout.oriented((0, 0, 90)).align_x(inner_tray, Alignment.L, 71 + 55.5).align_y(inner_tray, Alignment.LR, self.dim.holder_offset),  # front
        )

    def _create_cutting_wire(self, tray: SmartSolid) -> Wire:
        angle = degrees(atan(self.dim.hole_step_y / (2 * self.dim.hole_step_x)))
        l = sqrt(4 * self.dim.hole_step_x ** 2 + self.dim.hole_step_y ** 2) / 4
        v1 = self.dim.get_hole_offset(3, 0)
        v2 = self.dim.get_hole_offset(4, 0)
        delta_x = self.dim.tray_height / 4 # since cut goes 45 degrees to the left
        start = (v1 + v2) / 2 + Vector(tray.x_mid + delta_x, tray.y_mid, tray.z_mid)
        pencil = Pencil(start - create_vector(self.dim.outer_width / 2, angle))
        pencil.draw(self.dim.outer_width / 2 + l / 2, angle)
        pencil.draw(l, -angle)
        pencil.draw(l, angle)
        pencil.draw(l, -angle)
        pencil.draw(self.dim.outer_width / 2, angle)
        return pencil.create_wire(False)

    def prepare_for_print(self, tray: SmartSolid):
        # return tray

        tray.orient((0, 0, 45))

        print_size_x = 300
        print_size_y = 300
        print_area = SmartBox(print_size_x, print_size_y, 60).align(tray)
        return tray.intersect(print_area)

    def create_basket_hole(self) -> SmartSolid:
        dim = self.dim.basket_dimensions
        cap_45_outer = SmarterCone.with_base_angle(dim.cap_diameter_outer_middle / 2 + self.dim.basket_gap, 180 - dim.cap_angle, self.dim.basket_hole_width / 2)

        leg_holder_boundary = SmarterCone.cylinder(dim.cap_diameter_outer_middle / 2 + self.dim.basket_gap, self.dim.tray_height)
        leg_holder_boundary.align_zxy(cap_45_outer, Alignment.RL)

        for angle_shift in [0, 180]:
            start_arc_angle = self.dim.basket_notch_angle - self.dim.basket_notch_arc_angle / 2 + angle_shift
            top = create_handle_wire(cap_45_outer.center(1), create_vector(cap_45_outer.top_radius, start_arc_angle), self.dim.basket_notch_arc_angle, self.dim.basket_notch_width)
            bottom = create_handle_wire(cap_45_outer.center(0.5), create_vector(cap_45_outer.radius(0.5), start_arc_angle), self.dim.basket_notch_arc_angle, 0.1)
            handle = SmartSolid(loft([Face(top), Face(bottom)]))
            cap_45_outer.fuse(handle)

        return cap_45_outer.fuse(leg_holder_boundary)

    def create_cutout(self) -> SmartSolid:
        l = (self.dim.cutout_length - self.dim.cutout_diameter / 2 * (1 + sin(radians(self.dim.cutout_angle))))

        pencil = Pencil()
        pencil.draw(l, 180 + self.dim.cutout_angle)
        pencil.arc_with_radius(self.dim.cutout_diameter / 2, 90 + self.dim.cutout_angle, -90 - self.dim.cutout_angle)

        return pencil.extrude_mirrored_y(self.dim.tray_height, pencil.location.X)

    def create_watering_hole(self, radius_delta: float = 0) -> SmartSolid:
        radius_wide = self.dim.watering_hole_radius_wide - radius_delta
        central_cone = SmarterCone.with_base_angle_and_height(radius_wide, self.dim.tray_height, self.dim.watering_hole_angle)
        top_cone = SmarterCone.with_base_angle_and_height(radius_wide + self.dim.watering_hole_bevel, self.dim.tray_height, -45)
        top_cone.align_zxy(central_cone, Alignment.RL)
        return central_cone.fuse(top_cone)

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

        peg = SmarterCone.cylinder(thread.min_radius, thread.length + self.dim.peg_height, label="peg")
        peg.fillet_positional(self.dim.peg_fillet_radius, None, PositionalFilter(Axis.Z, peg.z_max))

        thread_screw_solid = SmartSolid(thread)
        thread_screw_solid.align_zxy(peg, Alignment.LR)

        peg_base = SmarterCone.with_base_angle_and_height(thread.min_radius, -self.dim.peg_base_width_delta, 45)
        peg_base.align_zxy(peg, Alignment.LR, thread.length)

        cap_hole, cap_thread = self.create_hole_parts(self.dim.peg_cap_hole_diameter, self.dim.peg_cap_hole_height, self.dim.peg_cap_hole_pitch)
        cap_hole.align_zxy(peg, Alignment.RL)
        cap_thread.colocate(cap_hole)

        cap_hole_cone = SmarterCone.with_base_angle(self.dim.peg_cap_hole_diameter / 2, -45)
        cap_hole_cone.align_zxy(cap_hole, Alignment.LL)

        return peg.cut(cap_hole, cap_hole_cone).fuse(thread_screw_solid, cap_thread, peg_base)


    def create_peg_cap(self) -> SmartSolid:
        thread = IsoThread(
            major_diameter=self.dim.peg_cap_hole_diameter - self.dim.peg_cap_thread_diameter_delta,
            pitch=self.dim.peg_cap_hole_pitch,
            length=self.dim.peg_cap_hole_height - self.dim.peg_cap_hole_height_delta,
            external=True,
            end_finishes=("fade", "fade")
        )

        peg_cap = SmarterCone.cylinder(thread.min_radius, thread.length + self.dim.peg_cap_handle_height, label="peg_cap")

        thread_screw_solid = SmartSolid(thread)
        thread_screw_solid.align_zxy(peg_cap, Alignment.LR, 0.1)

        peg_radius = self.create_peg_thread(True).min_radius
        cap_base = SmarterCone.cylinder(peg_radius, self.dim.peg_cap_handle_height)
        cap_base.fillet_positional(self.dim.peg_cap_fillet_radius, None, PositionalFilter(Axis.Z, cap_base.z_max))
        cap_base.align_zxy(peg_cap, Alignment.RL)

        hex_socket_face = hex_recess(self.dim.peg_cap_hex_socket_size)
        hex_socket = SmartSolid(extrude(hex_socket_face, self.dim.peg_cap_hex_socket_depth))
        hex_socket.align_zxy(peg_cap, Alignment.RL)

        return peg_cap.fuse(thread_screw_solid, cap_base).cut(hex_socket)

    def create_watering_hole_cap(self) -> SmartSolid:
        watering_hole = self.create_watering_hole(self.dim.watering_hole_cap_radius_delta)

        handle = SmarterCone.cylinder(self.dim.watering_hole_cap_handle_radius, self.dim.watering_hole_cap_handle_height)
        handle.align_zxy(watering_hole, Alignment.RR)

        ball = SmartSolid(Solid.make_sphere(self.dim.watering_hole_cap_handle_ball_radius))
        ball.align_zxy(handle, Alignment.RL, self.dim.watering_hole_cap_handle_ball_radius)

        return SmartSolid(watering_hole, handle, ball, label="watering_hole_cap")


dimensions = TrayDimensions()
tray_factory = TrayFactory(dimensions)


def export_3mf(tray_pieces: Iterable[SmartSolid], peg: SmartSolid, peg_cap: SmartSolid, watering_hole_cap: SmartSolid):
    for piece in tray_pieces:
        export(piece)

    tray = SmartSolid(tray_pieces)

    for direction_x in [-1, 1]:
        for direction_y in [-1, 1]:
            peg.align_xy(tray, Alignment.C, direction_x * dimensions.peg_hole_offset_x, direction_y * dimensions.watering_hole_offset_y)
            peg.align_z(tray, Alignment.RR, -dimensions.tray_height)
            export(peg.copy())

            peg_cap.align_zxy(peg, Alignment.RL, dimensions.peg_cap_handle_height)
            export(peg_cap.copy())

    watering_hole_cap.align_xy(tray, Alignment.C, dimensions.watering_hole_offset_x, dimensions.watering_hole_offset_y)
    watering_hole_cap.align_z(tray, Alignment.LR)
    export(watering_hole_cap)

    save_3mf("models/hydroponic/tray/export.3mf", current=True)

def export_all():
    tray_solid_pieces = tray_factory.create_tray()
    tray_solid_pieces_no_peg_holes = tray_factory.create_tray(False)
    peg_solid = tray_factory.create_peg()
    peg_cap_solid = tray_factory.create_peg_cap()
    watering_hole_cap_solid = tray_factory.create_watering_hole_cap()

    export_3mf(tray_solid_pieces, peg_solid, peg_cap_solid, watering_hole_cap_solid)

    clear()
    for piece in [*tray_solid_pieces, *tray_solid_pieces_no_peg_holes]:
        export(piece)

    export(peg_solid)
    export(peg_cap_solid)
    export(watering_hole_cap_solid)

    save_stl("models/hydroponic/tray/stl")

export_all()
