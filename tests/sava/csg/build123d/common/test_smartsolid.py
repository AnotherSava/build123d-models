import unittest

from build123d import Axis, Box, Plane, ShapeList, Sphere, Vector
from parameterized import parameterized

from sava.csg.build123d.common.geometry import rotate_vector
from sava.csg.build123d.common.pencil import Pencil
from sava.csg.build123d.common.smartbox import SmartBox
from sava.csg.build123d.common.smartsolid import SmartSolid
from tests.sava.csg.build123d.test_utils import assertVectorAlmostEqual


class TestSmartSolidBoundBox(unittest.TestCase):

    @parameterized.expand([
        # Default XY plane
        (Plane.XY, 10, 20, 30),
        # XZ plane (rotated 90 degrees around X axis)
        (Plane.XZ, 10, 30, 20),
        # YZ plane (rotated 90 degrees around Y axis)
        (Plane.YZ, 20, 30, 10),
    ])
    def test_get_bound_box_standard_planes(self, plane, expected_x, expected_y, expected_z) -> None:
        """Test get_bound_box with standard planes"""
        box = SmartSolid(Box(10, 20, 30))
        bbox = box.get_bound_box(plane)

        assertVectorAlmostEqual(self, bbox.size, (expected_x, expected_y, expected_z))


class TestSmartSolidOrient(unittest.TestCase):

    def test_orient_default_plane(self) -> None:
        """Test orient with default XY plane"""
        box = SmartSolid(Box(10, 20, 30))
        box.orient((0, 0, 90))

        # After 90 degree rotation around Z, X and Y dimensions should swap
        bbox = box.bound_box
        assertVectorAlmostEqual(self, bbox.size, (20, 10, 30))

    def test_orient_xz_plane(self) -> None:
        """Test orient relative to XZ plane"""
        box = SmartSolid(Box(10, 20, 30))
        box.rotate_multi((0, 0, 90), plane=Plane.XZ)

        # Rotation of 90 degrees in XZ plane coordinate system
        # should swap X and Z dimensions
        bbox = box.bound_box
        self.assertAlmostEqual(bbox.size.X, 30, places=1)
        self.assertAlmostEqual(bbox.size.Y, 20, places=1)
        self.assertAlmostEqual(bbox.size.Z, 10, places=1)


class TestSmartSolidRotate(unittest.TestCase):

    def test_rotate_fixed_axes_behavior(self) -> None:
        """Test that rotate uses fixed axes, not object-attached axes"""
        box = SmartSolid(Box(10, 20, 30))

        # Apply rotation (90, 90, 0) using fixed axes
        box.rotate_multi((90, 90, 0))

        # Should result in orientation (90, 0, -90) due to fixed-axis composition
        orientation = box.solid.orientation
        self.assertAlmostEqual(orientation.X, 90, places=1)
        self.assertAlmostEqual(orientation.Y, 0, places=1)
        self.assertAlmostEqual(orientation.Z, -90, places=1)

    @parameterized.expand([
        (Plane.XY,),
        (Plane.XZ,),
        (Plane.YZ,),
    ])
    def test_rotate_zero_incremental(self, plane) -> None:
        """Test that (0,0,0) rotation doesn't change orientation regardless of plane"""
        box = SmartSolid(Box(10, 20, 30))

        # Set some initial orientation
        initial_orientation = (45, 30, 60)
        box.rotate_multi(initial_orientation, plane)

        # Store the orientation after initial setup
        before_rotation = box.solid.orientation
        _before_x, _before_y, _before_z = before_rotation.X, before_rotation.Y, before_rotation.Z

        # Apply zero rotation
        box.rotate_multi((0, 0, 0), plane)

        # Orientation should remain unchanged
        after_rotation = box.solid.orientation
        assertVectorAlmostEqual(self, after_rotation, before_rotation)


class TestSmartSolidBoundsAlongAxis(unittest.TestCase):

    @parameterized.expand([
        # Test with standard axes
        (Axis.X, 10.0),  # X-axis along box length
        (Axis.Y, 20.0),  # Y-axis along box width
        (Axis.Z, 30.0),  # Z-axis along box height
    ])
    def test_get_bounds_along_axis_standard_axes(self, axis, expected_size) -> None:
        """Test get_bounds_along_axis with standard coordinate axes"""
        box = SmartSolid(Box(10, 20, 30))
        min_coord, max_coord = box.get_bounds_along_axis(axis)

        actual_size = max_coord - min_coord
        self.assertAlmostEqual(actual_size, expected_size, places=5)

    @parameterized.expand([
        # Test with diagonal axes - bounding box projections, not face diagonals
        (Axis((0, 0, 0), (1, 1, 0)), 21.213),  # XY projection: (10+20)/√2 = 21.213
        (Axis((0, 0, 0), (1, 0, 1)), 28.284),  # XZ projection: (10+30)/√2 = 28.284
        (Axis((0, 0, 0), (0, 1, 1)), 35.355),  # YZ projection: (20+30)/√2 = 35.355
    ])
    def test_get_bounds_along_axis_diagonal_axes(self, axis, expected_size) -> None:
        """Test get_bounds_along_axis with diagonal axes"""
        box = SmartSolid(Box(10, 20, 30))
        min_coord, max_coord = box.get_bounds_along_axis(axis)

        actual_size = max_coord - min_coord
        self.assertAlmostEqual(actual_size, expected_size, places=2)  # Lower precision for diagonal calculations

    def test_get_bounds_along_axis_custom_origin(self) -> None:
        """Test get_bounds_along_axis with custom axis origin"""
        box = SmartSolid(Box(10, 20, 30))

        # Test with axis origin at box center
        axis_through_center = Axis((5, 10, 15), (1, 0, 0))  # X-axis through box center
        min_coord, max_coord = box.get_bounds_along_axis(axis_through_center)

        # Should still have the same size along X direction
        actual_size = max_coord - min_coord
        self.assertAlmostEqual(actual_size, 10.0, places=5)

    def test_get_bounds_along_axis_moved_box(self) -> None:
        """Test get_bounds_along_axis with moved box"""
        box = SmartSolid(Box(10, 20, 30))
        box.move(100, 200, 300)  # Move box far from origin

        min_coord, max_coord = box.get_bounds_along_axis(Axis.X)
        actual_size = max_coord - min_coord

        # Size should remain the same regardless of position
        self.assertAlmostEqual(actual_size, 10.0, places=5)

    def test_get_bounds_along_axis_empty_solid(self) -> None:
        """Test get_bounds_along_axis with None solid raises error"""
        empty_solid = SmartSolid()

        with self.assertRaises(RuntimeError) as context:
            empty_solid.get_bounds_along_axis(Axis.X)

        self.assertIn("Cannot get bounds of None solid", str(context.exception))

    @parameterized.expand([
        # Test with standard axes for sphere
        (Axis.X, 20.0),  # X-axis should give diameter
        (Axis.Y, 20.0),  # Y-axis should give diameter
        (Axis.Z, 20.0),  # Z-axis should give diameter
    ])
    def test_get_bounds_along_axis_sphere(self, axis, expected_diameter) -> None:
        """Test get_bounds_along_axis with sphere (radius=10)"""
        sphere = SmartSolid(Sphere(10))
        min_coord, max_coord = sphere.get_bounds_along_axis(axis)

        actual_diameter = max_coord - min_coord
        self.assertAlmostEqual(actual_diameter, expected_diameter, places=3)

    def test_get_bounds_along_axis_sphere_diagonal(self) -> None:
        """Test get_bounds_along_axis with sphere along diagonal axis"""
        sphere = SmartSolid(Sphere(10))

        # Test diagonal axis - should also give diameter 20
        diagonal_axis = Axis((0, 0, 0), (1, 1, 1))
        min_coord, max_coord = sphere.get_bounds_along_axis(diagonal_axis)

        actual_diameter = max_coord - min_coord
        self.assertAlmostEqual(actual_diameter, 20.0, places=3)


