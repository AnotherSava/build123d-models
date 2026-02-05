from typing import TYPE_CHECKING

from build123d import Plane, Shape

from sava.csg.build123d.common.geometry import Alignment

if TYPE_CHECKING:
    from sava.csg.build123d.common.smartsolid import SmartSolid


class AlignmentBuilder:
    """Fluent builder for chaining alignment operations on a SmartSolid."""

    def __init__(self, target: 'SmartSolid', reference: 'SmartSolid | None', plane: Plane = Plane.XY):
        self.target = target
        self.reference = reference
        self.plane = plane

    def _parse_args(self, alignment_or_shift: 'Alignment | float', shift: float) -> tuple['Alignment', float]:
        if isinstance(alignment_or_shift, Alignment):
            return alignment_or_shift, shift  # .z(LL, 5) -> (LL, 5)
        return Alignment.C, alignment_or_shift  # .z(15) -> (C, 15)

    def x(self, alignment_or_shift: 'Alignment | float' = Alignment.C, shift: float = 0) -> 'AlignmentBuilder':
        alignment, shift = self._parse_args(alignment_or_shift, shift)
        self.target.align_x(self.reference, alignment, shift, self.plane)
        return self

    def y(self, alignment_or_shift: 'Alignment | float' = Alignment.C, shift: float = 0) -> 'AlignmentBuilder':
        alignment, shift = self._parse_args(alignment_or_shift, shift)
        self.target.align_y(self.reference, alignment, shift, self.plane)
        return self

    def z(self, alignment_or_shift: 'Alignment | float' = Alignment.C, shift: float = 0) -> 'AlignmentBuilder':
        alignment, shift = self._parse_args(alignment_or_shift, shift)
        self.target.align_z(self.reference, alignment, shift, self.plane)
        return self

    def xy(self, alignment: 'Alignment' = Alignment.C, shift_x: float = 0, shift_y: float = 0) -> 'AlignmentBuilder':
        return self.x(alignment, shift_x).y(alignment, shift_y)

    def xz(self, alignment: 'Alignment' = Alignment.C, shift_x: float = 0, shift_z: float = 0) -> 'AlignmentBuilder':
        return self.x(alignment, shift_x).z(alignment, shift_z)

    def yz(self, alignment: 'Alignment' = Alignment.C, shift_y: float = 0, shift_z: float = 0) -> 'AlignmentBuilder':
        return self.y(alignment, shift_y).z(alignment, shift_z)

    def done(self) -> 'SmartSolid':
        """Return the SmartSolid for further chaining with other methods."""
        return self.target

    def then(self) -> 'SmartSolid':
        """Return the SmartSolid for further chaining with other methods."""
        return self.target
