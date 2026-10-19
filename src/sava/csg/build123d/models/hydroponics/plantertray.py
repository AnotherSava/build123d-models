from collections.abc import Callable
from dataclasses import dataclass, field
from functools import cached_property
from math import cos, radians, sin, sqrt

import numpy as np
from build123d import Axis, Edge, Text, TextAlign, Vector, Wire

from sava.csg.build123d.common.exporter import get_path
from sava.csg.build123d.common.geometry import Alignment
from sava.csg.build123d.common.modelspec import ModelSpec, export_model
from sava.csg.build123d.common.smartloft import SmartLoft
from sava.csg.build123d.common.smartsolid import SmartSolid, fuse
from sava.csg.build123d.common.text import TextDimensions, TextSolid, create_text
from sava.csg.build123d.models.hydroponics.tray import TrayDimensions, TrayFactory


@dataclass(frozen=True)
class PlanterTrayDimensions:
    length: float = 123.0  # major diameter of the ellipse, the axis the basket holes sit on
    width: float = 110.5  # minor diameter of the ellipse
    edge_wall: float = 5.0  # material left between the outer edge and the basket and watering holes' bevels, and between it and a peg hole
    total_height: float = 75.0  # from the tray's top to the peg feet

    # raised on the top surface's half away from the watering hole, as large as fits edge_wall clear of every hole and the edge
    label: str = "Таня,\nс днём\nрождения!"
    label_angle: float = 30.0  # baselines, counterclockwise from the major axis
    label_height: float = 0.6
    label_font: str = "Caveat"
    label_font_path: str = "input/fonts/caveat/Caveat-Regular.ttf"  # from the project root

    # basket hole profile, plate thickness, pegs and watering hole are the hydroponic tray's, the watering hole 50% wider
    tray: TrayDimensions = field(default_factory=lambda: TrayDimensions(watering_hole_radius_wide=TrayDimensions.watering_hole_radius_wide * 1.5))

    @property
    def thickness(self) -> float:
        return self.tray.tray_height

    @property
    def peg_height(self) -> float:
        # the peg's threaded part spans the plate, so only the rest hangs below it
        return self.total_height - self.thickness

    @property
    def basket_hole_offset_x(self) -> float:
        # the ellipse's vertex is the edge point nearest a hole centred this close to it
        return self.length / 2 - self.edge_wall - self.tray.basket_hole_width / 2

    @property
    def watering_hole_offset_y(self) -> float:
        # on the minor axis, whose vertex is the edge point nearest a hole centred this close to it
        return -(self.width / 2 - self.edge_wall - self.tray.watering_hole_radius_wide - self.tray.watering_hole_bevel)

    @cached_property
    def peg_hole_offset(self) -> Vector:
        # start beside the basket hole: at its x, midway between it and the edge
        x = self.basket_hole_offset_x
        y = (self.tray.basket_hole_width / 2 + self.width / 2 * sqrt(1 - (2 * x / self.length) ** 2)) / 2
        # then move equally along both axes until edge_wall is left, i.e. onto the ellipse offset inward by the peg hole radius plus edge_wall
        clearance = Wire.make_ellipse(self.length / 2, self.width / 2).offset_2d(-(self.tray.peg_hole_diameter / 2 + self.edge_wall))
        ray = Edge.make_line((x - y, 0), (x - y + self.length, self.length))
        points = clearance.intersect(ray)
        assert len(points) == 1
        return points[0].center()

    @property
    def peg_hole_centres(self) -> list[Vector]:
        return [Vector(direction_x * self.peg_hole_offset.X, direction_y * self.peg_hole_offset.Y) for direction_x in [-1, 1] for direction_y in [-1, 1]]


