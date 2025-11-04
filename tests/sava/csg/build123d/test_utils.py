"""Common test utilities for build123d tests."""

from build123d import Vector, VectorLike


# Fixed precision for all vector comparisons
VECTOR_PRECISION_PLACES = 5


def assertVectorAlmostEqual(test_case, vector1: VectorLike, vector2: VectorLike) -> None:
    """Helper function to compare two vectors with fixed precision.
    
    Args:
        test_case: The test case instance (for accessing assertAlmostEqual)
        vector1: First vector to compare (can be Vector, tuple, or list)
        vector2: Second vector to compare (can be Vector, tuple, or list)
    """
    v1 = Vector(vector1)
    v2 = Vector(vector2)
    test_case.assertAlmostEqual(v1.X, v2.X, places=VECTOR_PRECISION_PLACES)
    test_case.assertAlmostEqual(v1.Y, v2.Y, places=VECTOR_PRECISION_PLACES)
    test_case.assertAlmostEqual(v1.Z, v2.Z, places=VECTOR_PRECISION_PLACES)