class TestSmartSolidShapeList(unittest.TestCase):
    """Tests for SmartSolid containing ShapeList (multiple shapes)."""

    def _create_shape_list_solid(self) -> SmartSolid:
        """Create a SmartSolid containing multiple shapes (ShapeList)."""
        box1 = SmartSolid(Box(10, 10, 10))
        box2 = SmartSolid(Box(10, 10, 10))
        box2.move(20, 0, 0)
        return SmartSolid([box1, box2])

    def test_orient_shapelist_works(self) -> None:
        """Test that orient() works on ShapeList - it wraps to Compound first."""
        solid = self._create_shape_list_solid()

        solid.orient((0, 0, 90))

        # After 90 degree rotation around Z, the shape should have different bounds
        # Original: two boxes at x=0 and x=20, total x_size ~30
        # After rotation: should be ~10 in X (the width becomes the length)
        self.assertAlmostEqual(solid.x_size, 10, places=1)
        self.assertAlmostEqual(solid.y_size, 30, places=1)

    def test_rotate_multi_shapelist_works(self) -> None:
        """Test that rotate_multi() works on ShapeList - reads _orientation, not solid.orientation."""
        solid = self._create_shape_list_solid()

        solid.rotate_multi((0, 0, 90))

        # After 90 degree rotation around Z, the shape should have different bounds
        # Original: two boxes at x=0 and x=20, total x_size ~30
        # After rotation: should be ~10 in X (the width becomes the length)
        self.assertAlmostEqual(solid.x_size, 10, places=1)
        self.assertAlmostEqual(solid.y_size, 30, places=1)

    def test_rotate_with_axis_shapelist_works(self) -> None:
        """Test that rotate_with_axis() works on ShapeList by wrapping first."""
        solid = self._create_shape_list_solid()

        solid.rotate(Axis.Z, 90)

        # After 90 degree rotation around Z, the shape should have different bounds
        # Original: two boxes at x=0 and x=20, total x_size ~30
        # After rotation: should be ~10 in X (the width becomes the length)
        self.assertAlmostEqual(solid.x_size, 10, places=1)
        self.assertAlmostEqual(solid.y_size, 30, places=1)


