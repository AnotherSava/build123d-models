from build123d import Axis, Edge, Plane, Vector

from sava.common.logging import logger
from sava.csg.build123d.common.boxgeometry import TopRect, build_box_solid, is_tapered, offset_box_geometry, resolve_top_rect
from sava.csg.build123d.common.geometry import Alignment, Direction, format_float
from sava.csg.build123d.common.smartsolid import SmartSolid

FILLET_ENABLER_COEFFICIENT = 1.01  # coefficient between side length and fillet radius (operation fails when 1.0)


class SmartBox(SmartSolid):
    """
    A box primitive with optional, per-side tapering support.

    The base is always a (length × width) rectangle centred on the origin. The top is an
    axis-aligned rectangle at ``height`` whose four edges can each be displaced
    independently, so any frustum/wedge with planar walls is expressible.

    Each top edge is resolved from whichever tapering parameter is supplied: a per-side
    wall ``angle_*`` takes precedence, otherwise the symmetric ``tapered_length`` /
    ``tapered_width`` applies to both edges of its pair, otherwise the wall is vertical.
    The geometry math lives in ``boxgeometry``; this class is the user-facing API.

    Examples:
        # Simple box (non-tapered)
        box = SmartBox(100, 80, 50)

        # Symmetric taper (both length walls and both width walls lean in equally)
        tapered = SmartBox(100, 80, 50, tapered_length=90, tapered_width=70)

        # Asymmetric: east wall vertical, west wall at 45°, width walls untouched
        wedge = SmartBox(100, 80, 50, angle_east=90, angle_west=45)

        # Mix: symmetric width taper, but override the east wall to a specific angle
        mixed = SmartBox(100, 80, 50, tapered_width=60, angle_east=70)
    """

    def __init__(self, length: float, width: float, height: float, tapered_length: float = None, tapered_width: float = None, angle_east: float = None, angle_west: float = None, angle_north: float = None, angle_south: float = None, plane: Plane = Plane.XY, label: str = None):
        """
        Creates a box, optionally tapered per side.

        Args:
            length: Length (X dimension) at the base
            width: Width (Y dimension) at the base
            height: Height (Z dimension)
            tapered_length: Symmetric top length (applies to both the east and west walls)
            tapered_width: Symmetric top width (applies to both the north and south walls)
            angle_east: Wall angle of the east (+X) wall from horizontal (90° = vertical, <90° = inward)
            angle_west: Wall angle of the west (-X) wall
            angle_north: Wall angle of the north (+Y) wall
            angle_south: Wall angle of the south (-Y) wall
            plane: Plane to create the box in (default: XY)
            label: Optional label for export

        A per-side ``angle_*`` overrides ``tapered_length`` / ``tapered_width`` for that
        wall only. Passing ``tapered_length`` together with both ``angle_east`` and
        ``angle_west`` (which would fully override it) is rejected; likewise for width.
        """
        top = resolve_top_rect(length, width, height, tapered_length, tapered_width, angle_east, angle_west, angle_north, angle_south)
        self._build(length, width, height, top, plane, label)

    @classmethod
    def with_delta(cls, length: float, width: float, height: float, delta: float, plane: Plane = Plane.XY, label: str = None) -> 'SmartBox':
        return cls(length, width, height, length + 2 * delta, width + 2 * delta, plane=plane, label=label)

    def _build(self, length: float, width: float, height: float, top: TopRect, plane: Plane = Plane.XY, label: str = None) -> None:
        """Store dimensions and the top rectangle, build the solid, and run SmartSolid setup."""
        self.length = length
        self.width = width
        self.height = height
        self._top = top

        if label:
            dimensions = f"{format_float(length)} x {format_float(width)}"
            tapered_dimensions = ' -> ' + (format_float(top.length) + ' x ' + format_float(top.width)) if self.tapered else ''
            logger.info(f"Smart box '{label}': {dimensions}{tapered_dimensions}, height: {format_float(height)}")

        SmartSolid.__init__(self, build_box_solid(length, width, height, top, plane), label=label)

    @classmethod
    def _from_top(cls, length: float, width: float, height: float, top: TopRect, plane: Plane = Plane.XY, label: str = None) -> 'SmartBox':
        """Build a SmartBox from an explicit top rectangle (for asymmetric results, e.g. create_offset)."""
        box = cls.__new__(cls)
        box._build(length, width, height, top, plane, label)
        return box

    @property
    def tapered_length(self) -> float:
        """Top length (X span of the top rectangle)."""
        return self._top.length

    @property
    def tapered_width(self) -> float:
        """Top width (Y span of the top rectangle)."""
        return self._top.width

    @property
    def tapered(self) -> bool:
        return is_tapered(self.length, self.width, self._top)

    @property
    def slope_length(self) -> float:
        """Rate of total length change per unit height: (tapered_length - length) / height"""
        return (self.tapered_length - self.length) / self.height

    @property
    def slope_width(self) -> float:
        """Rate of total width change per unit height: (tapered_width - width) / height"""
        return (self.tapered_width - self.width) / self.height

    def length_at(self, height_fraction: float) -> float:
        """Returns length at given height (0.0 = base, 1.0 = top)"""
        return self.length + (self.tapered_length - self.length) * height_fraction

    def width_at(self, height_fraction: float) -> float:
        """Returns width at given height (0.0 = base, 1.0 = top)"""
        return self.width + (self.tapered_width - self.width) * height_fraction

    def center(self, height_fraction: float = 1) -> Vector:
        """Returns center point at given height in local coordinates (0.0 = base, 1.0 = top).

        The base is centred at the origin, so an asymmetric top shifts the centre in X/Y
        as the height fraction increases."""
        return Vector(self._top.center_x * height_fraction, self._top.center_y * height_fraction, self.height * height_fraction)

    def taper(self, tapered_length: float = None, tapered_width: float = None, angle_east: float = None, angle_west: float = None, angle_north: float = None, angle_south: float = None, label: str = None) -> 'SmartBox':
        """Return a new SmartBox with this box's base footprint, height, and placement, but
        re-tapered per the given parameters.

        Takes the same tapering inputs as the constructor; ``length``, ``width``, ``height``
        and the box's orientation come from this box, so they're not repeated. The taper is
        applied to the base (length × width) footprint — walls left unspecified are vertical,
        so any existing taper is replaced rather than compounded. The result is placed where
        this box is (its tracked move/rotate transforms are re-applied).

        Args:
            tapered_length: Symmetric top length (applies to both the east and west walls)
            tapered_width: Symmetric top width (applies to both the north and south walls)
            angle_east: Wall angle of the east (+X) wall from horizontal (90° = vertical, <90° = inward)
            angle_west: Wall angle of the west (-X) wall
            angle_north: Wall angle of the north (+Y) wall
            angle_south: Wall angle of the south (-Y) wall
            label: Optional label for the new box (defaults to this box's label)
        """
        top = resolve_top_rect(self.length, self.width, self.height, tapered_length, tapered_width, angle_east, angle_west, angle_north, angle_south)
        result = SmartBox._from_top(self.length, self.width, self.height, top, label=label or self.label)
        # Copy this box's full placement transform. colocate() clones solid.location directly,
        # so it also carries plane-constructed orientation that self._orientation doesn't track
        # (e.g. a box from with_top()); both share the same base-centred canonical geometry.
        result.colocate(self)
        result.bed_orientation = self.bed_orientation
        return result

    def with_top(self, direction: Direction, label: str = None) -> 'SmartBox':
        """Return a new SmartBox occupying the exact same space as this one, but re-framed so
        the face on the given Direction is its top (local +Z / height axis). The geometry does
        not move — that face still points the same way in the world; we only rename which face
        the box calls "top", reassigning length/width/height and the construction plane to match.

        Non-tapered, axis-aligned boxes only — a tapered box's taper is tied to its Z axis and
        can't be re-pointed at another face.

        Note: operations keyed to world +Z (`create_offset(up/down)`, `add_cutout`, `z_max`,
        `bed_orientation`) still act on the world top — the renamed top is what plane-aware
        methods and the box's own length/width/height see.

        Example: a 10×20×30 (L×W×H) box `.with_top(Direction.N)` stays exactly in place but now
        reports height 20 (the Y extent) with its +Y face as the top.
        """
        assert not self.tapered, "with_top only works on non-tapered boxes"
        bb = self.bound_box
        aabb_volume = bb.size.X * bb.size.Y * bb.size.Z
        assert abs(aabb_volume - self.solid.volume) < 1e-6 * aabb_volume, "with_top requires an axis-aligned box"

        # local +Z (the new top/height axis) points along `direction`; the box keeps its world
        # occupancy, so build it in a plane rotated to that frame, anchored at the opposite face.
        n = direction.value
        x_dir = Vector(1, 0, 0) if abs(n.X) < 0.5 else Vector(0, 1, 0)   # a world axis in the new base plane
        y_dir = n.cross(x_dir)
        project = lambda axis: abs(bb.size.X * axis.X) + abs(bb.size.Y * axis.Y) + abs(bb.size.Z * axis.Z)
        height = project(n)
        # Build in a plane anchored at the world origin (keeps solid.location honest), then
        # translate the base-face centre to where it belongs — the opposite face from `direction`.
        result = SmartBox(project(x_dir), project(y_dir), height, plane=Plane(origin=(0, 0, 0), x_dir=x_dir, z_dir=n), label=label or self.label)
        result.move_vector(Vector(bb.center()) - n * (height / 2))
        return result

    def create_offset(self, offset: float, north: float = None, south: float = None, east: float = None, west: float = None, up: float = None, down: float = None, label: str = None) -> 'SmartBox':
        """
        Creates an offset box by adjusting dimensions with per-direction control.

        Args:
            offset: Base offset for all 6 directions (positive = outward, negative = inward)
            north: Override for north (+Y) wall, None uses base offset
            south: Override for south (-Y) wall, None uses base offset
            east: Override for east (+X) wall, None uses base offset
            west: Override for west (-X) wall, None uses base offset
            up: Override for up (+Z), None uses base offset
            down: Override for down (-Z), None uses base offset
            label: Optional label for the new box

        Returns:
            A new SmartBox with adjusted dimensions
        """
        n = offset if north is None else north
        s = offset if south is None else south
        e = offset if east is None else east
        w = offset if west is None else west
        u = offset if up is None else up
        d = offset if down is None else down

        geometry = offset_box_geometry(self.length, self.width, self.height, self._top, n, s, e, w, u, d)
        offset_box = SmartBox._from_top(geometry.length, geometry.width, geometry.height, geometry.top, label=label)
        offset_box.move(self.x_mid + geometry.center_x, self.y_mid + geometry.center_y, self.z_min - d)

        return offset_box

    def create_shell(self, offset: float = 0, north: float = None, south: float = None, east: float = None, west: float = None, up: float = None, down: float = None) -> 'SmartBox':
        """
        Creates a shell by cutting between self and an offset box.

        Args:
            offset: Base wall thickness for all 6 directions
            north: Override for north (+Y) wall, None uses base offset
            south: Override for south (-Y) wall, None uses base offset
            east: Override for east (+X) wall, None uses base offset
            west: Override for west (-X) wall, None uses base offset
            up: Override for up (+Z), None uses base offset
            down: Override for down (-Z), None uses base offset

        Returns:
            A new SmartBox representing the shell

        Behavior:
            - Negative offsets: creates inner box, cuts from copy of self (hollow interior)
            - Positive offsets: creates outer box, cuts copy of self from it (shell around original)
        """
        signs = {o > 0 for o in [offset, north, south, east, west, up, down] if o}
        assert len(signs) == 1, "All non-zero offsets must have the same sign, and at least one must be non-zero"

        offset_box = self.create_offset(offset, north, south, east, west, up, down)

        if False in signs:
            return self.cutted(offset_box)
        else:
            return offset_box.cut(self)

    def copy(self, label: str = None) -> 'SmartBox':
        """Deep copy returning SmartBox"""
        result = SmartBox.__new__(SmartBox)
        self._copy_base_fields(result, label)
        result.length = self.length
        result.width = self.width
        result.height = self.height
        result._top = self._top
        return result

    def add_cutout(self, direction: Direction, length: float, radius_bottom: float = 0, radius_top: float | None = None, width: float | None = None, height: float | None = None, shift: float = 0) -> 'SmartBox':
        assert width is not None or height is not None, "Either width or height must be specified"

        axis = direction.axis
        horizontal = direction in [Direction.E, Direction.W]
        width_actual = width or self.get_size(axis)
        height_actual = (height or self.z_size)

        if horizontal:
            cutout_bottom = SmartBox(width_actual, length, height_actual)
        else:
            cutout_bottom = SmartBox(length, width_actual, height_actual)

        if radius_bottom:
            if height:  # cutout doesn't go all the way to the bottom
                cutout_bottom._fillet(axis, radius_bottom, Axis.Z, cutout_bottom.z_min)
            else:  # cutout goes all the way to the bottom
                cutout_bottom._fillet(Axis.Z, radius_bottom)

        radius_top_actual = radius_bottom if radius_top is None else radius_top
        if radius_top_actual:
            if horizontal:
                cutout_top = SmartBox(width_actual, length, radius_top_actual * FILLET_ENABLER_COEFFICIENT)
            else:
                cutout_top = SmartBox(length, width_actual, radius_top_actual * FILLET_ENABLER_COEFFICIENT)
            cutout_bottom.align_xy(cutout_top).align_z(cutout_top, Alignment.RL)

            if horizontal:
                cutout_cap = SmartBox(width_actual, length + radius_top_actual * 2 * FILLET_ENABLER_COEFFICIENT, radius_top_actual)
            else:
                cutout_cap = SmartBox(length + radius_top_actual * 2 * FILLET_ENABLER_COEFFICIENT, width_actual, radius_top_actual)
            cutout_cap.align_xy(cutout_top).align_z(cutout_top, Alignment.RR)
            cutout_top.fuse(cutout_cap)
            cutout_top.fillet_edges(Edge.is_interior, radius_top_actual)

            cutout_bottom = cutout_top.fuse(cutout_bottom)

        cutout_bottom.align_z(self, Alignment.RL, radius_top_actual or 0).align_axis(self, direction.rotate(90).axis, Alignment.C, shift).align_axis(self, axis, direction.alignment_closer if height else direction.alignment_middle)

        return self.cut(cutout_bottom)
