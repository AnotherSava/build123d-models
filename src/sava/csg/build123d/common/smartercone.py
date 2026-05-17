from __future__ import annotations

from dataclasses import dataclass
from enum import IntEnum
from math import acos, atan2, cos, radians, sin, tan

import numpy as np

from build123d import Edge, Face, Plane, Solid, Vector, Wire, loft

from sava.common.advanced_math import advanced_mod
from sava.csg.build123d.common.geometry import MIN_SIZE_OCCT, are_numbers_too_close, snap_to
from sava.csg.build123d.common.smartsolid import SmartSolid


class InnerMode(IntEnum):
    THICKNESS = 0  # preserve wall thickness (outer - inner) during extend
    RADIUS = 1     # preserve inner radius and inner shifts as-is during extend


@dataclass(frozen=True)
class ConeSection:
    """A cross-section of a SmarterCone at a given height.

    Inner fields use None to mean "inherit from outer" (or "no inner hole" for inner_radius),
    while outer fields use 0 as a concrete default position.
    """
    radius: float
    height: float = 0
    inner_radius: float | None = None  # None = no inner hole
    shift_x: float = 0  # offset of this section's center from the cone axis along X
    shift_y: float = 0  # offset of this section's center from the cone axis along Y
    inner_shift_x: float | None = None  # None = follow outer shift
    inner_shift_y: float | None = None  # None = follow outer shift

    def validate(self, index: int, previous: ConeSection | None = None) -> None:
        assert self.radius >= 0, f"Section {index}: radius must be >= 0, got {self.radius}"
        if index == 0:
            assert self.height == 0, f"Section 0: height must be 0, got {self.height}"
            assert self.shift_x == 0 and self.shift_y == 0, "Section 0: must have no shift"
        if previous is not None:
            if previous.height == 0:
                pass  # any height ok: 0 for radius steps, positive/negative to establish direction
            elif previous.height > 0:
                assert self.height >= previous.height, f"Section {index}: heights must be monotonically non-decreasing, got {previous.height} then {self.height}"
            else:
                assert self.height <= previous.height, f"Section {index}: heights must be monotonically non-increasing, got {previous.height} then {self.height}"
        if self.inner_radius is not None:
            assert 0 <= self.inner_radius < self.radius, f"Section {index}: inner radius must satisfy 0 <= inner_radius < radius, got inner={self.inner_radius}, outer={self.radius}"
        if self.inner_shift_x is not None or self.inner_shift_y is not None:
            assert self.inner_radius is not None, f"Section {index}: inner_shift requires inner_radius"