class TestSmartSolidOriginTracking(unittest.TestCase):
    """Tests for origin tracking across various transformations."""

    def test_move_tracks_origin(self) -> None:
        """Test that move() updates origin correctly."""
        box = SmartSolid(Box(100, 50, 30))
        box.move(10, 20, 30)
        assertVectorAlmostEqual(self, box.origin, (10, 20, 30))

    def test_colocate_tracks_origin(self) -> None:
        """Test that colocate() updates origin correctly."""
        b1 = SmartSolid(Box(100, 50, 30))
        b1.move(10, 20, 30)

        b2 = SmartSolid(Box(50, 50, 50))
        b2.colocate(b1)

        assertVectorAlmostEqual(self, b2.origin, (10, 20, 30))

    def test_orient_does_not_move_origin(self) -> None:
        """Test that orient() does not change origin — rotation only, no position change."""
        box = SmartSolid(Box(100, 50, 30))
        box.move(10, 0, 0)  # origin at (10, 0, 0)

        box.orient((0, 0, 90))  # Rotate 90° around Z

        # orient() is rotation-only — origin stays at (10, 0, 0)
        assertVectorAlmostEqual(self, box.origin, (10, 0, 0))

    def test_orient_does_not_move_origin_x_rotation(self) -> None:
        """Test that orient() does not change origin — X rotation."""
        box = SmartSolid(Box(100, 50, 30))
        box.move(0, 10, 0)  # origin at (0, 10, 0)

        box.orient((90, 0, 0))  # Rotate 90° around X

        # orient() is rotation-only — origin stays at (0, 10, 0)
        assertVectorAlmostEqual(self, box.origin, (0, 10, 0))

    def test_orient_does_not_move_origin_y_rotation(self) -> None:
        """Test that orient() does not change origin — Y rotation."""
        box = SmartSolid(Box(100, 50, 30))
        box.move(10, 0, 0)  # origin at (10, 0, 0)

        box.orient((0, 90, 0))  # Rotate 90° around Y

        # orient() is rotation-only — origin stays at (10, 0, 0)
        assertVectorAlmostEqual(self, box.origin, (10, 0, 0))

    def test_mirror_xz_resets_origin(self) -> None:
        """mirror() produces a fresh OCC shape with location.position == (0, 0, 0);
        the class invariant requires self.origin to match, so it resets to (0, 0, 0)
        rather than reflecting the previous value."""
        box = SmartSolid(Box(100, 50, 30))
        box.move(10, 5, 0)

        box.mirror(Plane.XZ)

        assertVectorAlmostEqual(self, box.origin, (0, 0, 0))

    def test_mirror_yz_resets_origin(self) -> None:
        """mirror() resets self.origin to (0, 0, 0) (see test_mirror_xz_resets_origin)."""
        box = SmartSolid(Box(100, 50, 30))
        box.move(10, 5, 0)

        box.mirror(Plane.YZ)

        assertVectorAlmostEqual(self, box.origin, (0, 0, 0))

    def test_scale_resets_origin(self) -> None:
        """scale() produces a fresh OCC shape with location.position == (0, 0, 0);
        self.origin resets to match the invariant."""
        box = SmartSolid(Box(100, 50, 30))
        box.move(10, 5, 3)

        box.scale(2, 2, 2)

        assertVectorAlmostEqual(self, box.origin, (0, 0, 0))

    def test_scale_non_uniform_resets_origin(self) -> None:
        """Non-uniform scale() also resets self.origin to (0, 0, 0)."""
        box = SmartSolid(Box(100, 50, 30))
        box.move(10, 10, 10)

        box.scale(2, 3, 4)

        assertVectorAlmostEqual(self, box.origin, (0, 0, 0))

    def test_rotate_axis_tracks_origin(self) -> None:
        """Test that rotate(axis, angle) updates origin correctly."""
        box = SmartSolid(Box(100, 50, 30))
        box.move(10, 0, 0)  # origin at (10, 0, 0)

        box.rotate(Axis.Z, 90)  # Rotate 90° around Z

        # After 90° Z rotation, (10, 0, 0) -> (0, 10, 0)
        assertVectorAlmostEqual(self, box.origin, (0, 10, 0))

    def test_copy_preserves_orientation(self) -> None:
        """Test that copy() preserves _orientation field."""
        box = SmartSolid(Box(100, 50, 30))
        box.move(10, 20, 30)
        box.orient((45, 30, 60))

        box_copy = box.copy()

        assertVectorAlmostEqual(self, box_copy.origin, box.origin)
        assertVectorAlmostEqual(self, box_copy._orientation, box._orientation)

    def test_bed_orientation_default_none(self) -> None:
        """Test that bed_orientation is None by default."""
        box = SmartSolid(Box(10, 10, 10))
        self.assertIsNone(box.bed_orientation)

    def test_copy_preserves_bed_orientation(self) -> None:
        """Test that copy() preserves bed_orientation field."""
        box = SmartSolid(Box(10, 20, 30))
        box.bed_orientation = (90, 0, 0)

        box_copy = box.copy()

        self.assertEqual(box_copy.bed_orientation, (90, 0, 0))

    def test_combined_transformations(self) -> None:
        """Test origin tracking through multiple transformations."""
        box = SmartSolid(Box(100, 50, 30))

        # Move first
        box.move(10, 0, 0)  # origin: (10, 0, 0)

        # Then rotate 90° around Z
        box.rotate(Axis.Z, 90)  # origin: (0, 10, 0)

        # Then move again
        box.move(5, 5, 5)  # origin: (5, 15, 5)

        assertVectorAlmostEqual(self, box.origin, (5, 15, 5))

    def test_rotate_multi_tracks_origin(self) -> None:
        """Test that rotate_multi() (which uses orient()) tracks origin correctly."""
        box = SmartSolid(Box(100, 50, 30))
        box.move(10, 0, 0)  # origin at (10, 0, 0)

        box.rotate_multi((0, 0, 90))  # Rotate 90° around Z

        # After 90° Z rotation, (10, 0, 0) -> (0, 10, 0)
        assertVectorAlmostEqual(self, box.origin, (0, 10, 0))


class TestSmartSolidMoveWithPlane(unittest.TestCase):
    """Tests for move operations with plane parameter."""

    def test_move_without_plane_uses_global_coordinates(self) -> None:
        """Test that move() without plane uses global XYZ coordinates."""
        box = SmartSolid(Box(10, 10, 10))
        box.move(5, 10, 15)

        assertVectorAlmostEqual(self, box.origin, (5, 10, 15))
        # Box is centered at origin, so after move center is at (5, 10, 15)
        assertVectorAlmostEqual(self, box.solid.center(), (5, 10, 15))

    def test_move_with_xy_plane_same_as_global(self) -> None:
        """Test that move() with Plane.XY is same as global coordinates."""
        box1 = SmartSolid(Box(10, 10, 10))
        box2 = SmartSolid(Box(10, 10, 10))

        box1.move(5, 10, 15)
        box2.move(5, 10, 15, plane=Plane.XY)

        assertVectorAlmostEqual(self, box1.origin, box2.origin)

    def test_move_with_xz_plane(self) -> None:
        """Test that move() with Plane.XZ uses XZ plane coordinates."""
        box = SmartSolid(Box(10, 10, 10))
        # In Plane.XZ: x_dir=(1,0,0), y_dir=(0,0,1), z_dir=(0,-1,0)
        # So move(5, 10, 15) in XZ plane = 5*x_dir + 10*y_dir + 15*z_dir
        # = 5*(1,0,0) + 10*(0,0,1) + 15*(0,-1,0) = (5, -15, 10)
        box.move(5, 10, 15, plane=Plane.XZ)

        assertVectorAlmostEqual(self, box.origin, (5, -15, 10))

    def test_move_with_yz_plane(self) -> None:
        """Test that move() with Plane.YZ uses YZ plane coordinates."""
        box = SmartSolid(Box(10, 10, 10))
        # In Plane.YZ: x_dir=(0,1,0), y_dir=(0,0,1), z_dir=(1,0,0)
        # So move(5, 10, 15) in YZ plane = 5*x_dir + 10*y_dir + 15*z_dir
        # = 5*(0,1,0) + 10*(0,0,1) + 15*(1,0,0) = (15, 5, 10)
        box.move(5, 10, 15, plane=Plane.YZ)

        assertVectorAlmostEqual(self, box.origin, (15, 5, 10))

    def test_move_x_with_plane(self) -> None:
        """Test that move_x() with plane uses plane's x direction."""
        box = SmartSolid(Box(10, 10, 10))
        box.move_x(10, plane=Plane.YZ)

        # In Plane.YZ: x_dir=(0,1,0), so move_x(10) = (0, 10, 0)
        assertVectorAlmostEqual(self, box.origin, (0, 10, 0))

    def test_move_y_with_plane(self) -> None:
        """Test that move_y() with plane uses plane's y direction."""
        box = SmartSolid(Box(10, 10, 10))
        box.move_y(10, plane=Plane.XZ)

        # In Plane.XZ: y_dir=(0,0,1), so move_y(10) = (0, 0, 10)
        assertVectorAlmostEqual(self, box.origin, (0, 0, 10))

    def test_move_z_with_plane(self) -> None:
        """Test that move_z() with plane uses plane's z direction."""
        box = SmartSolid(Box(10, 10, 10))
        box.move_z(10, plane=Plane.XZ)

        # In Plane.XZ: z_dir=(0,-1,0), so move_z(10) = (0, -10, 0)
        assertVectorAlmostEqual(self, box.origin, (0, -10, 0))

    def test_moved_with_plane_returns_copy(self) -> None:
        """Test that moved() with plane returns a moved copy."""
        box = SmartSolid(Box(10, 10, 10))
        moved_box = box.moved(5, 10, 15, plane=Plane.XZ)

        # Original should be unchanged
        assertVectorAlmostEqual(self, box.origin, (0, 0, 0))
        # Copy should be moved: (5, -15, 10) in XZ plane
        assertVectorAlmostEqual(self, moved_box.origin, (5, -15, 10))

    def test_move_with_custom_plane(self) -> None:
        """Test move() with a custom rotated plane."""
        box = SmartSolid(Box(10, 10, 10))
        # Create a plane rotated 90 degrees around Z
        rotated_plane = Plane.XY.rotated((0, 0, 90))
        # After 90° Z rotation: x_dir=(0,1,0), y_dir=(-1,0,0), z_dir=(0,0,1)
        # So move(10, 0, 0) in rotated plane = 10*(0,1,0) = (0, 10, 0)
        box.move(10, 0, 0, plane=rotated_plane)

        assertVectorAlmostEqual(self, box.origin, (0, 10, 0))

    @parameterized.expand([
        (Plane.XY,),
        (Plane.XZ,),
        (Plane.YZ,),
    ])
    def test_move_with_plane_origin_tracked(self, plane) -> None:
        """Test that origin is properly tracked with plane-relative moves."""
        box = SmartSolid(Box(10, 10, 10))
        box.move(5, 10, 15, plane=plane)

        # The solid's center should match origin (since Box starts centered at origin)
        assertVectorAlmostEqual(self, box.solid.center(), box.origin)


