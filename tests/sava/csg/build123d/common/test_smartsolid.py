import unittest

from build123d import Box, Sphere, Plane, Axis
from parameterized import parameterized

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
    def test_get_bound_box_standard_planes(self, plane, expected_x, expected_y, expected_z):
        """Test get_bound_box with standard planes"""
        box = SmartSolid(Box(10, 20, 30))
        bbox = box.get_bound_box(plane)
        
        assertVectorAlmostEqual(self, bbox.size, (expected_x, expected_y, expected_z))


class TestSmartSolidOrient(unittest.TestCase):

    def test_orient_default_plane(self):
        """Test orient with default XY plane"""
        box = SmartSolid(Box(10, 20, 30))
        box.orient((0, 0, 90))
        
        # After 90 degree rotation around Z, X and Y dimensions should swap
        bbox = box.bound_box
        assertVectorAlmostEqual(self, bbox.size, (20, 10, 30))

    def test_orient_xz_plane(self):
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

    def test_rotate_fixed_axes_behavior(self):
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
    def test_rotate_zero_incremental(self, plane):
        """Test that (0,0,0) rotation doesn't change orientation regardless of plane"""
        box = SmartSolid(Box(10, 20, 30))
        
        # Set some initial orientation
        initial_orientation = (45, 30, 60)
        box.rotate_multi(initial_orientation, plane)
        
        # Store the orientation after initial setup
        before_rotation = box.solid.orientation
        before_x, before_y, before_z = before_rotation.X, before_rotation.Y, before_rotation.Z
        
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
    def test_get_bounds_along_axis_standard_axes(self, axis, expected_size):
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
    def test_get_bounds_along_axis_diagonal_axes(self, axis, expected_size):
        """Test get_bounds_along_axis with diagonal axes"""
        box = SmartSolid(Box(10, 20, 30))
        min_coord, max_coord = box.get_bounds_along_axis(axis)
        
        actual_size = max_coord - min_coord
        self.assertAlmostEqual(actual_size, expected_size, places=2)  # Lower precision for diagonal calculations

    def test_get_bounds_along_axis_custom_origin(self):
        """Test get_bounds_along_axis with custom axis origin"""
        box = SmartSolid(Box(10, 20, 30))
        
        # Test with axis origin at box center
        axis_through_center = Axis((5, 10, 15), (1, 0, 0))  # X-axis through box center
        min_coord, max_coord = box.get_bounds_along_axis(axis_through_center)
        
        # Should still have the same size along X direction
        actual_size = max_coord - min_coord
        self.assertAlmostEqual(actual_size, 10.0, places=5)

    def test_get_bounds_along_axis_moved_box(self):
        """Test get_bounds_along_axis with moved box"""
        box = SmartSolid(Box(10, 20, 30))
        box.move(100, 200, 300)  # Move box far from origin
        
        min_coord, max_coord = box.get_bounds_along_axis(Axis.X)
        actual_size = max_coord - min_coord
        
        # Size should remain the same regardless of position
        self.assertAlmostEqual(actual_size, 10.0, places=5)

    def test_get_bounds_along_axis_empty_solid(self):
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
    def test_get_bounds_along_axis_sphere(self, axis, expected_diameter):
        """Test get_bounds_along_axis with sphere (radius=10)"""
        sphere = SmartSolid(Sphere(10))
        min_coord, max_coord = sphere.get_bounds_along_axis(axis)
        
        actual_diameter = max_coord - min_coord
        self.assertAlmostEqual(actual_diameter, expected_diameter, places=3)

    def test_get_bounds_along_axis_sphere_diagonal(self):
        """Test get_bounds_along_axis with sphere along diagonal axis"""
        sphere = SmartSolid(Sphere(10))
        
        # Test diagonal axis - should also give diameter 20
        diagonal_axis = Axis((0, 0, 0), (1, 1, 1))
        min_coord, max_coord = sphere.get_bounds_along_axis(diagonal_axis)
        
        actual_diameter = max_coord - min_coord
        self.assertAlmostEqual(actual_diameter, 20.0, places=3)


