from pathlib import Path

from build123d import Shape, Color, Mesher

CURRENT_MODEL_LOCATION = "models/current_model.3mf"

extra_shapes = []

def show_red(shape):
    extra_shapes.append(set_color(shape, "red"))

def set_color(shape: Shape, color: str = "yellow") -> Shape:
    shape = shape.solid()
    shape.color = Color(color)
    shape.label = color
    return shape

def get_project_root_folder():
    current = Path(__file__).resolve()
    for parent in current.parents:
        if (parent / '.git').exists():
            return parent
    raise FileNotFoundError("Could not find project root")


class Exporter:
    def __init__(self, *shapes):
        self.exporter = Mesher()
        for shape in shapes:
            self.add(shape)

    def add(self, shape: Shape, color: str = "yellow"):
        self.exporter.add_shape(set_color(shape, color))

    def export(self, location: str = None):
        for shape in extra_shapes:
            self.exporter.add_shape(shape)

        actual_location = location or str(get_project_root_folder() / CURRENT_MODEL_LOCATION)
        print(f"Exporting to {actual_location}")
        self.exporter.write(actual_location)
        print("Done")
