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


if __name__ == '__main__':
    unittest.main()