class TestSmartSolidCutMethods(unittest.TestCase):
    """Tests for cut_x, cut_y, cut_z methods with cut, cut_fraction, keep, and keep_fraction parameters."""

    def test_cut_x_with_cut(self) -> None:
        """Test cut_x with explicit cut."""
        box = SmartSolid(Box(20, 10, 10))
        box.cut_x(cut=5)
        self.assertAlmostEqual(box.x_size, 15, places=5)
        self.assertAlmostEqual(box.x_min, -5, places=5)
        self.assertAlmostEqual(box.x_max, 10, places=5)

    def test_cut_x_with_cut_fraction(self) -> None:
        """Test cut_x with cut_fraction parameter."""
        box = SmartSolid(Box(20, 10, 10))
        box.cut_x(cut_fraction=0.25)  # Cut 25% = 5 units
        self.assertAlmostEqual(box.x_size, 15, places=5)
        self.assertAlmostEqual(box.x_min, -5, places=5)
        self.assertAlmostEqual(box.x_max, 10, places=5)

    def test_cut_y_with_cut_fraction(self) -> None:
        """Test cut_y with cut_fraction parameter."""
        box = SmartSolid(Box(10, 20, 10))
        box.cut_y(cut_fraction=0.5)  # Cut 50% = 10 units
        self.assertAlmostEqual(box.y_size, 10, places=5)

    def test_cut_z_with_cut_fraction(self) -> None:
        """Test cut_z with cut_fraction parameter."""
        box = SmartSolid(Box(10, 10, 30))
        box.cut_z(cut_fraction=0.333333)  # Cut ~1/3 = 10 units
        self.assertAlmostEqual(box.z_size, 20, places=4)

    def test_cut_requires_parameter(self) -> None:
        """Test that cut methods require at least one parameter."""
        box = SmartSolid(Box(10, 10, 10))
        with self.assertRaises(ValueError):
            box.cut_x()

    def test_cut_rejects_multiple_parameters(self) -> None:
        """Test that cut methods reject multiple parameters."""
        box = SmartSolid(Box(10, 10, 10))
        with self.assertRaises(ValueError):
            box.cut_x(cut=5, cut_fraction=0.5)

    @parameterized.expand([
        (0.0,),
        (1.0,),
        (-1.0,),
        (1.5,),
        (-1.5,),
    ])
    def test_cut_validates_cut_fraction_range(self, invalid_fraction) -> None:
        """Test that cut_fraction must satisfy -1 < f < 0 or 0 < f < 1."""
        box = SmartSolid(Box(10, 10, 10))
        with self.assertRaises(ValueError):
            box.cut_x(cut_fraction=invalid_fraction)

    def test_cut_x_with_negative_cut_fraction(self) -> None:
        """Test cut_x with negative cut_fraction cuts from the other side."""
        box = SmartSolid(Box(20, 10, 10))
        box.cut_x(cut_fraction=-0.25)  # Cut 25% from the other side
        self.assertAlmostEqual(box.x_size, 15, places=5)
        self.assertAlmostEqual(box.x_min, -10, places=5)
        self.assertAlmostEqual(box.x_max, 5, places=5)

    def test_cut_x_negative_cut(self) -> None:
        """Test cut_x with negative cut value cuts from the other side."""
        box = SmartSolid(Box(20, 10, 10))
        box.cut_x(cut=-5)
        self.assertAlmostEqual(box.x_size, 15, places=5)
        self.assertAlmostEqual(box.x_min, -10, places=5)
        self.assertAlmostEqual(box.x_max, 5, places=5)

    def test_cut_x_with_keep(self) -> None:
        """Test cut_x with keep parameter."""
        box = SmartSolid(Box(20, 10, 10))
        box.cut_x(keep=15)  # Keep 15 on positive side
        self.assertAlmostEqual(box.x_size, 15, places=5)
        self.assertAlmostEqual(box.x_min, -5, places=5)
        self.assertAlmostEqual(box.x_max, 10, places=5)

    def test_cut_z_with_keep(self) -> None:
        """Test cut_z with keep parameter."""
        box = SmartSolid(Box(10, 10, 30))
        box.cut_z(keep=20)  # Keep 20 from positive side
        self.assertAlmostEqual(box.z_size, 20, places=5)

    def test_cut_x_with_negative_keep(self) -> None:
        """Test cut_x with negative keep keeps from the other side."""
        box = SmartSolid(Box(20, 10, 10))
        box.cut_x(keep=-15)  # Keep 15 on negative side
        self.assertAlmostEqual(box.x_size, 15, places=5)
        self.assertAlmostEqual(box.x_min, -10, places=5)
        self.assertAlmostEqual(box.x_max, 5, places=5)

    def test_cut_z_with_keep_fraction(self) -> None:
        """Test cut_z with keep_fraction parameter."""
        box = SmartSolid(Box(10, 10, 30))
        box.cut_z(keep_fraction=2/3)  # Keep 2/3 = 20 units
        self.assertAlmostEqual(box.z_size, 20, places=4)
        self.assertAlmostEqual(box.z_min, -5, places=4)
        self.assertAlmostEqual(box.z_max, 15, places=4)

    def test_cut_x_with_negative_keep_fraction(self) -> None:
        """Test cut_x with negative keep_fraction keeps from the other side."""
        box = SmartSolid(Box(20, 10, 10))
        box.cut_x(keep_fraction=-0.75)  # Keep 75% on negative side
        self.assertAlmostEqual(box.x_size, 15, places=5)
        self.assertAlmostEqual(box.x_min, -10, places=5)
        self.assertAlmostEqual(box.x_max, 5, places=5)

    @parameterized.expand([
        (0.0,),
        (1.0,),
        (-1.0,),
        (1.5,),
        (-1.5,),
    ])
    def test_cut_validates_keep_fraction_range(self, invalid_fraction) -> None:
        """Test that keep_fraction must satisfy -1 < f < 0 or 0 < f < 1."""
        box = SmartSolid(Box(10, 10, 10))
        with self.assertRaises(ValueError):
            box.cut_x(keep_fraction=invalid_fraction)

    def test_cut_rejects_cut_and_keep(self) -> None:
        """Test that cut methods reject cut + keep combination."""
        box = SmartSolid(Box(10, 10, 10))
        with self.assertRaises(ValueError):
            box.cut_x(cut=5, keep=5)

    def test_cut_rejects_fraction_and_keep_fraction(self) -> None:
        """Test that cut methods reject cut_fraction + keep_fraction combination."""
        box = SmartSolid(Box(10, 10, 10))
        with self.assertRaises(ValueError):
            box.cut_x(cut_fraction=0.5, keep_fraction=0.5)


