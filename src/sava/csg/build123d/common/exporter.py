import shutil
import tempfile
import warnings
from copy import copy, deepcopy
from pathlib import Path
from collections.abc import Iterable

from build123d import Shape, Color, Mesher, Plane, Wire, Compound, Edge, BoundBox, Face

from sava.common.logging import logger
from sava.csg.build123d.common.geometry import solidify_wire, solidify_edges, solidify_faces
from sava.csg.build123d.common.smartplane import SmartPlane
from sava.csg.build123d.common.smartsolid import get_solid

CURRENT_MODEL_LOCATION_3MF = "models/current_model.3mf"
CURRENT_MODEL_LOCATION_STL = "models/current_model/"
BASIC_COLORS = ["yellow", "blue", "green", "orange", "purple", "cyan", "magenta", "red", "brown", "pink", "lime", "navy", "teal", "maroon", "olive", "indigo", "white"]

# Module-level storage
_shapes: dict[str, list] = {}
_label_colors: dict[str, str] = {}
_index: int = 1
# Raw triangle meshes loaded from external STL files. These bypass the normal
# Mesher.add_shape pipeline (which would re-tessellate and often fail lib3MF's
# IsValid check on imported geometry) — the triangles go straight into the
# 3MF/STL output as-is. Keyed by label, list of (verts, faces) tuples.
_raw_meshes: dict[str, list[tuple[list, list]]] = {}
# Labels for which the caller opted into emergency export: on add_shape
# failure, fall back to writing raw triangles instead of raising. Set by
# `export(..., emergency=True)`.
_emergency_labels: set[str] = set()
# Labels where the emergency fallback actually fired (output is NOT slicer-safe).
# Drives the warning banner at the end of save_3mf / save_stl.
_emergency_used: set[str] = set()


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


def _prepare_shape(shape, label: str, edge_max_length: float = None, prepare_for_stl: bool = False) -> Iterable[Shape]:
    """Convert shape to exportable shape(s) and assign color based on label.

    Args:
        prepare_for_stl: When True, skip color assignment (STL doesn't support colors, and the limited color set
            could be depleted by many STL labels) and apply bed_orientation to SmartSolid shapes.
    """
    from build123d import Box, Location
    result = []
    if isinstance(shape, Plane):
        extracted = SmartPlane(shape).solid
    elif isinstance(shape, Wire):
        extracted = solidify_wire(shape).solid
    elif isinstance(shape, Edge):
        extracted = solidify_edges(shape, max_length=edge_max_length).solid
    elif isinstance(shape, Face):
        extracted = solidify_faces(shape).solid
    elif isinstance(shape, BoundBox):
        # Convert BoundBox to a visible box solid
        box = Box(shape.size.X, shape.size.Y, shape.size.Z)
        box.locate(Location(shape.center()))
        extracted = box
    else:
        extracted = get_solid(shape, apply_bed_orientation=prepare_for_stl)

    if isinstance(extracted, Iterable):
        for item in extracted:
            result += _prepare_shape(item, label, edge_max_length, prepare_for_stl)
    else:
        shape_copy = copy(extracted)
        if not prepare_for_stl:
            shape_copy.color = Color(_get_color_for_label(label))
        shape_copy.label = label
        result.append(shape_copy.clean())

    return result


def clear() -> None:
    """Clear all stored shapes and color assignments. Useful for testing."""
    global _index
    _shapes.clear()
    _raw_meshes.clear()
    _emergency_labels.clear()
    _emergency_used.clear()
    _label_colors.clear()
    _index = 1


