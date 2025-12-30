import unittest

from parameterized import parameterized

from sava.common.advanced_math import advanced_mod


class TestAdvancedMod(unittest.TestCase):

    @parameterized.expand([
        # No constraints - should return x as-is
        (7.5, 10, None, None, 7.5),
        (23.7, 5, None, None, 23.7),
        (-3.2, 4, None, None, -3.2),

        # Only min_value constraint - x already >= min_value
        (7, 5, 5, None, 7),
        (12.3, 10, 10, None, 12.3),

        # Only min_value constraint - x < min_value, need to adjust upward
        (3, 5, 10, None, 13),  # 13%5=3
        (2.5, 10, 20, None, 22.5),  # 22.5%10=2.5

        # Only max_value constraint - x already < max_value
        (7, 5, None, 10, 7),

        # Only max_value constraint - x >= max_value, need to adjust downward
        (23, 5, None, 20, 18),  # 18%5=3
        (47.5, 10, None, 40, 37.5),  # 37.5%10=7.5

        # Both constraints - x is already within [min_value, max_value)
        (15, 10, 10, 20, 15),
        (12.7, 5, 10, 20, 12.7),

        # Both constraints - x < min_value
        (3, 5, 10, 20, 13),  # 13%5=3
        (2.5, 10, 20, 40, 22.5),  # 22.5%10=2.5

        # Both constraints - x >= max_value
        (27, 5, 10, 20, 17),  # 17%5=2
        (52.7, 10, 20, 40, 32.7),  # 32.7%10=2.7

        # Negative values
        (-3, 5, 0, None, 2),  # -3%5=2
        (-7.5, 10, 0, 20, 2.5),  # -7.5%10=2.5

        # Edge cases at boundaries
        (10, 5, 10, 20, 10),
        (20, 5, 10, 20, 15),  # x at max_value, adjust down

        # Angle normalization
        (326.60151153201275, 360, -180, 180, -33.39848846798725),
    ])
    def test_advanced_mod(self, x, div, min_value, max_value, expected):
        """Test advanced_mod with various inputs"""
        result = advanced_mod(x, div, min_value=min_value, max_value=max_value)
        if isinstance(expected, float):
            self.assertAlmostEqual(result, expected, places=7)
        else:
            self.assertEqual(result, expected)
        # Verify modulo is preserved
        self.assertAlmostEqual(result % div, x % div, places=7)

    @parameterized.expand([
        # Impossible constraints
        (4, 5, 0, 3),  # range [0,3), div=5, x=4 -> mod=4, no value in range has mod 4
        (5, 10, 10, 12),  # range [10,12), div=10, x=5 -> mod=5, no value in range has mod 5
    ])
    def test_advanced_mod_impossible(self, x, div, min_value, max_value):
        """Test advanced_mod with impossible constraints"""
        with self.assertRaises(ValueError):
            advanced_mod(x, div, min_value=min_value, max_value=max_value)


if __name__ == '__main__':
    unittest.main()
