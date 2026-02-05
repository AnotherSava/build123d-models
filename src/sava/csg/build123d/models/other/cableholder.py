from dataclasses import dataclass, field

from build123d import Plane, Axis, Solid, Location

from sava.common.advanced_math import COS_45
from sava.csg.build123d.common.exporter import export, save_3mf, save_stl, clear, export_3mf, export_stl, show_red
from sava.csg.build123d.common.geometry import Alignment
from sava.csg.build123d.common.pencil import Pencil
from sava.csg.build123d.common.smartbox import SmartBox
from sava.csg.build123d.common.smartercone import SmarterCone
from sava.csg.build123d.common.edgefilters import PositionalFilter, SurfaceFilter, FilletDebug
from sava.csg.build123d.common.smartsolid import SmartSolid
from sava.csg.build123d.common.smartsphere import SmartSphere
from sava.csg.build123d.common.text import create_text, TextDimensions


@dataclass(frozen=True)
class CableHolderDimensions:
    # Wall-mounted holder
    attachment_height: float = 20.0
    attachment_thickness: float = 3.0
    attachment_fillet_radius: float = 0.5
    ball_distance: float = 3.0
    holder_length_straight: float = 10.0
    holder_length_angled: float = 4.0
    holder_radius: float = 3.0
    holder_angle: float = 60.0
    holder_thickness: float = 3
    holder_width: tuple = (6.5, 5.6, 2.75)
    cut_offset: float = 2.0
    cut_angle: float = 2.0

    # Cable ball
    ball_radius: float = 8
    ball_shell_thickness: float = 0.8
    ball_connector_height: float = 5
    ball_connectors_padding_y: float = 0.1
    ball_large_connector_height: float = 2
    ball_tooth_offset: float = 1
    ball_tooth_size: float = 0.4
    ball_tooth_thickness: float = 0.8
    ball_text_depth: float = 0.4
    ball_text: TextDimensions = field(default_factory=lambda: TextDimensions(font_size=4, font="Seven Segment", height=-8)) # https://www.fontrepo.com/font/21332/seven-segment
    ball_opener_length: float = 2.55
    ball_opener_width: float = 0.4
    ball_opener_depth: float = 2.4

    ball_holder_thickness: float = 2
    ball_holder_cannel_width: float = 7
    ball_holder_fillet_radius: float = 0.61
    ball_holder_sphere_radius_gap: float = 0.2
    ball_holder_sphere_lock_fraction: float = 0.06

    @property
    def ball_holder_radius_inner(self) -> float:
        return self.ball_radius + self.ball_holder_sphere_radius_gap


