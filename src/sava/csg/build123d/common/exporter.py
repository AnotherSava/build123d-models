from copy import copy
from pathlib import Path
from typing import Iterable

from build123d import Shape, Color, Mesher, Solid, Plane

from sava.csg.build123d.common.smartplane import SmartPlane
from sava.csg.build123d.common.smartsolid import get_solid

CURRENT_MODEL_LOCATION = "models/current_model.3mf"

extra_shapes = []

def show_red(shape):
    extra_shapes.append(set_color(shape, "red"))

def show_blue(shape):
    extra_shapes.append(set_color(shape, "blue"))

def show_green(shape):
    extra_shapes.append(set_color(shape, "green"))

def set_color(shape: Shape, color: str = "yellow", label: str = None) -> Iterable[Solid]:
    result = []
    if isinstance(shape, Plane):
        solid = SmartPlane(shape).solid
    else:
        solid = get_solid(shape)
    if isinstance(solid, Iterable):
        for item in solid:
            result += set_color(item, color)
    else:
        solid_copy = copy(solid)
        solid_copy.color = Color(color)
        solid_copy.label = color if label is None else label
        result.append(solid_copy.clean())

    return result

def get_project_root_folder():
    current = Path(__file__).resolve()
    for parent in current.parents:
        if (parent / '.git').exists():
            return parent
    raise FileNotFoundError("Could not find project root")

def get_path(path_from_project_root: str) -> str:
    return str(get_project_root_folder() / path_from_project_root)

class Exporter:
    def __init__(self, *shapes):
        self.color_counts = {}
        self.exporter = Mesher()
        for shape in shapes:
            self.add(shape)

    def add(self, shape: Shape, color: str = "yellow", label: str = None) -> 'Exporter':
        colored_shapes = set_color(shape, color, label)
        self._add_shapes(colored_shapes)
        return self

    def _add_shapes(self, shapes: Iterable[Shape]):
        for shape in shapes:
            if isinstance(shape, Iterable):
                self._add_shapes(shape)
            else:
                color = shape.label
                self.color_counts[color] = (self.color_counts[color] if color in self.color_counts else 0) + 1
                self.exporter.add_shape(shape)

    def report_colors(self):
        for color, count in self.color_counts.items():
            print(f"{color + ':':<7} {count} shape(s)")

    def export(self, location: str = None):
        self._add_shapes(extra_shapes)

        actual_location = location or get_path(CURRENT_MODEL_LOCATION)
        print(f"\nExporting to {actual_location}\n")
        self.report_colors()

        self.exporter.write(actual_location)

        print(f"\nDone")