def _try_add_shape(mesher: Mesher, prepared: Shape, label: str, **kwargs) -> None:
    """Add `prepared` to `mesher`. On lib3MF validation failure, fall back to
    raw triangles iff `label` is emergency-flagged; otherwise re-raise.

    The fallback is opt-in (via `export(..., emergency=True)`) and prints a
    loud per-shape warning; a final banner is emitted by save_3mf / save_stl
    if any fallback fired.
    """
    try:
        mesher.add_shape(prepared, **kwargs)
    except RuntimeError as e:
        if label not in _emergency_labels:
            raise
        print(f"!!! EMERGENCY: '{label}' failed lib3MF validation: {e}")
        print(f"!!! Writing raw triangles -- geometry is NOT slicer-safe.")
        verts, tris = Mesher._mesh_shape(deepcopy(prepared), 0.001, 0.1)
        _add_raw_mesh_to_mesher(mesher, verts, tris, label)
        _emergency_used.add(label)


def _print_emergency_banner() -> None:
    """Print a loud reminder that any emergency-flagged fallbacks ran."""
    if not _emergency_used:
        return
    bar = "=" * 70
    print()
    print(bar)
    print("WARNING: emergency export bypassed lib3MF validation for:")
    for lbl in sorted(_emergency_used):
        print(f"  - {lbl}")
    print()
    print("Output is NOT usable as-is. The geometry contains defects")
    print("(typically non-manifold edges from dense CSG) that will fail")
    print("in slicers (PrusaSlicer/Bambu/Cura). Fix the modeling code that")
    print("produced these shapes before printing.")
    print(bar)
    print()


def _add_raw_mesh_to_mesher(mesher: Mesher, verts: list, faces: list, label: str) -> None:
    """Append a raw triangle mesh to `mesher` under `label`'s colour."""
    v3, t3 = Mesher._create_3mf_mesh(verts, faces)
    mesh = mesher.model.AddMeshObject()
    mesh.SetGeometry(v3, t3)
    mesh.SetName(label)
    color = Color(_get_color_for_label(label))
    grp = mesher.model.AddBaseMaterialGroup()
    rgb = mesher.wrapper.FloatRGBAToColor(*tuple(color))
    mat_id = grp.AddMaterial(Name=str(color), DisplayColor=rgb)
    mesh.SetObjectLevelProperty(grp.GetResourceID(), mat_id)
    mesher.meshes.append(mesh)
    mesher.model.AddBuildItem(mesh, mesher.wrapper.GetIdentityTransform())


def export_stl_file(stl_path: str, label: str = 'source',
                    shift: tuple[float, float, float] = (0.0, 0.0, 0.0)) -> None:
    """Register an existing STL file's triangle mesh for inclusion in the next
    `save_3mf()` / `save_stl()` call.

    The mesh is added as-is; re-tessellating an imported STL through the
    standard `Mesher.add_shape` pipeline usually fails lib3MF's IsValid
    check, so this side-channel copies the triangles directly.

    Args:
        stl_path: path to the source STL.
        label: label used for grouping and colour assignment (same as
            `export()`).
        shift: per-vertex translation, useful for placing the mesh beside
            a reconstructed model for visual comparison.
    """
    from sava.csg.build123d.reconstruct.mesh_io import read_mesh

    verts, faces = read_mesh(_resolve_path(stl_path))
    if any(s != 0 for s in shift):
        sx, sy, sz = shift
        verts = [(v[0] + sx, v[1] + sy, v[2] + sz) for v in verts]
    _raw_meshes.setdefault(label, []).append((verts, faces))


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


def export(*shapes, label: str = None, emergency: bool = False):
    """Add shape(s) to export storage.

    If label is provided, all shapes use that label.
    Otherwise, each shape uses its own .label attribute or gets an auto-generated label.

    `emergency=True` opts the label into a raw-triangle fallback if
    lib3MF rejects the shape's tessellation during save (typical for
    densely-CSG'd solids with non-manifold edges). The bypass prints a
    loud warning per shape and a final banner. Output produced this way
    is NOT slicer-safe and is intended for diagnostic visualization only.
    """
    global _index

    for shape in shapes:
        shape_label = label or getattr(shape, 'label', None)
        if shape_label is None:
            shape_label = f"shape_{_index}"
            _index += 1

        if shape_label not in _shapes:
            _shapes[shape_label] = []
        if emergency:
            _emergency_labels.add(shape_label)
        _shapes[shape_label].append(_copy_shape_for_storage(shape))