# One-piece elliptical variant of the hydroponic tray, holding two baskets and a watering hole, standing on pegs screwed in from below.
class PlanterTray:
    def __init__(self, dim: PlanterTrayDimensions) -> None:
        self.dim = dim
        self.tray_factory = TrayFactory(dim.tray)

    def create_tray(self) -> SmartSolid:
        tray = SmartLoft.extrude(Wire.make_ellipse(self.dim.length / 2, self.dim.width / 2), self.dim.thickness)
        tray.label = "planter_tray"

        basket_hole = self.tray_factory.create_basket_hole()
        tray.cut(fuse([basket_hole.copy().align_zxy(tray, Alignment.RL, shift_x=direction_x * self.dim.basket_hole_offset_x) for direction_x in [-1, 1]]))

        # the tray's peg hole turned upside down, so a peg screws in from below
        peg_hole_inner, peg_hole_outer = self.tray_factory.create_peg_hole_parts()
        peg_hole_inner.rotate_x(180)
        for centre in self.dim.peg_hole_centres:
            peg_hole_inner.align_xy(tray, Alignment.C, centre.X, centre.Y).align_z(tray)
            peg_hole_outer.colocate(peg_hole_inner)
            tray.cut(peg_hole_inner).fuse(peg_hole_outer)

        tray.cut(self.tray_factory.create_watering_hole().align_zxy(tray, Alignment.C, shift_y=self.dim.watering_hole_offset_y))

        return tray

    def create_label(self, tray: SmartSolid) -> SmartSolid:
        font_size, centres = self._fit_label()
        text = TextDimensions(font_size=font_size, font=self.dim.label_font, height=self.dim.label_height, font_path=get_path(self.dim.label_font_path))
        lines = TextSolid([create_text(text, line).align_xy(None).move_vector(centre) for line, centre in zip(self.dim.label.split("\n"), centres, strict=True)], label="planter_tray_label")
        label = lines.connected().rotate_z(self.dim.label_angle).align_z(tray, Alignment.RR)
        # the pane spans the lines' box, whose corners can reach past the edge; the glyphs themselves sit edge_wall inside it
        top_face = tray.solid.faces().sort_by(Axis.Z)[-1]
        return label.intersect(SmartLoft.extrude(top_face, self.dim.label_height))

    def _fit_label(self) -> tuple[float, list[Vector]]:
        """Largest font size at which every line's glyph box keeps edge_wall clear of the holes and the edge, inside the half away from the watering hole.

        Works in the label's own frame: `u` along the baselines, `v` across them. Each line slides along its baseline, and once the block's
        position across the baselines is chosen, every line is centred in the free span left for it. Returns the font size and each line's
        glyph box centre in that frame, the label turning by label_angle about the tray's centre to land on the tray.
        """
        angle = radians(self.dim.label_angle)
        assert 0 < angle < radians(90)
        u, v = Vector(cos(angle), sin(angle)), Vector(-sin(angle), cos(angle))
        lines = self.dim.label.split("\n")

        reference_size = 10
        boxes = [self._text_box(line, reference_size) for line in lines]
        # the font's own line spacing: how much taller a second line makes the same glyph
        one_line, two_lines = self._text_box("Х", reference_size), self._text_box("Х\nХ", reference_size)
        pitch = (two_lines[3] - two_lines[2]) - (one_line[3] - one_line[2])

        disks = [(centre.dot(u), centre.dot(v), radius + self.dim.edge_wall) for centre, radius in self._top_holes()]
        chord, v_min, v_max = self._clear_chord(u, v)

        def place(size: float, first_baseline: float) -> list[tuple[float, float, float, float]] | None:
            # per line: the free span for its left edge, its width, and its centre across the baselines
            scale = size / reference_size
            placed = []
            for index, (x_min, x_max, y_min, y_max) in enumerate(boxes):
                width = (x_max - x_min) * scale
                baseline = first_baseline - index * pitch * scale
                v_low, v_high = baseline + y_min * scale, baseline + y_max * scale
                if v_low < v_min or v_high > v_max:
                    return None
                (low_left, low_right), (high_left, high_right) = chord(v_low), chord(v_high)
                # the lowest corner is the start of the line's lower edge; keeping it at y >= 0 keeps the line on its half
                spans = [(max(low_left, high_left, -v_low * cos(angle) / sin(angle)), min(low_right, high_right) - width)]
                for disk_u, disk_v, radius in disks:
                    gap_v = max(v_low - disk_v, 0, disk_v - v_high)
                    if gap_v < radius:
                        gap_u = sqrt(radius ** 2 - gap_v ** 2)
                        spans = [piece for start, end in spans for piece in ((start, min(end, disk_u - width - gap_u)), (max(start, disk_u + gap_u), end)) if piece[0] <= piece[1]]
                spans = [span for span in spans if span[0] <= span[1]]
                if not spans:
                    return None
                start, end = max(spans, key=lambda span: span[1] - span[0])
                placed.append((start, end, width, (v_low + v_high) / 2))
            return placed

        baselines = np.arange(v_min, v_max, 0.05)
        smallest, largest = 0.0, self.dim.width
        for _ in range(20):
            size = (smallest + largest) / 2
            smallest, largest = (size, largest) if any(place(size, baseline) for baseline in baselines) else (smallest, size)

        # centre the block across the baselines within the widest run of positions that fit
        fitting = [place(smallest, baseline) is not None for baseline in baselines]
        runs, run_start = [], None
        for index, fits in enumerate([*fitting, False]):
            if fits and run_start is None:
                run_start = index
            elif not fits and run_start is not None:
                runs.append((run_start, index - 1))
                run_start = None
        run_start, run_end = max(runs, key=lambda run: run[1] - run[0])
        placed = place(smallest, (baselines[run_start] + baselines[run_end]) / 2)
        return smallest, [Vector((start + end) / 2 + width / 2, centre_v) for start, end, width, centre_v in placed]

    def _text_box(self, text: str, size: float) -> tuple[float, float, float, float]:
        # glyph bounding box relative to the first baseline's start
        box = Text(text, font_size=size, font=self.dim.label_font, font_path=get_path(self.dim.label_font_path), text_align=(TextAlign.LEFT, TextAlign.BOTTOM)).bounding_box()
        return box.min.X, box.max.X, box.min.Y, box.max.Y

    def _top_holes(self) -> list[tuple[Vector, float]]:
        # every hole's outline on the top surface: basket and watering holes at their bevel's rim, peg holes at the bore
        holes = [(Vector(direction_x * self.dim.basket_hole_offset_x, 0), self.dim.tray.basket_hole_width / 2) for direction_x in [-1, 1]]
        holes += [(centre, self.dim.tray.peg_hole_diameter / 2) for centre in self.dim.peg_hole_centres]
        holes.append((Vector(0, self.dim.watering_hole_offset_y), self.dim.tray.watering_hole_radius_wide + self.dim.tray.watering_hole_bevel))
        return holes

    def _clear_chord(self, u: Vector, v: Vector) -> tuple[Callable[[float], tuple[float, float]], float, float]:
        """The span along `u` lying edge_wall inside the ellipse, as a function of the position along `v`, with the range of `v` it exists in."""
        a, b, wall = self.dim.length / 2, self.dim.width / 2, self.dim.edge_wall
        theta = np.linspace(0, 2 * np.pi, 7200, endpoint=False)
        normal_x, normal_y = b * np.cos(theta), a * np.sin(theta)
        normal_length = np.hypot(normal_x, normal_y)
        # inner parallel curve: regular, and so convex, while edge_wall stays under the smallest radius of curvature, b² / a
        x, y = a * np.cos(theta) - wall * normal_x / normal_length, b * np.sin(theta) - wall * normal_y / normal_length
        along, across = x * u.X + y * u.Y, x * v.X + y * v.Y
        lowest, highest = int(np.argmin(across)), int(np.argmax(across))
        order = np.roll(np.arange(len(theta)), -lowest)
        split = (highest - lowest) % len(theta)
        rising, falling = order[:split + 1], np.append(order[split:], order[0])[::-1]
        chains = sorted([(across[rising], along[rising]), (across[falling], along[falling])], key=lambda chain: chain[1].mean())
        (left_v, left_u), (right_v, right_u) = chains

        def chord(position: float) -> tuple[float, float]:
            return float(np.interp(position, left_v, left_u)), float(np.interp(position, right_v, right_u))

        return chord, float(across[lowest]), float(across[highest])

    def create_peg(self) -> SmartSolid:
        # thread end up, collar against the tray's underside
        peg = self.tray_factory.create_plain_peg(self.dim.peg_height).rotate_x(180)
        # the pose TrayFactory.create_plain_peg builds in: thread end down on the bed
        peg.bed_orientation = (0, 0, 0)
        return peg


def _arrange_scene(dim: PlanterTrayDimensions, tray: SmartSolid, label: SmartSolid, peg: SmartSolid, watering_hole_cap: SmartSolid) -> list[SmartSolid]:
    scene = [tray, label, watering_hole_cap.copy().align_xy(tray, Alignment.C, 0, dim.watering_hole_offset_y).align_z(tray, Alignment.LR)]
    scene += [peg.copy().align_xy(tray, Alignment.C, centre.X, centre.Y).align_z(tray, Alignment.RL) for centre in dim.peg_hole_centres]
    return scene


def build() -> ModelSpec:
    dim = PlanterTrayDimensions()
    planter_tray = PlanterTray(dim)

    tray = planter_tray.create_tray()
    # printed where it stands in the scene, so its STL lines up with the tray's when both load as parts of one object
    label = planter_tray.create_label(tray)
    peg = planter_tray.create_peg()
    watering_hole_cap = planter_tray.tray_factory.create_watering_hole_cap()

    return ModelSpec(name="planter_tray", output_dir="models/hydroponic/planter_tray", scene=_arrange_scene(dim, tray, label, peg, watering_hole_cap), prints=[tray, label, peg, watering_hole_cap])


if __name__ == "__main__":
    export_model(build())