class TestSmartSolidRotateConvenience(unittest.TestCase):
    """Tests for rotate_x(), rotate_y(), rotate_z() convenience methods."""

    @parameterized.expand([
        (Axis.X, "rotate_x", 45),
        (Axis.X, "rotate_x", 90),
        (Axis.Y, "rotate_y", 45),
        (Axis.Y, "rotate_y", 90),
        (Axis.Z, "rotate_z", 45),
        (Axis.Z, "rotate_z", 90),
    ])
    def test_convenience_matches_rotate(self, axis, method_name, angle) -> None:
        """Test that rotate_x/y/z() produce same result as rotate(Axis, angle)."""
        box1 = SmartSolid(Box(10, 20, 30))
        box1.move(5, 10, 15)
        box2 = SmartSolid(Box(10, 20, 30))
        box2.move(5, 10, 15)

        box1.rotate(axis, angle)
        getattr(box2, method_name)(angle)

        assertVectorAlmostEqual(self, box1.origin, box2.origin)
        assertVectorAlmostEqual(self, box1._orientation, box2._orientation)
        assertVectorAlmostEqual(self, box1.bound_box.size, box2.bound_box.size)


class TestSmartSolidRotatedCopy(unittest.TestCase):
    """Tests for rotated() returning a copy without modifying original."""

    def test_rotated_returns_copy(self) -> None:
        """Test that rotated() returns a new SmartSolid and leaves original unchanged."""
        box = SmartSolid(Box(10, 20, 30))
        box.move(5, 0, 0)
        original_origin = Vector(box.origin.X, box.origin.Y, box.origin.Z)
        original_orientation = Vector(box._orientation.X, box._orientation.Y, box._orientation.Z)

        copy = box.rotated(Axis.Z, 90)

        # Original unchanged
        assertVectorAlmostEqual(self, box.origin, original_origin)
        assertVectorAlmostEqual(self, box._orientation, original_orientation)
        # Copy is rotated
        assertVectorAlmostEqual(self, copy.origin, (0, 5, 0))
        self.assertNotAlmostEqual(copy._orientation.Z, 0, places=1)

    def test_oriented_returns_copy(self) -> None:
        """Test that oriented() returns a new SmartSolid and leaves original unchanged."""
        box = SmartSolid(Box(10, 20, 30))
        box.move(10, 0, 0)
        original_origin = Vector(box.origin.X, box.origin.Y, box.origin.Z)

        copy = box.oriented((0, 0, 90))

        # Original unchanged
        assertVectorAlmostEqual(self, box.origin, original_origin)
        assertVectorAlmostEqual(self, box._orientation, (0, 0, 0))
        # Copy is oriented — orient doesn't move position
        assertVectorAlmostEqual(self, copy.origin, (10, 0, 0))
        assertVectorAlmostEqual(self, copy._orientation, (0, 0, 90))