class SmarterCone(SmartSolid):
    """Builder for rotationally symmetric solids: cylinders, cones, and multi-section profiles.

    See docs/code/smartercone.md for the full builder guide.
    """

    def __init__(self, sections: list[ConeSection], plane: Plane = Plane.XY, angle: float = 360, label: str = None):
        # Validation
        assert len(sections) >= 1, "Must have at least 1 section"
        for i in range(len(sections)):
            previous_section = sections[i - 1] if i > 0 else None
            sections[i].validate(i, previous_section)

        self.sections = list(sections)
        self.plane = plane
        self.angle = angle
        self._inner_mode = InnerMode.THICKNESS
        solid = self._build_solid()
        super().__init__(solid, label=label)

    def _geometry_sections(self) -> list[ConeSection]:
        """Return sections for 3D geometry, offsetting radius-step sections by epsilon.

        A radius step (same height as previous) becomes a tiny-height segment so
        the previous segment keeps its original end radius.
        """
        result = [self.sections[0]]
        for i, s in enumerate(self.sections[1:], start=1):
            if s.height == self.sections[i - 1].height:
                sign = self._height_sign or 1
                prev_geo_height = result[-1].height
                result.append(ConeSection(s.radius, prev_geo_height + sign * MIN_SIZE_OCCT, s.inner_radius, s.shift_x, s.shift_y, s.inner_shift_x, s.inner_shift_y))
            else:
                result.append(s)
        return result

    def _build_solid(self) -> Solid:
        geo = self._geometry_sections()

        if len(geo) == 1:
            return Solid.make_cylinder(max(geo[0].radius, MIN_SIZE_OCCT), MIN_SIZE_OCCT, self.plane, self.angle)

        has_shift = any(s.shift_x != 0 or s.shift_y != 0 for s in geo)
        has_inner_shift = any(s.inner_shift_x is not None or s.inner_shift_y is not None for s in geo)

        # Analytical path: 2 sections, no shift, no inner_radius, angle==360
        if len(geo) == 2 and not has_shift and not any(s.inner_radius is not None for s in geo) and self.angle == 360:
            base = geo[0]
            top = geo[1]
            h = top.height
            build_plane = self.plane
            if h < 0:
                build_plane = Plane(self.plane.origin, x_dir=self.plane.x_dir, z_dir=-self.plane.z_dir)
                h = -h
            if are_numbers_too_close(base.radius, top.radius):
                return Solid.make_cylinder(base.radius, h, build_plane, self.angle)
            else:
                return Solid.make_cone(base.radius, top.radius, h, build_plane, self.angle)

        # Loft path
        has_inner = any(s.inner_radius is not None for s in geo)
        faces = []
        for section in geo:
            face_plane = self._section_plane(section)
            if has_inner:
                inner_radius = section.inner_radius if section.inner_radius is not None else MIN_SIZE_OCCT
                inner_plane = self._inner_section_plane(section) if has_inner_shift else None
                faces.append(self._create_face(section.radius, face_plane, inner_radius, inner_plane))
            else:
                faces.append(self._create_face(section.radius, face_plane))

        return loft(faces, ruled=True)

    def _section_plane(self, section: ConeSection) -> Plane:
        return Plane(self._section_center(section), x_dir=self.plane.x_dir, z_dir=self.plane.z_dir)

    def _inner_section_plane(self, section: ConeSection) -> Plane:
        isx = section.inner_shift_x if section.inner_shift_x is not None else section.shift_x
        isy = section.inner_shift_y if section.inner_shift_y is not None else section.shift_y
        origin = self.plane.origin + self.plane.z_dir * section.height + self.plane.x_dir * isx + self.plane.y_dir * isy
        return Plane(origin, x_dir=self.plane.x_dir, z_dir=self.plane.z_dir)

    def _create_wire(self, radius: float, face_plane: Plane) -> Wire:
        actual_radius = max(radius, MIN_SIZE_OCCT)
        if self.angle == 360:
            return Wire.make_circle(actual_radius, face_plane)
        else:
            arcs = [Edge.make_circle(actual_radius, face_plane, start_angle=0, end_angle=self.angle)]
            line1 = Edge.make_line(face_plane.origin, arcs[0] @ 0)
            line2 = Edge.make_line(arcs[-1] @ 1, face_plane.origin)
            return Wire([line1] + arcs + [line2])

    def _create_face(self, radius: float, face_plane: Plane, inner_radius: float = None, inner_plane: Plane = None) -> Face:
        outer_wire = self._create_wire(radius, face_plane)

        if inner_radius is None:
            return Face(outer_wire)

        inner_wire = self._create_wire(inner_radius, inner_plane or face_plane)
        return Face(outer_wire, [inner_wire])

    def _compute_fillet_sections(self, before: ConeSection, junction: ConeSection, after: ConeSection, fillet_radius: float, num_segments: int = 8) -> list[ConeSection]:
        """Insert arc sections to round a junction, computed in (h, r, sx, sy) space so shifts are handled correctly."""
        def to_vec(s: ConeSection) -> np.ndarray:
            return np.array([s.height, s.radius, s.shift_x, s.shift_y])

        def normalize(v: np.ndarray) -> tuple[np.ndarray, float]:
            length = np.linalg.norm(v)
            return v / length, length

        p0, p1, p2 = to_vec(before), to_vec(junction), to_vec(after)
        d1, len1 = normalize(p1 - p0)
        d2, len2 = normalize(p2 - p1)
        assert len1 > 0 and len2 > 0, "Degenerate segments cannot be filleted"

        cos_a = np.clip(d1 @ d2, -1.0, 1.0)
        deviation = acos(cos_a)
        if deviation < 1e-6:
            return [junction]

        half = deviation / 2
        trim = fillet_radius * tan(half)
        assert trim < len1, f"Fillet radius {fillet_radius} too large for incoming segment"
        assert trim < len2, f"Fillet radius {fillet_radius} too large for outgoing segment"

        t1 = p1 - d1 * trim
        t2 = p1 + d2 * trim

        bis, bis_len = normalize(-d1 + d2)
        assert bis_len > 1e-10, "Degenerate bisector"
        center = p1 + bis * (fillet_radius / cos(half))

        # Orthonormal basis for the arc plane
        v1 = t1 - center
        e1, _ = normalize(v1)
        v2 = t2 - center
        e2, _ = normalize(v2 - e1 * (v2 @ e1))
        arc_angle = atan2(v2 @ e2, v2 @ e1)

        if self._inner_mode == InnerMode.THICKNESS:
            wall_thickness = junction.radius - junction.inner_radius if junction.inner_radius is not None else None
            inner_offset_x = junction.inner_shift_x - junction.shift_x if junction.inner_shift_x is not None else None
            inner_offset_y = junction.inner_shift_y - junction.shift_y if junction.inner_shift_y is not None else None
        else:
            fixed_inner_radius = junction.inner_radius
            fixed_inner_shift_x = junction.inner_shift_x
            fixed_inner_shift_y = junction.inner_shift_y

        result = []
        for i in range(num_segments + 1):
            t = i / num_segments
            a = arc_angle * t
            point = center + e1 * (fillet_radius * cos(a)) + e2 * (fillet_radius * sin(a))
            h, r, sx, sy = point
            r = max(r, 0)
            if self._inner_mode == InnerMode.THICKNESS:
                ir = max(r - wall_thickness, MIN_SIZE_OCCT) if wall_thickness is not None else None
                isx = sx + inner_offset_x if inner_offset_x is not None else None
                isy = sy + inner_offset_y if inner_offset_y is not None else None
            else:
                ir = fixed_inner_radius
                isx = fixed_inner_shift_x
                isy = fixed_inner_shift_y
            result.append(ConeSection(r, h, inner_radius=ir, shift_x=sx, shift_y=sy, inner_shift_x=isx, inner_shift_y=isy))
        return result

    # --- Properties ---

    @property
    def height(self) -> float:
        if len(self.sections) == 1:
            return 0
        return self.sections[-1].height

    @property
    def has_inner(self) -> bool:
        return any(s.inner_radius is not None for s in self.sections)

    @property
    def base_radius(self) -> float:
        return self.sections[0].radius

    @property
    def top_radius(self) -> float:
        return self.sections[-1].radius

    def _resolve_position(self, position: float) -> tuple[int, float]:
        """Convert a float position to (segment_index, fraction) within that segment.

        Returns (segment, fraction) where sections[segment] and sections[segment+1]
        are the endpoints, and fraction is the interpolation parameter in [0, 1].
        """
        last_segment = len(self.sections) - 2
        assert last_segment >= 0, "Need at least 2 sections to resolve position"
        assert 0 <= position <= last_segment + 1, f"Position {position} out of range [0, {last_segment + 1}]"
        segment = int(position)
        if segment > last_segment:
            segment = last_segment
        fraction = position - segment
        return segment, fraction

    def radius(self, position: float) -> float:
        segment, fraction = self._resolve_position(position)
        r1 = self.sections[segment].radius
        r2 = self.sections[segment + 1].radius
        return r1 + (r2 - r1) * fraction

    def _section_center(self, section: ConeSection) -> Vector:
        return self.plane.origin + self.plane.z_dir * section.height + self.plane.x_dir * section.shift_x + self.plane.y_dir * section.shift_y

    def center(self, position: float) -> Vector:
        segment, fraction = self._resolve_position(position)
        c1 = self._section_center(self.sections[segment])
        c2 = self._section_center(self.sections[segment + 1])
        return c1 + (c2 - c1) * fraction

    @property
    def _height_sign(self) -> int:
        """Return 1 if heights grow positive, -1 if negative, 0 if direction not yet established."""
        for s in self.sections[1:]:
            if s.height != 0:
                return 1 if s.height > 0 else -1
        return 0

    # --- Builder API ---

    @classmethod
    def base(cls, radius: float, *, plane: Plane = Plane.XY, angle: float = 360, label: str = None) -> 'SmarterCone':
        return cls([ConeSection(radius)], plane, angle, label)

    @classmethod
    def cylinder(cls, radius: float, height: float, *, plane: Plane = Plane.XY, angle: float = 360, label: str = None) -> 'SmarterCone':
        return cls([ConeSection(radius), ConeSection(radius, height)], plane, angle, label)

    def inner(self, radius: float = None, *, shift_x: float = None, shift_y: float = None, mode: InnerMode = None) -> 'SmarterCone':
        assert radius is not None or mode is not None, "inner() requires at least radius or mode"
        if mode is not None:
            self._inner_mode = mode
        if radius is None:
            self._recalculate_inner()
            return self
        last = self.sections[-1]
        if radius == 0:
            replaced = ConeSection(last.radius, last.height, inner_radius=None, shift_x=last.shift_x, shift_y=last.shift_y, inner_shift_x=None, inner_shift_y=None)
        else:
            assert 0 < radius < last.radius, f"Inner radius must satisfy 0 < inner_radius < radius, got inner={radius}, outer={last.radius}"
            replaced = ConeSection(last.radius, last.height, inner_radius=radius, shift_x=last.shift_x, shift_y=last.shift_y, inner_shift_x=shift_x, inner_shift_y=shift_y)
        self.sections[-1] = replaced
        self._rebuild()
        return self

    def _rebuild(self) -> None:
        """Rebuild `self.solid` from `self.sections` and re-apply tracked
        transforms (`self._orientation`, `self.origin`) so prior `rotate()` /
        `move()` calls survive the rebuild. Without this, mid-build transforms
        would silently disappear because `_build_solid()` always produces an
        unrotated solid at the origin in `self.plane`.
        """
        self.solid = self._build_solid()
        self._apply_tracked_transforms()
        self.assert_valid()

    def _propagate_inner(self, prev: ConeSection, outer_radius: float, shift_x: float, shift_y: float) -> tuple[float | None, float | None, float | None]:
        """Compute inner radius/shifts for a new section based on the previous section and current mode.

        Returns (inner_radius, inner_shift_x, inner_shift_y). All None if prev has no inner.
        """
        if prev.inner_radius is None:
            return None, None, None
        if self._inner_mode == InnerMode.THICKNESS:
            wall_thickness = prev.radius - prev.inner_radius
            inner_radius = max(outer_radius - wall_thickness, MIN_SIZE_OCCT)
            inner_shift_x = shift_x + (prev.inner_shift_x - prev.shift_x) if prev.inner_shift_x is not None else None
            inner_shift_y = shift_y + (prev.inner_shift_y - prev.shift_y) if prev.inner_shift_y is not None else None
        else:
            inner_radius = prev.inner_radius
            assert inner_radius < outer_radius, f"RADIUS mode: inner_radius {inner_radius} must be < outer radius {outer_radius}"
            inner_shift_x = prev.inner_shift_x
            inner_shift_y = prev.inner_shift_y
        return inner_radius, inner_shift_x, inner_shift_y

    def _recalculate_inner(self) -> None:
        """Recalculate the last section's inner radius/shifts using the current mode."""
        if len(self.sections) < 2:
            return
        prev = self.sections[-2]
        last = self.sections[-1]
        if prev.inner_radius is None or last.inner_radius is None:
            return
        inner_radius, inner_shift_x, inner_shift_y = self._propagate_inner(prev, last.radius, last.shift_x, last.shift_y)
        self.sections[-1] = ConeSection(last.radius, last.height, inner_radius=inner_radius, shift_x=last.shift_x, shift_y=last.shift_y, inner_shift_x=inner_shift_x, inner_shift_y=inner_shift_y)
        self._rebuild()

    def _resolve_extend_params(self, radius: float, height: float, angle: float, shift_x: float, shift_y: float) -> tuple[float, float]:
        """Resolve extend parameters into absolute (radius, height)."""
        prev = self.sections[-1]
        has_r, has_h, has_a = radius is not None, height is not None, angle is not None
        assert not (has_a and (shift_x != 0 or shift_y != 0)), "Cannot combine angle with shift — wall angle is ambiguous when shifted"

        # height param is relative; convert to absolute for internal storage
        if has_h:
            assert height != 0, f"Height must be non-zero, got {height}"
            if self._height_sign != 0:
                assert (height > 0) == (self._height_sign > 0), f"Height sign must match existing direction"
            height = prev.height + height

        if has_r and has_h and not has_a:
            pass
        elif has_h and not has_r and not has_a:
            radius = prev.radius
        elif has_a and has_h and not has_r:
            segment_height = abs(height - prev.height)
            angle = advanced_mod(angle, 360, -180, 180)
            assert not are_numbers_too_close(advanced_mod(angle, 180, -90, 90), 0), f"Angle is invalid: {angle}"
            radius_change = segment_height / tan(radians(abs(angle)))
            radius = snap_to(prev.radius + (-radius_change if angle >= 0 else radius_change), 0)
            assert radius >= 0, f"Computed radius is negative: {radius}"
        elif has_a and has_r and not has_h:
            angle = advanced_mod(angle, 360, -180, 180)
            assert not are_numbers_too_close(advanced_mod(angle, 180, -90, 90), 0), f"Angle is invalid: {angle}"
            sign = self._height_sign or 1
            height = prev.height + sign * abs(radius - prev.radius) / abs(tan(radians(angle)))
        elif has_r and not has_h and not has_a:
            height = prev.height  # radius step: same height, skip in geometry
        elif not has_r and not has_h and not has_a:
            radius = prev.radius
            height = prev.height  # inner-only step: same outer radius and height
        else:
            assert False, "Invalid parameter combination: specify (radius+height), (angle+height), (angle+radius), (radius only), (height only), or (no params)"

        return radius, height

    def extend(self, *, radius: float = None, height: float = None, angle: float = None,
               shift_x: float = 0, shift_y: float = 0, fillet: float = None) -> 'SmarterCone':
        """Extend the cone with a new section.

        angle: wall steepness in degrees. 90° = vertical wall (no radius change).
        Positive = inward (radius decreases), negative = outward (radius increases).
        Direction-independent: same convention regardless of height sign.
        """
        prev = self.sections[-1]
        radius, height = self._resolve_extend_params(radius, height, angle, shift_x, shift_y)

        inner_radius, inner_shift_x, inner_shift_y = self._propagate_inner(prev, radius, shift_x, shift_y)

        new_section = ConeSection(radius, height, inner_radius=inner_radius, shift_x=shift_x, shift_y=shift_y, inner_shift_x=inner_shift_x, inner_shift_y=inner_shift_y)
        if fillet is not None:
            assert len(self.sections) >= 2, "Cannot fillet: need at least one prior segment"
            fillet_sections = self._compute_fillet_sections(self.sections[-2], self.sections[-1], new_section, fillet)
            self.sections.pop()
            self.sections.extend(fillet_sections)
        self.sections.append(new_section)
        self._rebuild()
        return self

    # --- create_offset / create_shell / copy ---

    def create_offset(self, offset: float, label: str = None) -> 'SmarterCone':
        new_sections = []
        for s in self.sections:
            new_radius = s.radius + offset
            assert new_radius >= 0, f"Offset would make radius negative: {s.radius} + {offset} = {new_radius}"
            new_inner = None
            if s.inner_radius is not None:
                new_inner = max(s.inner_radius + offset, MIN_SIZE_OCCT)
            new_sections.append(ConeSection(new_radius, s.height, new_inner, s.shift_x, s.shift_y, s.inner_shift_x, s.inner_shift_y))
        result = SmarterCone(new_sections, self.plane, self.angle, label or self.label)
        return result.colocate(self)

    def create_shell(self, thickness: float, label: str = None) -> 'SmarterCone':
        assert thickness != 0, "Shell thickness must be non-zero"
        assert not self.has_inner, "Cannot create shell on already hollow cone"

        new_sections = []
        for s in self.sections:
            if thickness > 0:
                outer_r = s.radius + thickness
                inner_r = max(s.radius, MIN_SIZE_OCCT)
            else:
                outer_r = s.radius
                inner_r = max(s.radius + thickness, MIN_SIZE_OCCT)
            new_sections.append(ConeSection(outer_r, s.height, inner_r, s.shift_x, s.shift_y, s.inner_shift_x, s.inner_shift_y))
        result = SmarterCone(new_sections, self.plane, self.angle, label or self.label)
        return result.colocate(self)

    def get_outer_cone(self, label: str = None) -> 'SmarterCone':
        new_sections = [ConeSection(s.radius, s.height, shift_x=s.shift_x, shift_y=s.shift_y) for s in self.sections]
        result = SmarterCone(new_sections, self.plane, self.angle, label or self.label)
        return result.colocate(self)

    def get_inner_cone(self, label: str = None) -> 'SmarterCone':
        assert self.has_inner, "No inner radius defined"
        s0 = self.sections[0]
        base_sx = s0.inner_shift_x if s0.inner_shift_x is not None else s0.shift_x
        base_sy = s0.inner_shift_y if s0.inner_shift_y is not None else s0.shift_y
        new_sections = []
        for s in self.sections:
            r = s.inner_radius if s.inner_radius is not None else MIN_SIZE_OCCT
            sx = (s.inner_shift_x if s.inner_shift_x is not None else s.shift_x) - base_sx
            sy = (s.inner_shift_y if s.inner_shift_y is not None else s.shift_y) - base_sy
            new_sections.append(ConeSection(r, s.height, shift_x=sx, shift_y=sy))
        new_plane = Plane(self.plane.origin + self.plane.x_dir * base_sx + self.plane.y_dir * base_sy, x_dir=self.plane.x_dir, z_dir=self.plane.z_dir)
        result = SmarterCone(new_sections, new_plane, self.angle, label or self.label)
        return result.colocate(self)

    def copy(self, label: str = None) -> 'SmarterCone':
        result = SmarterCone.__new__(SmarterCone)
        self._copy_base_fields(result, label)
        result.sections = list(self.sections)
        result.plane = self.plane
        result.angle = self.angle
        result._inner_mode = self._inner_mode
        return result