def show_red(*shapes):
    """Export shape(s) with 'red' label."""
    export(*shapes, label="red")


def show_blue(*shapes):
    """Export shape(s) with 'blue' label."""
    export(*shapes, label="blue")


def show_green(*shapes):
    """Export shape(s) with 'green' label."""
    export(*shapes, label="green")


def get_project_root_folder() -> Path:
    current = Path(__file__).resolve()
    for parent in current.parents:
        if (parent / '.git').exists():
            return parent
    raise FileNotFoundError("Could not find project root")


def get_path(*path_from_project_root) -> str:
    # If first path is absolute, use it directly - mostly for temporary files in tests
    first = Path(path_from_project_root[0])
    if first.is_absolute():
        return str(first.joinpath(*path_from_project_root[1:]))

    # Otherwise join to project root
    return str(get_project_root_folder().joinpath(*path_from_project_root))


def _resolve_path(location: str) -> str:
    """Resolve path to absolute path. If relative, treat as relative to project root."""
    p = Path(location)
    if p.is_absolute():
        return str(Path(p))
    return str(Path(get_path(location)))


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

    _print_emergency_banner()
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
                    _try_add_shape(mesher, prepared, label, angular_deflection=0.05)

                    # Print any warnings with label information
                    for w in caught_warnings:
                        print(f"WARNING: Shape with label '{label}': {w.message}")

    for label, meshes in _raw_meshes.items():
        for verts, faces in meshes:
            _add_raw_mesh_to_mesher(mesher, verts, faces, label)

    _report_labels(edge_max_length)

    # Write to the temporary file first, then copy to the actual location
    # Writing it to the actual location exactly may be slow enough for F3D viewer to close
    with tempfile.NamedTemporaryFile(mode='wb', delete=False, suffix='.3mf') as temp_file:
        temp_path = temp_file.name

    try:
        mesher.write(temp_path)
        shutil.copy2(temp_path, location)
    finally:
        temp = Path(temp_path)
        if temp.exists():
            temp.unlink()


def create_file_path(location: str, filename: str = None) -> str:
    """Resolve path and create parent directory if needed.

    Args:
        location: Directory or file path
        filename: Optional filename to join with location
    """
    if filename:
        path = _resolve_path(str(Path(location) / filename))
    else:
        path = _resolve_path(location)
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    return path

def export_stl(directory: str, *shapes) -> None:
    clear()
    export(*shapes)
    save_stl(directory)

def export_3mf(directory: str, *shapes) -> None:
    export(*shapes)
    save_3mf(directory, True)

def save_stl(directory: str = None) -> None:
    """Save each label group to separate STL files."""
    base_dir = directory or CURRENT_MODEL_LOCATION_STL
    actual_directory = _resolve_path(base_dir)
    print(f"\nExporting STL files to {actual_directory}\n")

    edge_max_length = _get_edge_max_length()

    for label, shapes in _shapes.items():
        mesher = Mesher()
        for shape in shapes:
            for prepared in _prepare_shape(shape, label, edge_max_length, prepare_for_stl=True):
                _try_add_shape(mesher, prepared, label)

        file_path = create_file_path(actual_directory, f"{label}.stl")
        mesher.write(str(file_path))
        print(f"  - {Path(file_path).name}")

    for label, meshes in _raw_meshes.items():
        mesher = Mesher()
        for verts, faces in meshes:
            _add_raw_mesh_to_mesher(mesher, verts, faces, label)
        file_path = create_file_path(actual_directory, f"{label}.stl")
        mesher.write(str(file_path))
        print(f"  - {Path(file_path).name}")

    _print_emergency_banner()
    logger.info("Done")