class TestSmartSolidShapeList(unittest.TestCase):
    """Tests for SmartSolid containing ShapeList (multiple shapes)."""

    def _create_shape_list_solid(self):
        """Create a SmartSolid containing multiple shapes (ShapeList)."""
        box1 = SmartSolid(Box(10, 10, 10))
        box2 = SmartSolid(Box(10, 10, 10))
        box2.move(20, 0, 0)
        return SmartSolid([box1, box2])

    def test_orient_shapelist_works(self):
        """Test that orient() works on ShapeList - it wraps to Compound first."""
        solid = self._create_shape_list_solid()

        solid.orient((0, 0, 90))

        # After 90 degree rotation around Z, the shape should have different bounds
        # Original: two boxes at x=0 and x=20, total x_size ~30
        # After rotation: should be ~10 in X (the width becomes the length)
        self.assertAlmostEqual(solid.x_size, 10, places=1)
        self.assertAlmostEqual(solid.y_size, 30, places=1)

    def test_rotate_shapelist_fails(self):
        """Test that rotate() fails on ShapeList - reads .orientation before wrapping."""
        solid = self._create_shape_list_solid()

        with self.assertRaises(AttributeError):
            solid.rotate_multi((0, 0, 90))

    def test_rotate_with_axis_shapelist_works(self):
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

    def test_move_tracks_origin(self):
        """Test that move() updates origin correctly."""
        box = SmartSolid(Box(100, 50, 30))
        box.move(10, 20, 30)
        assertVectorAlmostEqual(self, box.origin, (10, 20, 30))

    def test_colocate_tracks_origin(self):
        """Test that colocate() updates origin correctly."""
        b1 = SmartSolid(Box(100, 50, 30))
        b1.move(10, 20, 30)

        b2 = SmartSolid(Box(50, 50, 50))
        b2.colocate(b1)

        assertVectorAlmostEqual(self, b2.origin, (10, 20, 30))

    def test_orient_tracks_origin(self):
        """Test that orient() updates origin correctly - 90° Z rotation."""
        box = SmartSolid(Box(100, 50, 30))
        box.move(10, 0, 0)  # origin at (10, 0, 0)

        box.orient((0, 0, 90))  # Rotate 90° around Z

        # After 90° Z rotation, (10, 0, 0) -> (0, 10, 0)
        assertVectorAlmostEqual(self, box.origin, (0, 10, 0))

    def test_orient_tracks_origin_x_rotation(self):
        """Test that orient() updates origin correctly - 90° X rotation."""
        box = SmartSolid(Box(100, 50, 30))
        box.move(0, 10, 0)  # origin at (0, 10, 0)

        box.orient((90, 0, 0))  # Rotate 90° around X

        # After 90° X rotation, (0, 10, 0) -> (0, 0, 10)
        assertVectorAlmostEqual(self, box.origin, (0, 0, 10))

    def test_orient_tracks_origin_y_rotation(self):
        """Test that orient() updates origin correctly - 90° Y rotation."""
        box = SmartSolid(Box(100, 50, 30))
        box.move(10, 0, 0)  # origin at (10, 0, 0)

        box.orient((0, 90, 0))  # Rotate 90° around Y

        # After 90° Y rotation, (10, 0, 0) -> (0, 0, -10)
        assertVectorAlmostEqual(self, box.origin, (0, 0, -10))

    def test_mirror_xz_tracks_origin(self):
        """Test that mirror(Plane.XZ) updates origin correctly."""
        box = SmartSolid(Box(100, 50, 30))
        box.move(10, 5, 0)

        box.mirror(Plane.XZ)  # Mirror about Y=0 plane

        # After mirroring about XZ plane: Y becomes -Y
        assertVectorAlmostEqual(self, box.origin, (10, -5, 0))

    def test_mirror_yz_tracks_origin(self):
        """Test that mirror(Plane.YZ) updates origin correctly."""
        box = SmartSolid(Box(100, 50, 30))
        box.move(10, 5, 0)

        box.mirror(Plane.YZ)  # Mirror about X=0 plane

        # After mirroring about YZ plane: X becomes -X
        assertVectorAlmostEqual(self, box.origin, (-10, 5, 0))

    def test_scale_tracks_origin(self):
        """Test that scale() updates origin correctly."""
        box = SmartSolid(Box(100, 50, 30))
        box.move(10, 5, 3)

        box.scale(2, 2, 2)

        assertVectorAlmostEqual(self, box.origin, (20, 10, 6))

    def test_scale_non_uniform_tracks_origin(self):
        """Test that non-uniform scale() updates origin correctly."""
        box = SmartSolid(Box(100, 50, 30))
        box.move(10, 10, 10)

        box.scale(2, 3, 4)

        assertVectorAlmostEqual(self, box.origin, (20, 30, 40))

    def test_rotate_axis_tracks_origin(self):
        """Test that rotate(axis, angle) updates origin correctly."""
        box = SmartSolid(Box(100, 50, 30))
        box.move(10, 0, 0)  # origin at (10, 0, 0)

        box.rotate(Axis.Z, 90)  # Rotate 90° around Z

        # After 90° Z rotation, (10, 0, 0) -> (0, 10, 0)
        assertVectorAlmostEqual(self, box.origin, (0, 10, 0))

    def test_copy_preserves_orientation(self):
        """Test that copy() preserves _orientation field."""
        box = SmartSolid(Box(100, 50, 30))
        box.move(10, 20, 30)
        box.orient((45, 30, 60))

        box_copy = box.copy()

        assertVectorAlmostEqual(self, box_copy.origin, box.origin)
        assertVectorAlmostEqual(self, box_copy._orientation, box._orientation)

    def test_combined_transformations(self):
        """Test origin tracking through multiple transformations."""
        box = SmartSolid(Box(100, 50, 30))

        # Move first
        box.move(10, 0, 0)  # origin: (10, 0, 0)

        # Then rotate 90° around Z
        box.rotate(Axis.Z, 90)  # origin: (0, 10, 0)

        # Then move again
        box.move(5, 5, 5)  # origin: (5, 15, 5)

        assertVectorAlmostEqual(self, box.origin, (5, 15, 5))

    def test_rotate_multi_tracks_origin(self):
        """Test that rotate_multi() (which uses orient()) tracks origin correctly."""
        box = SmartSolid(Box(100, 50, 30))
        box.move(10, 0, 0)  # origin at (10, 0, 0)

        box.rotate_multi((0, 0, 90))  # Rotate 90° around Z

        # After 90° Z rotation, (10, 0, 0) -> (0, 10, 0)
        assertVectorAlmostEqual(self, box.origin, (0, 10, 0))


