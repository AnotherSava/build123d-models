import unittest

from parameterized import parameterized

from sava.common.common import flatten


class TestFlatten(unittest.TestCase):

    @parameterized.expand([
        # Non-iterable inputs
        (5, [5]),
        (42, [42]),
        (3.14, [3.14]),
        
        # String inputs (treated as a single item)
        ("hello", ["hello"]),
        ("", [""]),
        
        # Simple lists
        ([1, 2, 3], [1, 2, 3]),
        ([1], [1]),
        ([], []),
        
        # Nested lists
        ([1, [2, 3], 4], [1, 2, 3, 4]),
        ([[1, 2], [3, 4]], [1, 2, 3, 4]),
        ([1, [2, [3, [4]]]], [1, 2, 3, 4]),
        
        # Mixed nesting
        ([1, [2, 3], 4, [5, [6, 7]]], [1, 2, 3, 4, 5, 6, 7]),
        ([[], [1], [[2]]], [1, 2]),
        
        # Tuples (also iterable)
        ((1, 2, 3), [1, 2, 3]),
        ((1, (2, 3), 4), [1, 2, 3, 4]),
        
        # Mixed list and tuple
        ([1, (2, 3), [4, 5]], [1, 2, 3, 4, 5]),
    ])
    def test_flatten(self, input_data, expected):
        """Test flatten with various inputs"""
        result = list(flatten(input_data))
        self.assertEqual(result, expected)


if __name__ == '__main__':
    unittest.main()