class TestSmartSolidConsecutiveRotations(unittest.TestCase):
    """Tests for consecutive rotate() calls verifying cumulative behavior."""

    def test_two_rotations_equal_single(self) -> None:
        """Test that rotate(Z, 45) + rotate(Z, 45) equals rotate(Z, 90)."""
        box1 = SmartSolid(Box(10, 20, 30))
        box1.move(10, 0, 0)
        box1.rotate(Axis.Z, 45)
        box1.rotate(Axis.Z, 45)

        box2 = SmartSolid(Box(10, 20, 30))
        box2.move(10, 0, 0)
        box2.rotate(Axis.Z, 90)

        assertVectorAlmostEqual(self, box1.origin, box2.origin)
        assertVectorAlmostEqual(self, box1.bound_box.size, box2.bound_box.size)

    def test_three_rotations_different_axes(self) -> None:
        """Test consecutive rotations around different axes."""
        box = SmartSolid(Box(10, 20, 30))
        box.move(10, 0, 0)

        box.rotate(Axis.Z, 90)
        # origin: (10,0,0) -> (0,10,0)
        assertVectorAlmostEqual(self, box.origin, (0, 10, 0))

        box.rotate(Axis.X, 90)
        # origin: (0,10,0) -> (0,0,10)
        assertVectorAlmostEqual(self, box.origin, (0, 0, 10))

    def test_four_90_degree_rotations_return_to_original(self) -> None:
        """Test that 4x rotate(Z, 90) returns origin to original position."""
        box = SmartSolid(Box(10, 20, 30))
        box.move(7, 3, 5)
        original_origin = Vector(box.origin.X, box.origin.Y, box.origin.Z)

        for _ in range(4):
            box.rotate(Axis.Z, 90)

        assertVectorAlmostEqual(self, box.origin, original_origin)

    def test_360_rotation_returns_to_original(self) -> None:
        """Test that a single 360° rotation returns to original state."""
        box = SmartSolid(Box(10, 20, 30))
        box.move(7, 3, 5)
        original_origin = Vector(box.origin.X, box.origin.Y, box.origin.Z)
        original_size = Vector(box.bound_box.size.X, box.bound_box.size.Y, box.bound_box.size.Z)

        box.rotate(Axis.Z, 360)

        assertVectorAlmostEqual(self, box.origin, original_origin)
        assertVectorAlmostEqual(self, box.bound_box.size, original_size)


class TestSmartSolidMixedOperations(unittest.TestCase):
    """Tests for combining rotate(), orient(), and move() in various orders."""

    def test_rotate_move_rotate(self) -> None:
        """Test rotate() + move() + rotate() sequence."""
        box = SmartSolid(Box(10, 20, 30))
        box.move(10, 0, 0)  # origin: (10, 0, 0)

        box.rotate(Axis.Z, 90)  # origin: (0, 10, 0)
        assertVectorAlmostEqual(self, box.origin, (0, 10, 0))

        box.move(5, 0, 0)  # origin: (5, 10, 0)
        assertVectorAlmostEqual(self, box.origin, (5, 10, 0))

        box.rotate(Axis.Z, 90)  # origin: (5,10,0) -> (-10, 5, 0)
        assertVectorAlmostEqual(self, box.origin, (-10, 5, 0))

    def test_orient_move_orient(self) -> None:
        """Test orient() + move() + orient() — orient never changes position."""
        box = SmartSolid(Box(10, 20, 30))
        box.move(10, 0, 0)

        box.orient((0, 0, 90))  # origin stays at (10, 0, 0)
        assertVectorAlmostEqual(self, box.origin, (10, 0, 0))

        box.move(5, 0, 0)  # origin: (15, 0, 0)
        assertVectorAlmostEqual(self, box.origin, (15, 0, 0))

        # orient is absolute — replaces rotation, but never changes position
        box.orient((0, 0, 180))  # origin stays at (15, 0, 0)
        assertVectorAlmostEqual(self, box.origin, (15, 0, 0))

    def test_rotate_then_orient_replaces(self) -> None:
        """Test that orient() after rotate() replaces rotation but doesn't change position."""
        box = SmartSolid(Box(10, 20, 30))
        box.move(10, 0, 0)

        box.rotate(Axis.Z, 45)
        # rotate() moves position: (10,0,0) rotated 45° around Z
        import math
        expected_x = 10 * math.cos(math.radians(45))
        expected_y = 10 * math.sin(math.radians(45))
        assertVectorAlmostEqual(self, box.origin, (expected_x, expected_y, 0))

        box.orient((0, 0, 90))
        # orient() replaces rotation but does NOT change position
        assertVectorAlmostEqual(self, box.origin, (expected_x, expected_y, 0))

    def test_orient_then_rotate_adds(self) -> None:
        """Test that rotate() after orient() adds incrementally."""
        box1 = SmartSolid(Box(10, 20, 30))
        box1.move(10, 0, 0)
        box1.orient((0, 0, 45))  # origin stays at (10, 0, 0) — orient doesn't move
        box1.rotate(Axis.Z, 45)  # rotate moves position: (10,0,0) rotated 45° around Z

        box2 = SmartSolid(Box(10, 20, 30))
        box2.move(10, 0, 0)
        box2.rotate(Axis.Z, 45)  # same position effect

        assertVectorAlmostEqual(self, box1.origin, box2.origin)


class TestSmartSolidArbitraryAxis(unittest.TestCase):
    """Tests for rotate() with non-standard axes."""

    def test_arbitrary_axis_rotation_bounds(self) -> None:
        """Test that rotation around an arbitrary axis changes bounds correctly."""
        box = SmartSolid(Box(10, 20, 30))

        # Rotate 90° around XY diagonal (1,1,0)
        diagonal_axis = Axis((0, 0, 0), (1, 1, 0))
        box.rotate(diagonal_axis, 180)

        # 180° around (1,1,0) swaps X↔Y and flips Z
        # Box(10,20,30) -> Box(20,10,30)
        bbox = box.bound_box
        self.assertAlmostEqual(bbox.size.X, 20, places=1)
        self.assertAlmostEqual(bbox.size.Y, 10, places=1)
        self.assertAlmostEqual(bbox.size.Z, 30, places=1)

    def test_arbitrary_axis_rotation_origin(self) -> None:
        """Test that origin tracks correctly through arbitrary axis rotation."""
        box = SmartSolid(Box(10, 20, 30))
        box.move(10, 0, 0)

        # Rotate 90° around Z axis using standard Axis
        box1 = box.copy()
        box1.rotate(Axis.Z, 90)

        # Same rotation using custom Axis equivalent
        box2 = box.copy()
        box2.rotate(Axis((0, 0, 0), (0, 0, 1)), 90)

        assertVectorAlmostEqual(self, box1.origin, box2.origin)

    def test_arbitrary_axis_360_returns_to_original(self) -> None:
        """Test 360° rotation around arbitrary axis returns to original."""
        box = SmartSolid(Box(10, 20, 30))
        box.move(7, 3, 5)
        original_origin = Vector(box.origin.X, box.origin.Y, box.origin.Z)

        diagonal_axis = Axis((0, 0, 0), (1, 1, 1))
        box.rotate(diagonal_axis, 360)

        assertVectorAlmostEqual(self, box.origin, original_origin)