class TestSmartSolidMoveWithPlane(unittest.TestCase):
    """Tests for move operations with plane parameter."""

    def test_move_without_plane_uses_global_coordinates(self):
        """Test that move() without plane uses global XYZ coordinates."""
        box = SmartSolid(Box(10, 10, 10))
        box.move(5, 10, 15)

        assertVectorAlmostEqual(self, box.origin, (5, 10, 15))
        # Box is centered at origin, so after move center is at (5, 10, 15)
        assertVectorAlmostEqual(self, box.solid.center(), (5, 10, 15))

    def test_move_with_xy_plane_same_as_global(self):
        """Test that move() with Plane.XY is same as global coordinates."""
        box1 = SmartSolid(Box(10, 10, 10))
        box2 = SmartSolid(Box(10, 10, 10))

        box1.move(5, 10, 15)
        box2.move(5, 10, 15, plane=Plane.XY)

        assertVectorAlmostEqual(self, box1.origin, box2.origin)

    def test_move_with_xz_plane(self):
        """Test that move() with Plane.XZ uses XZ plane coordinates."""
        box = SmartSolid(Box(10, 10, 10))
        # In Plane.XZ: x_dir=(1,0,0), y_dir=(0,0,1), z_dir=(0,-1,0)
        # So move(5, 10, 15) in XZ plane = 5*x_dir + 10*y_dir + 15*z_dir
        # = 5*(1,0,0) + 10*(0,0,1) + 15*(0,-1,0) = (5, -15, 10)
        box.move(5, 10, 15, plane=Plane.XZ)

        assertVectorAlmostEqual(self, box.origin, (5, -15, 10))

    def test_move_with_yz_plane(self):
        """Test that move() with Plane.YZ uses YZ plane coordinates."""
        box = SmartSolid(Box(10, 10, 10))
        # In Plane.YZ: x_dir=(0,1,0), y_dir=(0,0,1), z_dir=(1,0,0)
        # So move(5, 10, 15) in YZ plane = 5*x_dir + 10*y_dir + 15*z_dir
        # = 5*(0,1,0) + 10*(0,0,1) + 15*(1,0,0) = (15, 5, 10)
        box.move(5, 10, 15, plane=Plane.YZ)

        assertVectorAlmostEqual(self, box.origin, (15, 5, 10))

    def test_move_x_with_plane(self):
        """Test that move_x() with plane uses plane's x direction."""
        box = SmartSolid(Box(10, 10, 10))
        box.move_x(10, plane=Plane.YZ)

        # In Plane.YZ: x_dir=(0,1,0), so move_x(10) = (0, 10, 0)
        assertVectorAlmostEqual(self, box.origin, (0, 10, 0))

    def test_move_y_with_plane(self):
        """Test that move_y() with plane uses plane's y direction."""
        box = SmartSolid(Box(10, 10, 10))
        box.move_y(10, plane=Plane.XZ)

        # In Plane.XZ: y_dir=(0,0,1), so move_y(10) = (0, 0, 10)
        assertVectorAlmostEqual(self, box.origin, (0, 0, 10))

    def test_move_z_with_plane(self):
        """Test that move_z() with plane uses plane's z direction."""
        box = SmartSolid(Box(10, 10, 10))
        box.move_z(10, plane=Plane.XZ)

        # In Plane.XZ: z_dir=(0,-1,0), so move_z(10) = (0, -10, 0)
        assertVectorAlmostEqual(self, box.origin, (0, -10, 0))

    def test_moved_with_plane_returns_copy(self):
        """Test that moved() with plane returns a moved copy."""
        box = SmartSolid(Box(10, 10, 10))
        moved_box = box.moved(5, 10, 15, plane=Plane.XZ)

        # Original should be unchanged
        assertVectorAlmostEqual(self, box.origin, (0, 0, 0))
        # Copy should be moved: (5, -15, 10) in XZ plane
        assertVectorAlmostEqual(self, moved_box.origin, (5, -15, 10))

    def test_move_with_custom_plane(self):
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
    def test_move_with_plane_origin_tracked(self, plane):
        """Test that origin is properly tracked with plane-relative moves."""
        box = SmartSolid(Box(10, 10, 10))
        box.move(5, 10, 15, plane=plane)

        # The solid's center should match origin (since Box starts centered at origin)
        assertVectorAlmostEqual(self, box.solid.center(), box.origin)