class CableHolder:
    def __init__(self, dim: CableHolderDimensions):
        self.dim = dim

    def create_cable_ball_connector(self, radius: float) -> SmartSolid:
        dim = self.dim
        pencil = Pencil()
        pencil.arc_with_radius(radius, 180, 90)
        pencil.down(dim.ball_connector_height - radius)
        pencil.right()
        return pencil.revolve(enclose=False)

    def create_teeth(self, cable_canal: SmartSolid) -> SmartSolid:
        dim = self.dim
        side = cable_canal.x_size * (1 - COS_45) / 2 + dim.ball_tooth_size * COS_45
        tooth = SmartBox(side, side, dim.ball_tooth_thickness)
        teeth = []
        for align_x in [Alignment.LR, Alignment.RL]:
            for align_z in [Alignment.LR, Alignment.RL]:
                copy = tooth.copy()
                copy.align(cable_canal).x(align_x).y(Alignment.RL).z(align_z, align_z.shift_towards_centre(dim.ball_tooth_offset))
                teeth.append(copy)

        return SmartSolid(teeth)

    def create_cable_ball(self, cable_diameter: float) -> SmartSolid:
        dim = self.dim

        sphere = SmartSolid(Solid.make_sphere(dim.ball_radius, angle3=180), label=f"split_ball_{cable_diameter}_mm")
        sphere_inner = SmartSolid(Solid.make_sphere(dim.ball_radius - dim.ball_shell_thickness), label="split_ball")
        sphere_inner.align(sphere).y(Alignment.L)

        cable_canal = SmarterCone.cylinder(cable_diameter / 2, dim.ball_radius * 2)
        cable_canal.align(sphere).y(Alignment.L)

        text_canal = cable_canal.create_offset(thickness_side=dim.ball_text_depth)

        quarter_box_in = SmartBox(dim.ball_radius - cable_diameter / 2 - dim.ball_shell_thickness, dim.ball_large_connector_height, dim.ball_radius * 2)
        quarter_box_in.align(sphere).y(Alignment.LR).x(Alignment.LR)
        segment_in = quarter_box_in.intersected(sphere_inner)

        quarter_box_out = SmartBox(quarter_box_in.x_size, dim.ball_large_connector_height - dim.ball_connectors_padding_y, dim.ball_radius * 2)
        quarter_box_out.align(sphere).y(Alignment.LL).x(Alignment.RL)
        segment_out = quarter_box_out.intersected(sphere_inner)

        connector_radius = segment_in.x_size / 3.3
        connector_in = self.create_cable_ball_connector(connector_radius)
        connector_in.align(segment_out).x(shift=-connector_radius / 6).y(Alignment.LR)

        connector_out = self.create_cable_ball_connector(connector_radius).rotate_x(180)
        connector_out.align(segment_in).x(shift=connector_radius / 6).y(Alignment.RL)

        teeth = self.create_teeth(cable_canal).intersect(sphere)

        text = create_text(dim.ball_text, str(cable_diameter), Plane.XZ).rotate_y(90).intersect(text_canal).cut(cable_canal)

        opener = SmartBox(sphere.x_max - connector_in.x_mid, dim.ball_opener_depth, connector_in.z_size)
        opener.align(sphere).x(Alignment.LR).y(Alignment.LL, dim.ball_opener_width)
        sphere.cut(opener)

        opener.align(sphere).x(Alignment.RL).y(Alignment.LL)
        segment_out.cut(opener)

        return sphere.fuse(segment_out).cut(cable_canal, connector_in, segment_in, text).fuse(teeth, connector_out).rotate_x(-90)


    def create_holder(self, holder_count: int = 3) -> SmartSolid:
        dim = self.dim

        sphere = SmartSphere(dim.ball_holder_radius_inner, label="ball_holder").create_shell(dim.ball_holder_thickness)
        ball_holder = sphere.cut_z(-dim.ball_radius * (1 - dim.ball_holder_sphere_lock_fraction))
        cable_canal = SmartBox(dim.ball_holder_cannel_width, ball_holder.y_size, ball_holder.z_size)
        cable_canal.align(ball_holder).y(Alignment.CR, -dim.ball_holder_cannel_width / 2)
        cable_canal.fillet_z(dim.ball_holder_cannel_width * 0.49)
        ball_holder.cut(cable_canal)

        pencil = Pencil(Plane.YZ)
        pencil.right(dim.ball_holder_radius_inner + dim.ball_holder_thickness - dim.ball_holder_cannel_width / 2)
        pencil.down(ball_holder.z_size)
        pencil.fillet(dim.attachment_fillet_radius)
        pencil.spline_abs((dim.attachment_thickness, -dim.attachment_height), (0, -1), start_tangent=(-1, 0))
        pencil.left()
        attachment = pencil.extrude(dim.ball_distance * (holder_count - 1) + ball_holder.x_size * holder_count, "cable_holder")

        for i in range(holder_count):
            ball_holder.align(attachment).x(Alignment.LR, (dim.ball_distance + ball_holder.x_size) * i).y(Alignment.LR).z(Alignment.RL)
            sphere.colocate(ball_holder)
            inner_sphere = sphere.create_inner_sphere()
            attachment.fuse(ball_holder).cut(inner_sphere)

        attachment.fillet_by(dim.ball_holder_fillet_radius, PositionalFilter(Axis.Z, attachment.z_max), PositionalFilter(Axis.Y), PositionalFilter(Axis.X))
        attachment.fillet_by(dim.ball_holder_fillet_radius, PositionalFilter(Axis.X, attachment.x_min), PositionalFilter(Axis.Y))
        attachment.fillet_by(dim.ball_holder_fillet_radius, PositionalFilter(Axis.X, attachment.x_max), PositionalFilter(Axis.Y))

        return attachment

    def create_ball_holder(self) -> SmartSolid:
        dim = self.dim
        sphere = SmartSphere(dim.ball_holder_radius_inner, label="ball_holder").create_shell(dim.ball_holder_thickness)
        ball_holder = sphere.cut_z(-dim.ball_radius * (1 - dim.ball_holder_sphere_lock_fraction))
        cable_canal = SmartBox(dim.ball_holder_cannel_width, ball_holder.y_size, ball_holder.z_size)
        cable_canal.align(ball_holder).y(Alignment.CR, -dim.ball_holder_cannel_width / 2)
        cable_canal.fillet_z(dim.ball_holder_cannel_width * 0.49)
        ball_holder.cut(cable_canal)
        ball_holder.fillet_by(dim.ball_holder_fillet_radius, PositionalFilter(Axis.Z, ball_holder.z_max))
        return ball_holder


if __name__ == "__main__":
    dimensions = CableHolderDimensions()
    cable_holder = CableHolder(dimensions)
    models = [cable_holder.create_holder()]

    export_3mf("models/other/cable_holder/export.3mf", models[0])
    export_stl("models/other/cable_holder/stl", *models)
