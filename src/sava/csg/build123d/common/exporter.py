import os
import shutil
import tempfile
import warnings
from copy import copy
from pathlib import Path
from typing import Iterable

from build123d import Shape, Color, Mesher, Plane, Wire, Compound, Edge, BoundBox

from sava.common.logging import logger
from sava.csg.build123d.common.geometry import solidify_wire, solidify_edges
from sava.csg.build123d.common.smartplane import SmartPlane
from sava.csg.build123d.common.smartsolid import get_solid

CURRENT_MODEL_LOCATION_3MF = "models/current_model.3mf"
CURRENT_MODEL_LOCATION_STL = "models/current_model/"
BASIC_COLORS = ["yellow", "blue", "green", "orange", "purple", "cyan", "magenta", "red", "brown", "pink", "lime", "navy", "teal", "maroon", "olive", "indigo", "white"]

# Module-level storage
_shapes: dict[str, list] = {}
_label_colors: dict[str, str] = {}
_index: int = 1


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


def _prepare_shape(shape, label: str, edge_max_length: float = None) -> Iterable[Shape]:
    """Convert shape to exportable shape(s) and assign color based on label."""
    from build123d import Box, Location
    result = []
    if isinstance(shape, Plane):
        extracted = SmartPlane(shape).solid
    elif isinstance(shape, Wire):
        extracted = solidify_wire(shape).solid
    elif isinstance(shape, Edge):
        extracted = solidify_edges(shape, max_length=edge_max_length).solid
    elif isinstance(shape, BoundBox):
        # Convert BoundBox to a visible box solid
        box = Box(shape.size.X, shape.size.Y, shape.size.Z)
        box.locate(Location(shape.center()))
        extracted = box
    else:
        extracted = get_solid(shape)

    if isinstance(extracted, Iterable):
        for item in extracted:
            result += _prepare_shape(item, label, edge_max_length)
    else:
        shape_copy = copy(extracted)
        shape_copy.color = Color(_get_color_for_label(label))
        shape_copy.label = label
        result.append(shape_copy.clean())

    return result


def clear() -> None:
    """Clear all stored shapes and color assignments. Useful for testing."""
    global _index
    _shapes.clear()
    _label_colors.clear()
    _index = 1


def _copy_shape_for_storage(shape):
    """Create a copy of a shape for storage to capture current state."""
    from sava.csg.build123d.common.smartsolid import SmartSolid

    if isinstance(shape, SmartSolid):
        return shape.copy()
    elif isinstance(shape, Iterable) and not isinstance(shape, Shape):
        # Consume iterator and copy each element
        return [_copy_shape_for_storage(item) for item in shape]
    else:
        return copy(shape)


def export(shape, label: str = None):
    """Add shape to export storage under the given label."""
    global _index
    label = label or getattr(shape, 'label', None)
    if label is None:
        label = f"shape_{_index}"
        _index += 1

    if label not in _shapes:
        _shapes[label] = []
    _shapes[label].append(_copy_shape_for_storage(shape))

    return shape


def show_red(shape):
    """Export shape with 'red' label."""
    return export(shape, "red")


def show_blue(shape):
    """Export shape with 'blue' label."""
    return export(shape, "blue")


def show_green(shape):
    """Export shape with 'green' label."""
    return export(shape, "green")


def get_project_root_folder() -> Path:
    current = Path(__file__).resolve()
    for parent in current.parents:
        if (parent / '.git').exists():
            return parent
    raise FileNotFoundError("Could not find project root")


def get_path(*path_from_project_root) -> str:
    # If first path is absolute, use it directly - mostly for temporary files in tests
    if os.path.isabs(path_from_project_root[0]):
        return os.path.join(*path_from_project_root)

    # Otherwise join to project root
    return os.path.join(str(get_project_root_folder()), *path_from_project_root)


def _resolve_path(location: str) -> str:
    """Resolve path to absolute path. If relative, treat as relative to project root."""
    if os.path.isabs(location):
        return os.path.normpath(location)
    return os.path.normpath(get_path(location))


