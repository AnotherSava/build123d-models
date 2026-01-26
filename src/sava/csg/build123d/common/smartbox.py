from copy import copy
from math import radians, tan

from build123d import Axis, Edge, Face, Location, Solid, Vector, Wire, loft

from sava.common.advanced_math import advanced_mod
from sava.common.logging import logger
from sava.csg.build123d.common.geometry import Alignment, Direction, are_numbers_too_close, snap_to, format_float
from sava.csg.build123d.common.smartsolid import SmartSolid

FILLET_ENABLER_COEFFICIENT = 1.01  # coefficient between side length and fillet radius (operation fails when 1.0)


class SmartBox(SmartSolid):
    """
    A box primitive with optional tapering support.

    When tapered_length or tapered_width differ from length/width, creates a tapered box
    (frustum) where the base has dimensions (length, width) and the top has dimensions
    (tapered_length, tapered_width). Non-tapered boxes use an efficient make_box() call,
    while tapered boxes use loft() between base and top rectangles.

    Examples:
        # Simple box (non-tapered)
        box = SmartBox(100, 80, 50)

        # Tapered box (wider at base, narrower at top)
        tapered = SmartBox(100, 80, 50, tapered_length=90, tapered_width=70)

        # Tapered box defined by wall angles
        angled = SmartBox.with_base_angles_and_height(100, 80, 50, 80, 80)
    """

    def __init__(self, length: float, width: float, height: float, tapered_length: float = None, tapered_width: float = None, label: str = None):
        """
        Creates a box, optionally tapered.

        Args:
            length: Length (X dimension) at the base
            width: Width (Y dimension) at the base
            height: Height (Z dimension)
            tapered_length: Length at the top (defaults to length if None)
            tapered_width: Width at the top (defaults to width if None)
            label: Optional label for export
        """
        self.length = length
        self.width = width
        self.tapered_length = length if tapered_length is None else tapered_length
        self.tapered_width = width if tapered_width is None else tapered_width
        self.height = height

        if label:
            dimensions = f"{format_float(length)} x {format_float(width)}"
            tapered_dimensions = ' -> ' + (format_float(tapered_length) + ' x ' + format_float(tapered_width)) if self.tapered else ''
            logger.info(f"Smart box '{label}': {dimensions}{tapered_dimensions}, height: {format_float(height)}")

        if self.tapered:
            base = Face(Wire.make_rect(length, width))
            top = Face(Wire.make_rect(self.tapered_length, self.tapered_width)).move(Location((0, 0, height)))
            solid = loft([base, top])
        else:
            solid = Solid.make_box(length, width, height).move(Location((-length / 2, -width / 2, 0)))

        super().__init__(solid, label=label)

    @classmethod
    def with_base_angles_and_height(cls, length: float, width: float, height: float, angle_length: float, angle_width: float, label: str = None) -> 'SmartBox':
        """
        Creates a tapered box defined by base dimensions, height, and wall angles.

        Args:
            length: Length at the base
            width: Width at the base
            height: Height of the box
            angle_length: Angle of length-direction walls from horizontal (90° = vertical, <90° = inward taper)
            angle_width: Angle of width-direction walls from horizontal (90° = vertical, <90° = inward taper)
            label: Optional label for the box

        Returns:
            A new SmartBox with the specified geometry

        Example:
            # Box with 10° inward taper on all walls
            box = SmartBox.with_base_angles_and_height(100, 80, 50, 80, 80)

            # Box with vertical length walls and tapered width walls
            box = SmartBox.with_base_angles_and_height(100, 80, 50, 90, 75)
        """
        assert not are_numbers_too_close(advanced_mod(angle_length, 180, -90, 90), 0), f"angle_length is invalid: {angle_length}"
        assert not are_numbers_too_close(advanced_mod(angle_width, 180, -90, 90), 0), f"angle_width is invalid: {angle_width}"

        if height < 0:
            height = -height
            angle_length = -angle_length
            angle_width = -angle_width

        angle_length = advanced_mod(angle_length, 360, -180, 180)
        angle_width = advanced_mod(angle_width, 360, -180, 180)

        # Both angles must have the same sign (or be 90°) - can't have narrow end at different Z positions
        assert (angle_length > 0) == (angle_width > 0), f"Both angles must have the same sign: angle_length={angle_length}, angle_width={angle_width}"

        # Calculate dimensions at the opposite end from base params
        length_change = 2 * height / tan(radians(abs(angle_length)))
        width_change = 2 * height / tan(radians(abs(angle_width)))

        opposite_length = snap_to(length - length_change, 0)
        opposite_width = snap_to(width - width_change, 0)

        assert opposite_length >= 0, f"With length {length}, angle_length {angle_length}, and height {height}, opposite_length ends up negative: {opposite_length}"
        assert opposite_width >= 0, f"With width {width}, angle_width {angle_width}, and height {height}, opposite_width ends up negative: {opposite_width}"

        # Positive angle: base params at bottom, opposite at top
        # Negative angle: base params at top, opposite at bottom
        if angle_length > 0:
            return SmartBox(length, width, height, opposite_length, opposite_width, label)
        else:
            return SmartBox(opposite_length, opposite_width, height, length, width, label)

    @property
    def tapered(self) -> bool:
        return self.tapered_length != self.length or self.tapered_width != self.width

    @property
    def slope_length(self) -> float:
        """Rate of length change per unit height: (tapered_length - length) / height"""
        return (self.tapered_length - self.length) / self.height

    @property
    def slope_width(self) -> float:
        """Rate of width change per unit height: (tapered_width - width) / height"""
        return (self.tapered_width - self.width) / self.height

    def length_at(self, height_fraction: float) -> float:
        """Returns length at given height (0.0 = base, 1.0 = top)"""
        return self.length + (self.tapered_length - self.length) * height_fraction

    def width_at(self, height_fraction: float) -> float:
        """Returns width at given height (0.0 = base, 1.0 = top)"""
        return self.width + (self.tapered_width - self.width) * height_fraction

    def center(self, height_fraction: float = 1) -> Vector:
        """Returns center point at given height in global coordinates (0.0 = base, 1.0 = top)"""
        return Vector(0, 0, self.height * height_fraction)

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

        offset_length = self.length + (e + self.slope_length * d) + (w + self.slope_length * d)
        offset_width = self.width + (n + self.slope_width * d) + (s + self.slope_width * d)
        offset_tapered_length = self.tapered_length + (e - self.slope_length * u) + (w - self.slope_length * u)
        offset_tapered_width = self.tapered_width + (n - self.slope_width * u) + (s - self.slope_width * u)
        offset_height = self.height + d + u

        offset_box = SmartBox(offset_length, offset_width, offset_height, offset_tapered_length, offset_tapered_width, label)
        offset_box.move(self.x_mid + (e - w) / 2, self.y_mid + (n - s) / 2, self.z_min - d)

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

        result.solid = copy(self.solid)
        result.label = label or self.label
        result.length = self.length
        result.width = self.width
        result.tapered_length = self.tapered_length
        result.tapered_width = self.tapered_width
        result.height = self.height

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