class TestSmartSolidOrientationTracking(unittest.TestCase):
    """Tests verifying _orientation field stays in sync with solid.orientation."""

    def test_orientation_matches_after_orient(self) -> None:
        """_orientation should match solid.orientation after orient()."""
        box = SmartSolid(Box(10, 20, 30))
        box.orient((45, 30, 60))
        assertVectorAlmostEqual(self, box._orientation, box.solid.orientation)

    def test_orientation_matches_after_rotate(self) -> None:
        """_orientation should match solid.orientation after rotate()."""
        box = SmartSolid(Box(10, 20, 30))
        box.rotate(Axis.Z, 90)
        assertVectorAlmostEqual(self, box._orientation, box.solid.orientation)

    def test_orientation_matches_after_consecutive_rotates(self) -> None:
        """_orientation should match solid.orientation after multiple rotate() calls."""
        box = SmartSolid(Box(10, 20, 30))
        box.rotate(Axis.Z, 45)
        assertVectorAlmostEqual(self, box._orientation, box.solid.orientation)
        box.rotate(Axis.X, 30)
        assertVectorAlmostEqual(self, box._orientation, box.solid.orientation)
        box.rotate(Axis.Y, 60)
        assertVectorAlmostEqual(self, box._orientation, box.solid.orientation)

    def test_orientation_matches_after_rotate_then_orient(self) -> None:
        """_orientation should match solid.orientation when mixing rotate and orient."""
        box = SmartSolid(Box(10, 20, 30))
        box.rotate(Axis.Z, 45)
        assertVectorAlmostEqual(self, box._orientation, box.solid.orientation)
        box.orient((90, 0, 0))
        assertVectorAlmostEqual(self, box._orientation, box.solid.orientation)

    def test_orientation_zero_initially(self) -> None:
        """_orientation should be (0,0,0) for a fresh solid."""
        box = SmartSolid(Box(10, 20, 30))
        assertVectorAlmostEqual(self, box._orientation, (0, 0, 0))

    def test_orientation_matches_after_rotate_multi(self) -> None:
        """_orientation should match solid.orientation after rotate_multi()."""
        box = SmartSolid(Box(10, 20, 30))
        box.rotate_multi((45, 30, 60))
        assertVectorAlmostEqual(self, box._orientation, box.solid.orientation)


def _offset_axis(axis: Axis) -> Axis:
    """Axis with the same direction as `axis` but a sub-tolerance positional
    offset — bypasses the `axis in (Axis.X/Y/Z)` shortcut in `SmartSolid.rotate`
    while staying on the same axis line within floating-point precision."""
    if axis == Axis.Z:
        return Axis((1e-9, 0, 0), (0, 0, 1))
    if axis == Axis.X:
        return Axis((0, 1e-9, 0), (1, 0, 0))
    return Axis((1e-9, 0, 0), (0, 1, 0))  # Axis.Y


class TestSmartSolidRotateAroundWorldOrigin(unittest.TestCase):
    """Cardinal-axis rotation (`Axis.X/Y/Z`) must always pivot at the world axis
    line, regardless of where `self.solid.location.position` ended up. The fast
    path goes through `orient()` (which rotates around the shape's
    location.position) and then applies a compensating translation
    `R(θ)·pivot − pivot` to re-anchor the result to the world axis.

    Strategy:
    - For symmetric single boxes, directly verify `bound_box.center()` maps to
      `R(θ)·original_center` (AABB stays centred on the rotated centroid).
    - For asymmetric / fused / pencil-built shapes, compare the cardinal-axis
      result against the OCC branch (an off-axis axis at the same line via
      `_offset_axis`) — they apply the same rotation through different code
      paths and must produce identical geometry.
    """

    # ----- Direct analytic check: single box is symmetric around its centre -----

    @parameterized.expand([
        (Axis.Z, 30), (Axis.Z, 60), (Axis.Z, 90), (Axis.Z, 180), (Axis.Z, -120),
        (Axis.X, 45), (Axis.X, 90),
        (Axis.Y, 60), (Axis.Y, 180),
    ])
    def test_translated_box_pivots_at_world_origin(self, axis, angle) -> None:
        box = SmartSolid(Box(4, 4, 4))
        box.move(20, 5, 3)
        c_before = box.bound_box.center()

        box.rotate(axis, angle)

        expected = rotate_vector(c_before, axis, angle)
        assertVectorAlmostEqual(self, box.bound_box.center(), expected)

    # ----- Cardinal vs OCC parity: works for any geometry, any angle -----

    @parameterized.expand([
        (Axis.Z, 30), (Axis.Z, 60), (Axis.Z, 120),
        (Axis.X, 45), (Axis.X, 90),
        (Axis.Y, 60), (Axis.Y, 90),
    ])
    def test_after_fuse_matches_offaxis(self, axis, angle) -> None:
        """Regression: `fuse()` resets `location.position` to `(0, 0, 0)` while
        `self.origin` keeps its tracked value. Old code used `self.origin` as
        the rotation pivot and translated wrong; the cardinal path must produce
        identical geometry to the OCC branch around the same axis."""
        a1 = SmartSolid(Box(4, 4, 4))
        a1.move(20, 5, 3)
        a1.fuse(SmartSolid(Box(2, 2, 2)).move(24, 5, 3))
        a2 = a1.copy()

        a1.rotate(axis, angle)
        a2.rotate(_offset_axis(axis), angle)

        assertVectorAlmostEqual(self, a1.bound_box.min, a2.bound_box.min)
        assertVectorAlmostEqual(self, a1.bound_box.max, a2.bound_box.max)

    @parameterized.expand([(30,), (60,), (90,), (120,), (180,), (-60,)])
    def test_pencil_built_matches_offaxis(self, angle) -> None:
        """Pencil-built solids carry a non-trivial `location.position` from
        face/extrude construction. The dispenser-bottle-mount polar-pattern
        bug surfaced here: cardinal Z rotation must match the OCC branch."""
        a1 = _build_pencil_cutter()
        a2 = a1.copy()

        a1.rotate(Axis.Z, angle)
        a2.rotate(_offset_axis(Axis.Z), angle)

        assertVectorAlmostEqual(self, a1.bound_box.min, a2.bound_box.min)
        assertVectorAlmostEqual(self, a1.bound_box.max, a2.bound_box.max)

    @parameterized.expand([(0,), (60,), (120,), (180,), (240,), (300,)])
    def test_polar_pattern_via_rotated_z(self, angle) -> None:
        """6-fold polar pattern via `rotated_z(i * 60)` on a pencil-built
        cutter — regression for the dispenser-bottle-mount failure mode where
        rotated copies landed at the wrong radii / angles."""
        cutter = _build_pencil_cutter()

        cardinal = cutter.rotated_z(angle)
        explicit = cutter.rotated(_offset_axis(Axis.Z), angle)

        assertVectorAlmostEqual(self, cardinal.bound_box.min, explicit.bound_box.min)
        assertVectorAlmostEqual(self, cardinal.bound_box.max, explicit.bound_box.max)

    # ----- Origin tracking -----

    def test_after_fuse_resets_origin(self) -> None:
        """`fuse()` produces a fresh OCC shape with location.position == (0, 0, 0);
        the invariant requires self.origin to match, so it resets — the
        pre-fuse anchor is not preserved. Subsequent rotate around Z then
        rotates `(0, 0, 0)` to `(0, 0, 0)`."""
        a = SmartSolid(Box(4, 4, 4))
        a.move(20, 5, 0)
        b = SmartSolid(Box(2, 2, 2))
        b.move(24, 5, 0)
        a.fuse(b)

        assertVectorAlmostEqual(self, a.origin, (0, 0, 0))

        a.rotate(Axis.Z, 90)

        assertVectorAlmostEqual(self, a.origin, (0, 0, 0))

    def test_rotate_fuse_rotate_zero_does_not_double_rotate(self) -> None:
        """Regression: pre-fix, `self._orientation` lingered through `fuse()`
        even though the fused BRep already incorporated the rotation. A
        subsequent `rotate_z(0)` then re-applied the stale orientation,
        rotating the world geometry a second time. The fix is to reset
        `self._orientation` to identity in the same place we reset
        `self.origin` (i.e. in `fuse`/`cut`/`intersect`/`mirror`/`scale`/`pad`)."""
        a = SmartSolid(Box(4, 4, 4))
        a.move(20, 0, 0)
        a.rotate_z(90)
        # Overlapping box so OCC fuse returns a single Shape (not ShapeList).
        a.fuse(SmartSolid(Box(2, 2, 2)).move(0, 20, 0))
        bbox_before = (a.bound_box.min.Y, a.bound_box.max.Y)

        a.rotate_z(0)  # semantically a no-op
        bbox_after = (a.bound_box.min.Y, a.bound_box.max.Y)

        self.assertAlmostEqual(bbox_before[0], bbox_after[0], places=4)
        self.assertAlmostEqual(bbox_before[1], bbox_after[1], places=4)