def _report_labels(edge_max_length: float = None) -> None:
    """Print summary of shapes by label."""
    for label, shapes in _shapes.items():
        count = sum(len(_prepare_shape(s, label, edge_max_length)) for s in shapes)
        count_suffix = f": {count} shapes" if count > 1 else ""
        print(f"  - {label}{count_suffix}")


def _get_shapes_bounding_box() -> BoundBox | None:
    """Get bounding box of all exported shapes."""
    bboxes = []
    for label, shapes in _shapes.items():
        for shape in shapes:
            if isinstance(shape, BoundBox):
                bboxes.append(shape)
            elif isinstance(shape, (Plane, Wire, Edge)):
                bboxes.append(shape.bounding_box())
            else:
                solid = get_solid(shape)
                if isinstance(solid, Iterable):
                    for s in solid:
                        bboxes.append(s.bounding_box())
                else:
                    bboxes.append(solid.bounding_box())

    if not bboxes:
        return None

    # Combine all bounding boxes
    result = bboxes[0]
    for bbox in bboxes[1:]:
        result = result.add(bbox)
    return result


def _get_edge_max_length() -> float | None:
    """Get max dimension for edge visualization."""
    bbox = _get_shapes_bounding_box()
    if bbox:
        return max(bbox.size.X, bbox.size.Y, bbox.size.Z)
    return None


def print_dimensions() -> None:
    """Print the combined bounding box dimensions of all exported objects."""
    bbox = _get_shapes_bounding_box()
    if bbox:
        logger.info(f"Combined dimensions: {bbox.size.X:.2f} x {bbox.size.Y:.2f} x {bbox.size.Z:.2f} mm")


def save_3mf(location: str = None, current: bool = False) -> None:
    """Save all shapes to a single 3MF file."""
    actual_location = create_file_path(location or CURRENT_MODEL_LOCATION_3MF)
    print(f"\nExporting 3mf file to: {actual_location}\n")
    _save_3mf(actual_location)

    if not location or current:
        print_dimensions()

    if location and current:
        current_model_location = create_file_path(CURRENT_MODEL_LOCATION_3MF)
        print(f"\nCopying 3MF to use as a current model: {current_model_location}\n")
        shutil.copy2(actual_location, current_model_location)

    logger.info("Done")

def _save_3mf(location: str) -> None:
    """Save all shapes to a single 3MF file."""
    edge_max_length = _get_edge_max_length()

    mesher = Mesher()
    for label, shapes in _shapes.items():
        for shape in shapes:
            for prepared in _prepare_shape(shape, label, edge_max_length):
                with warnings.catch_warnings(record=True) as caught_warnings:
                    warnings.simplefilter("always")
                    mesher.add_shape(prepared)

                    # Print any warnings with label information
                    for w in caught_warnings:
                        print(f"WARNING: Shape with label '{label}': {w.message}")

    _report_labels(edge_max_length)

    # Write to the temporary file first, then copy to the actual location
    # Writing it to the actual location exactly may be slow enough for F3D viewer to close
    with tempfile.NamedTemporaryFile(mode='wb', delete=False, suffix='.3mf') as temp_file:
        temp_path = temp_file.name

    try:
        mesher.write(temp_path)
        shutil.copy2(temp_path, location)
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)


def create_file_path(location: str, filename: str = None) -> str:
    """Resolve path and create parent directory if needed.

    Args:
        location: Directory or file path
        filename: Optional filename to join with location
    """
    if filename:
        path = _resolve_path(os.path.join(location, filename))
    else:
        path = _resolve_path(location)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    return path

def save_stl(directory: str = None) -> None:
    """Save each label group to separate STL files."""
    base_dir = directory or CURRENT_MODEL_LOCATION_STL
    actual_directory = _resolve_path(base_dir)
    print(f"\nExporting STL files to {actual_directory}\n")

    edge_max_length = _get_edge_max_length()

    for label, shapes in _shapes.items():
        mesher = Mesher()
        for shape in shapes:
            for prepared in _prepare_shape(shape, label, edge_max_length):
                mesher.add_shape(prepared)

        file_path = create_file_path(actual_directory, f"{label}.stl")
        mesher.write(str(file_path))
        print(f"  - {os.path.basename(file_path)}")

    logger.info("Done")
