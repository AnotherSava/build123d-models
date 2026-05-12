import math
import unittest
from pathlib import Path

from sava.csg.build123d.reconstruct import reconstruct

DATA_DIR = Path(__file__).parent / 'data'
MESH_PATH = DATA_DIR / 'iris_blade.off'
EXPECTED_PATH = DATA_DIR / 'expected_iris_blade.py'


class TestIrisBladeReconstruction(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.result = reconstruct(str(MESH_PATH))

    def test_is_2d5_extrudable(self):
        self.assertTrue(self.result.is_2d5_extrudable)
        self.assertIsNone(self.result.error)

    def _assert_vector_close(self, actual, expected_xyz, places=2):
        self.assertAlmostEqual(actual.X, expected_xyz[0], places=places)
        self.assertAlmostEqual(actual.Y, expected_xyz[1], places=places)
        self.assertAlmostEqual(actual.Z, expected_xyz[2], places=places)

    def test_extrusion_axis(self):
        self._assert_vector_close(self.result.extrusion_axis, (0.683, -0.731, 0.0))

    def test_datum_frame_axes(self):
        self._assert_vector_close(self.result.z_dir, (0.683, -0.731, 0.0))
        self._assert_vector_close(self.result.y_dir, (0.0, 0.0, 1.0))
        self._assert_vector_close(self.result.x_dir, (0.731, 0.683, 0.0))

    def test_datum_contact_area(self):
        self.assertAlmostEqual(self.result.datum_contact_area, 74.87, places=1)

    def test_layer_depths(self):
        depths = sorted(L.depth for L in self.result.layers)
        expected = [-0.611, 0.889, 3.889, 7.889]
        self.assertEqual(len(depths), len(expected))
        for actual, ref in zip(depths, expected):
            self.assertAlmostEqual(actual, ref, places=2)

    def test_layer_names(self):
        names = {L.name for L in self.result.layers}
        self.assertEqual(names, {'front', 'back', 'recess', 'pivot_tip'})

    def test_cylinder(self):
        self.assertEqual(len(self.result.cylinders), 1)
        cyl = self.result.cylinders[0]
        self.assertAlmostEqual(cyl.radius, 1.8, places=1)
        self.assertAlmostEqual(cyl.height, 4.0, places=1)

    def test_emitted_code_matches_expected(self):
        expected = EXPECTED_PATH.read_text(encoding='utf-8').strip()
        actual = self.result.code.strip()
        self.assertEqual(actual, expected)


if __name__ == '__main__':
    unittest.main()
