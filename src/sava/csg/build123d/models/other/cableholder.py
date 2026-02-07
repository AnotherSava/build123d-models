from dataclasses import dataclass, field
from math import asin, degrees

from build123d import Plane, Axis, Solid

from sava.common.advanced_math import COS_45
from sava.csg.build123d.common.exporter import export_3mf, export_stl
from sava.csg.build123d.common.geometry import Alignment
from sava.csg.build123d.common.pencil import Pencil
from sava.csg.build123d.common.smartbox import SmartBox
from sava.csg.build123d.common.smartercone import SmarterCone
from sava.csg.build123d.common.edgefilters import PositionalFilter
from sava.csg.build123d.common.smartsolid import SmartSolid
from sava.csg.build123d.common.smartsphere import SmartSphere
from sava.csg.build123d.common.text import create_text, TextDimensions


@dataclass(frozen=True)
class CableHolderDimensions:
    # Wall-mounted holder
    attachment_height: float = 20.0
    attachment_thickness: float = 3.0
    attachment_fillet_radius: float = 0.4
    ball_distance: float = 3.0

    # Cable ball
    ball_radius: float = 8
    ball_shell_thickness: float = 0.8
    ball_connector_height: float = 5
    ball_connector_padding_y: float = 0.1
    ball_large_connector_height: float = 2
    ball_tooth_offset: float = 1
    ball_tooth_size: float = 0.4
    ball_tooth_thickness: float = 0.8
    ball_text_depth: float = 0.4
    ball_text: TextDimensions = field(default_factory=lambda: TextDimensions(font_size=4, font="Seven Segment", height=-8)) # https://www.fontrepo.com/font/21332/seven-segment
    ball_opener_width: float = 0.4
    ball_opener_depth: float = 2.4

    ball_holder_thickness: float = 2
    ball_holder_channel_width: float = 7
    ball_holder_fillet_radius: float = 0.49
    ball_holder_gap: float = 0.2
    ball_holder_cut_fraction: float = 0.6

    # Top ring
    top_ring_tube_radius: float = 1.4
    top_ring_offset: float = 3
    top_ring_sphere_radius_multiplier: float = 1.5

    @property
    def ball_holder_radius_inner(self) -> float:
        return self.ball_radius + self.ball_holder_gap

    @property
    def top_ring_radius(self) -> float:
        return self.ball_holder_radius_inner * 0.97

    @property
    def top_ring_sphere_radius(self) -> float:
        return self.top_ring_tube_radius * self.top_ring_sphere_radius_multiplier


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

        quarter_box_out = SmartBox(quarter_box_in.x_size, dim.ball_large_connector_height - dim.ball_connector_padding_y, dim.ball_radius * 2)
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

        ball_holder = self.create_ball_holder()
        attachment = SmartBox(dim.ball_distance * (holder_count - 1) + ball_holder.x_size * holder_count, dim.attachment_thickness, dim.attachment_height, label="cable_holder")
        attachment.fillet_by(dim.attachment_fillet_radius, PositionalFilter(Axis.Y, inclusive=(False, True)))

        for i in range(holder_count):
            z = dim.attachment_height - ball_holder.z_size + dim.top_ring_sphere_radius - dim.top_ring_tube_radius
            ball_holder.align(attachment).x(Alignment.LR, (dim.ball_distance + ball_holder.x_size) * i).y(Alignment.LR, dim.attachment_thickness).z(Alignment.LR, z)
            attachment.fuse(ball_holder)

        return attachment

    def create_bottom_connector(self, ball_holder: SmartSolid, sphere: SmartSphere) -> SmartSolid:
        dim = self.dim
        pencil = Pencil(Plane.XZ)
        pencil.left(dim.ball_holder_thickness / 2).fillet(dim.ball_holder_fillet_radius)
        pencil.arc((ball_holder.x_size / 2, -ball_holder.z_size), (ball_holder.x_size, 0)).fillet()
        pencil.left()
        bottom_connector = pencil.extrude(dim.top_ring_radius + dim.top_ring_tube_radius * 2)
        bottom_connector.align(ball_holder).y(Alignment.CL).z(Alignment.LR)
        bottom_connector.cut(sphere.create_sphere(dim.ball_holder_radius_inner + dim.ball_holder_thickness / 2))
        return bottom_connector

    def create_ball_holder(self) -> SmartSolid:
        dim = self.dim
        sphere = SmartSphere(dim.ball_holder_radius_inner)
        ball_holder = sphere.create_shell(dim.ball_holder_thickness).cut_z(fraction=-dim.ball_holder_cut_fraction)
        bottom_connector = self.create_bottom_connector(ball_holder, sphere)

        cable_canal = SmartBox(dim.ball_holder_channel_width, ball_holder.y_size, ball_holder.z_size)
        cable_canal.align(ball_holder).y(Alignment.CR, -dim.ball_holder_channel_width / 2)
        cable_canal.fillet_z(dim.ball_holder_channel_width * 0.49)
        ball_holder.cut(cable_canal)
        bottom_connector.cut(cable_canal)
        bottom_connector.cut_z(bottom_connector.z_size - ball_holder.z_size)
        ball_holder.fillet_by(dim.ball_holder_fillet_radius, PositionalFilter(Axis.Z, ball_holder.z_max))
        ball_holder.fuse(bottom_connector)

        top_ring = self.create_top_ring()
        top_ring.align_z(sphere, Alignment.C, dim.top_ring_offset)

        return SmartSolid(ball_holder, top_ring, label="ball_holder")

    def create_top_connector(self) -> SmartSolid:
        dim = self.dim
        pencil = Pencil()
        length = dim.top_ring_radius + dim.top_ring_tube_radius * 2
        pencil.up(length)
        pencil.arc_with_radius(dim.top_ring_radius + dim.top_ring_tube_radius, 90, -180)
        pencil.down()
        connector = pencil.extrude(dim.top_ring_tube_radius * 2)

        side = SmarterCone.cylinder(dim.top_ring_tube_radius, length, Plane.XZ, 180).rotate_y(90)
        side.align(connector).x(Alignment.RR)
        connector.fuse(side)
        side.rotate_y(180).align(connector).x(Alignment.LL)
        connector.fuse(side)

        return connector

    def create_top_ring(self) -> SmartSolid:
        """Create a torus ring segment with a gap."""
        dim = self.dim

        # Calculate gap_angle so that the distance between spheres equals ball_holder_channel_width
        # Sphere centers are at radius (ring_radius + tube_radius) from Z axis (moved outward)
        # Chord distance formula: d = 2 * R * sin(gap_angle / 2)
        # Solving for gap_angle: gap_angle = 2 * arcsin(d / (2 * R))
        sphere_center_radius = dim.top_ring_radius + dim.top_ring_tube_radius
        desired_center_distance = dim.ball_holder_channel_width + 2 * dim.top_ring_sphere_radius
        gap_angle = degrees(2 * asin(desired_center_distance / (2 * sphere_center_radius)))

        # Create circular cross-section at ring_radius distance from Z axis
        # Use two 180° arcs since a single 360° arc fails (coincident endpoints)
        pencil = Pencil(Plane.XZ, start=(dim.top_ring_radius, 0))
        pencil.arc_with_radius(dim.top_ring_tube_radius, -90, 180)
        pencil.arc_with_radius(dim.top_ring_tube_radius, 90, 180)
        torus = pencil.revolve(360 - gap_angle, Axis.Z, enclose=True)

        for k in [0, 1]:
            plane = torus.create_plane_at(k)
            sphere = SmartSphere(dim.top_ring_sphere_radius, plane=plane)
            sphere.move_x(dim.top_ring_tube_radius, plane)
            torus.fuse(sphere)

        torus.rotate_z(90 + gap_angle / 2)
        top_connector = self.create_top_connector()
        top_connector.align(torus).y(Alignment.LR)
        return torus.fuse(top_connector)


if __name__ == "__main__":
    dimensions = CableHolderDimensions()
    cable_holder = CableHolder(dimensions)
    cable_ball_solids = [cable_holder.create_cable_ball(diameter / 10) for diameter in range(30, 43)]
    holder_solid = cable_holder.create_holder()

    export_3mf("models/other/cable_holder/export.3mf", holder_solid)
    export_stl("models/other/cable_holder/stl", holder_solid, *cable_ball_solids)
