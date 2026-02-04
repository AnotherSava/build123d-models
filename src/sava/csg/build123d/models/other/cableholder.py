from dataclasses import dataclass, field

from build123d import Plane, Axis, Solid, Location

from sava.common.advanced_math import COS_45
from sava.csg.build123d.common.exporter import export, save_3mf, save_stl, clear, export_3mf, export_stl, show_red
from sava.csg.build123d.common.geometry import Alignment
from sava.csg.build123d.common.pencil import Pencil
from sava.csg.build123d.common.smartbox import SmartBox
from sava.csg.build123d.common.smartercone import SmarterCone
from sava.csg.build123d.common.smartsolid import SmartSolid
from sava.csg.build123d.common.smartsphere import SmartSphere
from sava.csg.build123d.common.text import create_text, TextDimensions


@dataclass(frozen=True)
class CableHolderDimensions:
    # Wall-mounted holder
    attachment_height: float = 20.0
    attachment_thickness: float = 3.0
    attachment_fillet_radius: float = 0.5
    holder_distance: float = 13.0
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
    ball_holder_cannel_width: float = 5


class CableHolder:
    def __init__(self, dim: CableHolderDimensions):
        self.dim = dim

    def create_holder(self, length: float) -> SmartSolid:
        dim = self.dim

        pencil = Pencil(Plane.XZ)
        pencil.up(dim.attachment_height)
        pencil.right(dim.holder_length_straight + dim.attachment_thickness)
        pencil.arc_with_radius(dim.holder_radius, 0, dim.holder_angle)
        pencil.arc_with_radius(dim.holder_thickness / 2, dim.holder_angle - 180, -180)
        pencil.arc_with_radius(dim.holder_radius + dim.holder_thickness, dim.holder_angle, -dim.holder_angle)
        pencil.left(dim.holder_length_straight)
        pencil.down()

        return pencil.extrude(length, "holder").fillet_y(dim.attachment_fillet_radius, Axis.X, inclusive=(True, False))

    def create_cut(self, width: float, attachment_length: float) -> SmartSolid:
        dim = self.dim
        pencil = Pencil()
        pencil.arc_with_radius(width / 2, -90, -90)
        pencil.draw(dim.holder_length_straight - dim.cut_offset, dim.cut_angle - 90)
        distance = attachment_length - dim.attachment_thickness - dim.cut_offset - pencil.location.X
        delta = 0.01
        pencil.spline((distance - delta, distance), (0, 1))
        pencil.right(delta)
        pencil.down()
        return pencil.extrude_mirrored_x(dim.holder_thickness + dim.holder_length_angled)

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


    def create(self) -> SmartSolid:
        dim = self.dim
        length = dim.holder_distance * len(dim.holder_width)
        holder = self.create_holder(length)
        for i, width in enumerate(dim.holder_width):
            cut = self.create_cut(width, holder.x_size)
            cut.align(holder).x(Alignment.LR, dim.attachment_thickness + dim.cut_offset).y(Alignment.L, dim.holder_distance * (i + 0.5)).z(Alignment.RL)
            holder = holder.cut(cut)

        return holder

    def create_ball_holder(self) -> SmartSolid:
        dim = self.dim
        ball_holder = SmartSphere(dim.ball_radius).create_shell(dim.ball_holder_thickness)
        ball_holder.cut_z(-dim.ball_radius * 0.9)
        cable_canal = SmartBox(dim.ball_holder_cannel_width, ball_holder.y_size / 2, ball_holder.z_size)
        cable_canal.align(ball_holder).y(Alignment.CR)
        ball_holder.cut(cable_canal)
        return ball_holder



if __name__ == "__main__":
    dimensions = CableHolderDimensions()
    cable_holder = CableHolder(dimensions)
    # model = cable_holder.create()
    # models = [cable_holder.create_cable_ball(diameter / 10) for diameter in range(30, 43)]
    models = [cable_holder.create_ball_holder()]

    export_3mf("models/other/cable_holder/export.3mf", models[0])
    export_stl("models/other/cable_holder/stl", *models)
