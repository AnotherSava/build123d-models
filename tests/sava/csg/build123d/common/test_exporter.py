import os
import tempfile
import unittest

from build123d import Box
from parameterized import parameterized

from sava.csg.build123d.common.exporter import (
    export, clear, show_red, show_blue, show_green, save_3mf, save_stl,
    _shapes, _label_colors, _get_color_for_label, _prepare_shape, BASIC_COLORS
)


class TestExport(unittest.TestCase):

    def setUp(self):
        clear()

    def test_export_default_label(self):
        """Test export with default 'model' label"""
        box = Box(10, 10, 10)
        export(box)

        self.assertIn("model", _shapes)
        self.assertEqual(len(_shapes["model"]), 1)

    def test_export_custom_label(self):
        """Test export with custom label"""
        box = Box(10, 10, 10)
        export(box, "custom")

        self.assertIn("custom", _shapes)
        self.assertEqual(len(_shapes["custom"]), 1)

    def test_export_multiple_shapes_same_label(self):
        """Test exporting multiple shapes with the same label"""
        export(Box(10, 10, 10), "parts")
        export(Box(5, 5, 5), "parts")

        self.assertEqual(len(_shapes["parts"]), 2)

    def test_export_multiple_labels(self):
        """Test exporting shapes with different labels"""
        export(Box(10, 10, 10), "body")
        export(Box(5, 5, 5), "screw")

        self.assertIn("body", _shapes)
        self.assertIn("screw", _shapes)
        self.assertEqual(len(_shapes["body"]), 1)
        self.assertEqual(len(_shapes["screw"]), 1)


class TestShowColorFunctions(unittest.TestCase):

    def setUp(self):
        clear()

    def test_show_red(self):
        """Test show_red exports with 'red' label"""
        box = Box(10, 10, 10)
        show_red(box)

        self.assertIn("red", _shapes)
        self.assertEqual(len(_shapes["red"]), 1)

    def test_show_blue(self):
        """Test show_blue exports with 'blue' label"""
        box = Box(10, 10, 10)
        show_blue(box)

        self.assertIn("blue", _shapes)

    def test_show_green(self):
        """Test show_green exports with 'green' label"""
        box = Box(10, 10, 10)
        show_green(box)

        self.assertIn("green", _shapes)


class TestGetColorForLabel(unittest.TestCase):

    def setUp(self):
        clear()

    @parameterized.expand([
        ("red",),
        ("blue",),
        ("green",),
        ("yellow",),
    ])
    def test_valid_color_label_returns_itself(self, color):
        """Test that valid color names are returned as-is"""
        result = _get_color_for_label(color)
        self.assertEqual(result, color)

    def test_custom_label_gets_assigned_color(self):
        """Test that custom labels get assigned colors from BASIC_COLORS"""
        result = _get_color_for_label("custom_label")
        self.assertIn(result, BASIC_COLORS)

    def test_same_label_gets_same_color(self):
        """Test that the same label always returns the same color"""
        color1 = _get_color_for_label("my_label")
        color2 = _get_color_for_label("my_label")
        self.assertEqual(color1, color2)

    def test_different_labels_get_different_colors(self):
        """Test that different labels get different colors"""
        color1 = _get_color_for_label("label1")
        color2 = _get_color_for_label("label2")
        self.assertNotEqual(color1, color2)

    def test_exhaust_colors_raises_error(self):
        """Test that exhausting all colors raises RuntimeError"""
        for i in range(len(BASIC_COLORS)):
            _get_color_for_label(f"label_{i}")

        with self.assertRaises(RuntimeError) as context:
            _get_color_for_label("one_too_many")

        self.assertIn("exhausted", str(context.exception))


class TestPrepareShape(unittest.TestCase):

    def setUp(self):
        clear()

    def test_prepare_shape_assigns_label(self):
        """Test that _prepare_shape assigns label to shape"""
        box = Box(10, 10, 10)
        prepared = _prepare_shape(box, "test_label")

        self.assertEqual(len(prepared), 1)
        self.assertEqual(prepared[0].label, "test_label")

    def test_prepare_shape_assigns_color_for_color_label(self):
        """Test that color labels get their color assigned"""
        box = Box(10, 10, 10)
        prepared = _prepare_shape(box, "red")

        self.assertEqual(prepared[0].label, "red")


class TestClear(unittest.TestCase):

    def test_clear_removes_shapes(self):
        """Test that clear removes all stored shapes"""
        export(Box(10, 10, 10), "test")
        self.assertEqual(len(_shapes), 1)

        clear()
        self.assertEqual(len(_shapes), 0)

    def test_clear_removes_color_assignments(self):
        """Test that clear removes color assignments"""
        _get_color_for_label("custom")
        self.assertEqual(len(_label_colors), 1)

        clear()
        self.assertEqual(len(_label_colors), 0)


class TestSave3mf(unittest.TestCase):

    def setUp(self):
        clear()

    def test_save_3mf_creates_file(self):
        """Test that save_3mf creates a file at the specified location"""
        export(Box(10, 10, 10))

        with tempfile.TemporaryDirectory() as tmpdir:
            filepath = os.path.join(tmpdir, "test_model.3mf")
            save_3mf(filepath)

            self.assertTrue(os.path.exists(filepath))

    def test_save_3mf_with_multiple_labels(self):
        """Test that save_3mf works with multiple labels"""
        export(Box(10, 10, 10), "body")
        export(Box(5, 5, 5), "screw")

        with tempfile.TemporaryDirectory() as tmpdir:
            filepath = os.path.join(tmpdir, "multi_label.3mf")
            save_3mf(filepath)

            self.assertTrue(os.path.exists(filepath))
            self.assertGreater(os.path.getsize(filepath), 0)


class TestSaveStl(unittest.TestCase):

    def setUp(self):
        clear()

    def test_save_stl_creates_files_per_label(self):
        """Test that save_stl creates separate files for each label"""
        export(Box(10, 10, 10), "body")
        export(Box(5, 5, 5), "screw")

        with tempfile.TemporaryDirectory() as tmpdir:
            save_stl(tmpdir)

            self.assertTrue(os.path.exists(os.path.join(tmpdir, "body.stl")))
            self.assertTrue(os.path.exists(os.path.join(tmpdir, "screw.stl")))

    def test_save_stl_single_label(self):
        """Test that save_stl works with a single label"""
        export(Box(10, 10, 10), "model")

        with tempfile.TemporaryDirectory() as tmpdir:
            save_stl(tmpdir)

            self.assertTrue(os.path.exists(os.path.join(tmpdir, "model.stl")))
            self.assertGreater(os.path.getsize(os.path.join(tmpdir, "model.stl")), 0)


if __name__ == '__main__':
    unittest.main()