def _build_pencil_cutter() -> SmartSolid:
    """Match the iris / dispenser-bottle-mount decorative outer-edge cutter
    silhouette: an arc-and-teardrop face mirrored across Y, then extruded.
    Asymmetric enough to expose the AABB-vs-centroid mismatch."""
    pencil = Pencil()
    pencil.arc_with_radius(30, 180, 15)
    pencil.jump_to((0, -10))
    return pencil.extrude_mirrored_y(2)


class TestSmartSolidLocationInvariant(unittest.TestCase):
    """`SmartSolid` maintains the invariant `self.origin == self.solid.location.position`
    for single-shape solids. These tests pin down that the invariant holds after
    every operation that could break it — construction (including raw `Box` whose
    OCC default anchors at the `-X/-Y/-Z` corner), `move`, `rotate`, `mirror`,
    `scale`, `fuse`, `cut`, `intersect`. `_reanchor()` in `__init__` and the
    OCC-op wrappers re-syncs `location.position` to `self.origin` without
    moving world geometry."""

    def _assert_invariant(self, solid: SmartSolid) -> None:
        if solid.solid is None or isinstance(solid.solid, ShapeList):
            return
        assertVectorAlmostEqual(self, solid.origin, solid.solid.location.position)

    def test_invariant_after_raw_box_init(self) -> None:
        """Raw `Box(L, W, H)` defaults to a corner anchor; `__init__` must
        re-sync so the invariant holds from the start."""
        self._assert_invariant(SmartSolid(Box(4, 4, 4)))

    def test_invariant_after_smartbox_init(self) -> None:
        self._assert_invariant(SmartBox(4, 4, 4))

    def test_invariant_after_pencil_built(self) -> None:
        self._assert_invariant(_build_pencil_cutter())

    def test_invariant_after_move(self) -> None:
        s = SmartSolid(Box(4, 4, 4)).move(20, 5, 3)
        self._assert_invariant(s)

    @parameterized.expand([(Axis.Z, 30), (Axis.X, 90), (Axis.Y, 45), (Axis.Z, 180)])
    def test_invariant_after_rotate(self, axis, angle) -> None:
        s = SmartSolid(Box(4, 4, 4)).move(20, 5, 3)
        s.rotate(axis, angle)
        self._assert_invariant(s)

    def test_invariant_after_mirror(self) -> None:
        s = SmartSolid(Box(4, 4, 4)).move(10, 5, 0)
        s.mirror(Plane.XZ)
        self._assert_invariant(s)

    def test_invariant_after_scale(self) -> None:
        s = SmartSolid(Box(4, 4, 4)).move(10, 5, 3)
        s.scale(2, 2, 2)
        self._assert_invariant(s)

    def test_invariant_after_fuse(self) -> None:
        a = SmartSolid(Box(4, 4, 4)).move(20, 5, 3)
        b = SmartSolid(Box(4, 4, 4)).move(22, 5, 3)  # overlapping → single Shape result
        a.fuse(b)
        self._assert_invariant(a)

    def test_invariant_after_cut(self) -> None:
        a = SmartSolid(Box(10, 10, 10)).move(20, 5, 3)
        b = SmartSolid(Box(2, 2, 2)).move(20, 5, 3)
        a.cut(b)
        self._assert_invariant(a)


if __name__ == '__main__':
    unittest.main()
