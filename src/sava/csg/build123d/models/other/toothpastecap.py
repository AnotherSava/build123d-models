from dataclasses import dataclass
from math import cos, pi, sin

from bd_warehouse.thread import Thread
from build123d import Face, Vector, Wire

from sava.csg.build123d.common.geometry import Alignment
from sava.csg.build123d.common.modelspec import ModelSpec, export_model
from sava.csg.build123d.common.smartercone import SmarterCone
from sava.csg.build123d.common.smartloft import SmartLoft
from sava.csg.build123d.common.smartsolid import SmartSolid


@dataclass(frozen=True)
class ToothpasteCapDimensions:
    # Tube neck thread, as measured on the tube
    thread_diameter: float = 10.0
    thread_minor_diameter: float = 7.9
    thread_pitch: float = 1.45
    thread_length: float = 7.0
    # Added to both thread diameters so the printed cap screws onto the tube
    thread_clearance: float = 0.4
    # Axial widths of the cap's thread ridge at its crest and of its groove at the bottom; narrow ridges leave the
    # tube's teeth room along the axis, which the diameter clearance alone barely gives on steep flanks
    thread_ridge_width: float = 0.2
    thread_groove_width: float = 0.2

    # Between the thread's outer side and the ribs' inner side, and of the top
    wall_thickness: float = 1.5

    rib_count: int = 24
    # Rib height at the closed top (on the plate) and at the opening
    rib_height_top: float = 0.0
    rib_height_opening: float = 1.0

    @property
    def thread_major_diameter(self) -> float:
        return self.thread_diameter + self.thread_clearance

    @property
    def thread_root_diameter(self) -> float:
        return self.thread_minor_diameter + self.thread_clearance

    @property
    def body_radius(self) -> float:
        return self.thread_major_diameter / 2 + self.wall_thickness

    @property
    def height(self) -> float:
        return self.thread_length + self.wall_thickness


class ToothpasteCap:
    def __init__(self, dim: ToothpasteCapDimensions) -> None:
        self.dim = dim

    # Built top-down like a bucket: the top sits on the plate and the opening faces up
    def create(self) -> SmartSolid:
        body = SmartLoft.create(self._create_ribbed_profile(self.dim.rib_height_top), self._create_ribbed_profile(self.dim.rib_height_opening), self.dim.height)
        bolt = self._create_bolt()
        bolt.align_zxy(body, Alignment.LR, self.dim.wall_thickness)
        return SmartSolid(body.cut(bolt), label="toothpaste_cap")

    # Star outline of triangular ribs meeting base to base. Their bases are the sides of a polygon circumscribing
    # the body circle, so the wall is never thinner than wall_thickness, even between two ribs.
    def _create_ribbed_profile(self, rib_height: float) -> Face:
        step = pi / self.dim.rib_count
        radii = [self.dim.body_radius / cos(step), self.dim.body_radius + rib_height]
        points = [Vector(radii[i % 2] * cos(i * step), radii[i % 2] * sin(i * step)) for i in range(2 * self.dim.rib_count)]
        return Face(Wire.make_polygon(points, close=True))

    # The internal thread is cut with a threaded bolt: fusing bd_warehouse's internal IsoThread into a hole
    # silently adds nothing. The bolt copies the tube's measured thread, which is deeper than the ISO profile
    # for its pitch. The bolt (a core one pitch longer than thread_length, and the thread's raw top end) runs
    # out of the opening, so the thread stays full up to the rim.
    def _create_bolt(self) -> SmartSolid:
        pitch = self.dim.thread_pitch
        thread = Thread(apex_radius=self.dim.thread_major_diameter / 2, apex_width=self.dim.thread_groove_width, root_radius=self.dim.thread_root_diameter / 2, root_width=pitch - self.dim.thread_ridge_width, pitch=pitch, length=self.dim.thread_length, end_finishes=("fade", "raw"))
        core = SmarterCone.cylinder(thread.root_radius, self.dim.thread_length + pitch)
        return core.fuse(SmartSolid(thread))


def build() -> ModelSpec:
    dimensions = ToothpasteCapDimensions()
    toothpaste_cap = ToothpasteCap(dimensions)
    return ModelSpec(name="toothpaste_cap", output_dir="models/other/toothpaste_cap", scene=[toothpaste_cap.create()])


if __name__ == "__main__":
    export_model(build())
