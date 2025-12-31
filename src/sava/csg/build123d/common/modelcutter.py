from dataclasses import dataclass

from build123d import Wire, sweep, Sketch, Axis, Plane

from sava.csg.build123d.common.geometry import solidify_wire
from sava.csg.build123d.common.pencil import Pencil
from sava.csg.build123d.common.smartsolid import SmartSolid


@dataclass
class CutSpec:
    """Specification for a single cut operation.

    Attributes:
        wire: The wire path along which to cut
        plane: The plane orientation for the cutting triangle
        thickness: Thickness of material to remove (default 0 for thin cut)
    """
    wire: Wire
    plane: Plane
    thickness: float = 0.0


def _calculate_triangle_size(model: SmartSolid, wires: list[Wire]) -> float:
    """Calculate triangle leg length from model and wires bounding box.

    Creates an extended model that includes both the original model and all wires
    (converted to 3D by sweeping a small circle along them), then calculates
    the triangle size from the bounding box diagonal.

    Args:
        model: The original model
        wires: List of wires to include

    Returns:
        Triangle leg length (2x the bounding box diagonal)
    """
    # Create extended model that includes both the model and wires
    extended = model.copy()
    for wire in wires:
        extended.fuse(SmartSolid(solidify_wire(wire)))

    # Calculate triangle size from bounding box
    bbox = extended.bound_box
    diagonal = (bbox.size.X**2 + bbox.size.Y**2 + bbox.size.Z**2)**0.5
    # Use 2x diagonal to ensure complete cut from any angle
    return diagonal * 2.0


def _create_cutting_triangle_at_wire(plane: Plane, wire: Wire, leg_length: float, x_offset: float = 0.0) -> Sketch:
    """Create triangle positioned at wire start.

    Args:
        plane: The plane orientation
        wire: The wire path
        leg_length: Triangle leg length
        x_offset: Offset along the plane's X axis from the wire position

    Returns:
        Face representing the cutting triangle
    """
    wire_start = wire @ 0.0
    # Shift the origin along the plane's X axis
    shifted_origin = wire_start + plane.x_dir * x_offset
    positioned_plane = Plane(
        origin=shifted_origin,
        x_dir=plane.x_dir,
        z_dir=plane.z_dir
    )
    pencil = Pencil(plane=positioned_plane)
    pencil.draw(leg_length, 45)
    return pencil.create_mirrored_face(Axis.X)


def cut_with_wires(model: SmartSolid, *cuts: CutSpec) -> list[SmartSolid]:
    """Cut a model into pieces along one or more wires.

    Each cut processes all existing pieces progressively, creating a full subdivision
    of the model. With thickness > 0, material is removed along the cut path.

    Args:
        model: The SmartSolid to cut
        *cuts: CutSpec objects defining wire path, plane orientation, and thickness.
               Example: cut_with_wires(model, CutSpec(wire1, plane1), CutSpec(wire2, plane2, thickness=2))

    Returns:
        List of SmartSolid pieces resulting from the cuts
    """

    # Extract wires and calculate triangle size once
    wire_list = [cut.wire for cut in cuts]
    triangle_size = _calculate_triangle_size(model, wire_list)

    pieces = [model]
    for cut_spec in cuts:
        # Create triangles offset along the plane's X axis
        triangle_left = _create_cutting_triangle_at_wire(cut_spec.plane, cut_spec.wire, triangle_size, -cut_spec.thickness / 2)
        cutter_left = SmartSolid(sweep(triangle_left, cut_spec.wire))

        triangle_right = _create_cutting_triangle_at_wire(cut_spec.plane, cut_spec.wire, triangle_size, cut_spec.thickness / 2)
        cutter_right = SmartSolid(sweep(triangle_right, cut_spec.wire))

        new_pieces = []
        for piece in pieces:
            piece_left = piece.intersected(cutter_left, label=None if piece.label is None else f"{piece.label}_1")
            piece_right = piece.cutted(cutter_right, label=None if piece.label is None else f"{piece.label}_2")

            for sub_piece in [piece_left, piece_right]:
                if sub_piece.solid is not None and sub_piece.solid:
                    new_pieces.append(sub_piece)

        pieces = new_pieces

    return pieces
