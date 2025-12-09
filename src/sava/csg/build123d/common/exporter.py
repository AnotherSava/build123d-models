from copy import copy
from pathlib import Path
from typing import Iterable

from build123d import Shape, Color, Mesher, Plane

from sava.csg.build123d.common.smartplane import SmartPlane
from sava.csg.build123d.common.smartsolid import get_solid

CURRENT_MODEL_LOCATION = "models/current_model.3mf"
BASIC_COLORS = ["yellow", "blue", "green", "orange", "purple", "cyan", "magenta", "red"]

# Module-level storage
_shapes: dict[str, list] = {}
_label_colors: dict[str, str] = {}


def _is_valid_color(name: str) -> bool:
    """Check if name is a valid color by trying to create a Color object."""
    try:
        Color(name)
        return True
    except:
        return False


def _get_color_for_label(label: str) -> str:
    """Return color for label. Use label if it's a valid color name, otherwise assign from BASIC_COLORS."""
    if _is_valid_color(label):
        return label

    if label in _label_colors:
        return _label_colors[label]

    used_colors = set(_label_colors.values())
    for color in BASIC_COLORS:
        if color not in used_colors:
            _label_colors[label] = color
            return color

    raise RuntimeError(f"All {len(BASIC_COLORS)} colors exhausted. Cannot assign color to label '{label}'.")


def _prepare_shape(shape, label: str) -> Iterable[Shape]:
    """Convert shape to exportable shape(s) and assign color based on label."""
    result = []
    if isinstance(shape, Plane):
        extracted = SmartPlane(shape).solid
    else:
        extracted = get_solid(shape)

    if isinstance(extracted, Iterable):
        for item in extracted:
            result += _prepare_shape(item, label)
    else:
        shape_copy = copy(extracted)
        shape_copy.color = Color(_get_color_for_label(label))
        shape_copy.label = label
        result.append(shape_copy.clean())

    return result


def clear() -> None:
    """Clear all stored shapes and color assignments. Useful for testing."""
    _shapes.clear()
    _label_colors.clear()


def export(shape, label: str = "model") -> None:
    """Add shape to export storage under the given label."""
    if label not in _shapes:
        _shapes[label] = []
    _shapes[label].append(shape)


def show_red(shape) -> None:
    """Export shape with 'red' label."""
    export(shape, "red")


def show_blue(shape) -> None:
    """Export shape with 'blue' label."""
    export(shape, "blue")


def show_green(shape) -> None:
    """Export shape with 'green' label."""
    export(shape, "green")


def get_project_root_folder() -> Path:
    current = Path(__file__).resolve()
    for parent in current.parents:
        if (parent / '.git').exists():
            return parent
    raise FileNotFoundError("Could not find project root")


def get_path(path_from_project_root: str) -> str:
    return str(get_project_root_folder() / path_from_project_root)


def _report_labels() -> None:
    """Print summary of shapes by label."""
    for label, shapes in _shapes.items():
        count = sum(len(_prepare_shape(s, label)) for s in shapes)
        print(f"{label + ':':<15} {count} shape(s)")


def save_3mf(location: str = None) -> None:
    """Save all shapes to a single 3MF file."""
    actual_location = location or get_path(CURRENT_MODEL_LOCATION)
    print(f"\nExporting to {actual_location}\n")

    mesher = Mesher()
    for label, shapes in _shapes.items():
        for shape in shapes:
            for prepared in _prepare_shape(shape, label):
                mesher.add_shape(prepared)

    _report_labels()
    mesher.write(actual_location)
    print(f"\nDone")


def save_stl(directory: str = None) -> None:
    """Save each label group to separate STL files."""
    actual_directory = Path(directory) if directory else get_project_root_folder() / "models"
    actual_directory.mkdir(parents=True, exist_ok=True)

    print(f"\nExporting STL files to {actual_directory}\n")

    for label, shapes in _shapes.items():
        mesher = Mesher()
        for shape in shapes:
            for prepared in _prepare_shape(shape, label):
                mesher.add_shape(prepared)

        file_path = actual_directory / f"{label}.stl"
        mesher.write(str(file_path))
        print(f"  {file_path.name}")

    _report_labels()
    print(f"\nDone")