class TestSmartSolidCutMethods(unittest.TestCase):
    """Tests for cut_x, cut_y, cut_z methods with offset and fraction parameters."""

    def test_cut_x_with_offset(self):
        """Test cut_x with explicit offset."""
        box = SmartSolid(Box(20, 10, 10))
        box.cut_x(offset=5)
        self.assertAlmostEqual(box.x_size, 15, places=5)

    def test_cut_x_with_fraction(self):
        """Test cut_x with fraction parameter."""
        box = SmartSolid(Box(20, 10, 10))
        box.cut_x(fraction=0.25)  # Cut 25% = 5 units
        self.assertAlmostEqual(box.x_size, 15, places=5)

    def test_cut_y_with_fraction(self):
        """Test cut_y with fraction parameter."""
        box = SmartSolid(Box(10, 20, 10))
        box.cut_y(fraction=0.5)  # Cut 50% = 10 units
        self.assertAlmostEqual(box.y_size, 10, places=5)

    def test_cut_z_with_fraction(self):
        """Test cut_z with fraction parameter."""
        box = SmartSolid(Box(10, 10, 30))
        box.cut_z(fraction=0.333333)  # Cut ~1/3 = 10 units
        self.assertAlmostEqual(box.z_size, 20, places=4)

    def test_cut_requires_offset_or_fraction(self):
        """Test that cut methods require either offset or fraction."""
        box = SmartSolid(Box(10, 10, 10))
        with self.assertRaises(ValueError) as context:
            box.cut_x()
        self.assertIn("Either offset or fraction must be provided", str(context.exception))

    def test_cut_rejects_both_offset_and_fraction(self):
        """Test that cut methods reject both offset and fraction."""
        box = SmartSolid(Box(10, 10, 10))
        with self.assertRaises(ValueError) as context:
            box.cut_x(offset=5, fraction=0.5)
        self.assertIn("Only one of offset or fraction can be provided", str(context.exception))

    @parameterized.expand([
        (0.0,),
        (1.0,),
        (-1.0,),
        (1.5,),
        (-1.5,),
    ])
    def test_cut_validates_fraction_range(self, invalid_fraction):
        """Test that fraction must satisfy -1 < f < 0 or 0 < f < 1."""
        box = SmartSolid(Box(10, 10, 10))
        with self.assertRaises(ValueError) as context:
            box.cut_x(fraction=invalid_fraction)
        self.assertIn("fraction must satisfy", str(context.exception))

    def test_cut_x_with_negative_fraction(self):
        """Test cut_x with negative fraction cuts from the other side."""
        box = SmartSolid(Box(20, 10, 10))
        box.cut_x(fraction=-0.25)  # Cut 25% from the other side
        self.assertAlmostEqual(box.x_size, 15, places=5)

    def test_cut_x_negative_offset(self):
        """Test cut_x with negative offset cuts from the other side."""
        box = SmartSolid(Box(20, 10, 10))
        box.cut_x(offset=-5)
        self.assertAlmostEqual(box.x_size, 15, places=5)


if __name__ == '__main__':
    unittest.main()
