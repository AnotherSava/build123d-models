from pathlib import Path
from typing import Iterable

from build123d import Shape, Color, Mesher, Solid

from sava.csg.build123d.common.smartsolid import get_solid

CURRENT_MODEL_LOCATION = "models/current_model.3mf"

extra_shapes = []

def show_red(shape):
    extra_shapes.append(set_color(shape, "red"))

def show_blue(shape):
    extra_shapes.append(set_color(shape, "blue"))

def show_green(shape):
    extra_shapes.append(set_color(shape, "green"))

def set_color(shape: Shape, color: str = "yellow") -> Iterable[Solid]:
    result = []
    for solid in shape.solids(): # see https://github.com/gumyr/build123d/issues/929
        solid.color = Color(color)
        solid.label = color
        result.append(solid)
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
        self.exporter = Mesher()
        for shape in shapes:
            self.add(get_solid(shape))

    def add(self, shape: Shape, color: str = "yellow"):
        self.exporter.add_shape(set_color(shape, color))

    def export(self, location: str = None):
        for shape in extra_shapes:
            self.exporter.add_shape(shape)

        actual_location = location or get_path(CURRENT_MODEL_LOCATION)
        print(f"Exporting to {actual_location}")
        self.exporter.write(actual_location)
        print("Done")
