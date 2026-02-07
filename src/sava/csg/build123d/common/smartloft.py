from copy import copy

from build123d import Axis, Face, Location, Plane, Vector, VectorLike, Wire, extrude, loft

from sava.csg.build123d.common.smartsolid import SmartSolid


class SmartLoft(SmartSolid):
    base_profile: Face
    target_profile: Face

    @classmethod
    def create(cls, base: Wire | Face, target: Wire | Face, height: float = 0) -> "SmartLoft":
        """Create a lofted solid between two profiles.

        Args:
            base: Base profile (Wire or Face). Stays in place.
            target: Target profile (Wire or Face). Gets positioned at height distance from base.
            height: Distance from base to target along the axis orthogonal to base face.
                    If 0, target stays at its original position.

        Returns:
            SmartLoft containing the lofted shape.
        """
        base_face = base if isinstance(base, Face) else Face(base)
        target_face = target if isinstance(target, Face) else Face(target)

        if base_face.wrapped is None:
            raise ValueError("SmartLoft.create: base face is empty/invalid")
        if target_face.wrapped is None:
            raise ValueError("SmartLoft.create: target face is empty/invalid")

        if height != 0:
            # Move target along base's normal to be at `height` distance
            # Ensure positive height goes towards +Z (flip normal if it points more towards -Z)
            normal = base_face.normal_at()
            if normal.Z < 0:
                normal = -normal

            # Calculate current distance along normal from base to target
            current_distance = (target_face.center() - base_face.center()).dot(normal)

            # Move only along normal by the difference needed
            move_distance = height - current_distance
            offset = normal * move_distance
            target_face = copy(target_face).move(Location((offset.X, offset.Y, offset.Z)))

        result = cls(loft([base_face, target_face]))
        result.base_profile = copy(base_face)
        result.target_profile = copy(target_face)
        return result

    @classmethod
    def extrude(cls, profile: Wire | Face, amount: float, direction: VectorLike = (0, 0, 1)) -> "SmartLoft":
        """Create an extruded solid from a profile.

        Args:
            profile: Profile to extrude (Wire or Face).
            amount: Extrusion distance.
            direction: Extrusion direction vector. Defaults to (0, 0, 1).

        Returns:
            SmartLoft containing the extruded shape.
        """
        face = profile if isinstance(profile, Face) else Face(profile)
        result = cls(extrude(face, amount, direction))
        result.base_profile = copy(face)
        result.target_profile = copy(face).move(Location(tuple(d * amount for d in direction)))
        return result

    def move(self, x: float, y: float = 0, z: float = 0, plane: Plane = None) -> 'SmartLoft':
        super().move(x, y, z, plane=plane)
        # Convert plane-local offsets to global coordinates if plane is specified
        if plane is not None:
            global_offset = plane.x_dir * x + plane.y_dir * y + plane.z_dir * z
        else:
            global_offset = Vector(x, y, z)
        location = Location(global_offset)
        self.base_profile = self.base_profile.move(location)
        self.target_profile = self.target_profile.move(location)
        return self

    def rotate(self, axis: Axis, angle: float) -> 'SmartLoft':
        super().rotate(axis, angle)
        self.base_profile = self.base_profile.rotate(axis, angle)
        self.target_profile = self.target_profile.rotate(axis, angle)
        return self

    def orient(self, rotations: VectorLike) -> 'SmartLoft':
        super().orient(rotations)
        self.base_profile.orientation = rotations
        self.target_profile.orientation = rotations
        return self
