import unittest

from build123d import Axis, Mesher

from sava.csg.build123d.common.smartsolid import SmartSolid
from sava.csg.build123d.common.text import TextDimensions, create_text


class TestTextSolidRotation(unittest.TestCase):

    def test_text_is_valid_after_orient(self):
        """Test that text remains valid after orient()"""
        dim = TextDimensions(font_size=12, font="Liberation Sans", height=0.8)
        text = create_text(dim, "A")

        text.orient((0, 0, 180))

        self.assertTrue(text.wrap_solid().is_valid)

    def test_text_is_valid_after_rotate(self):
        """Test that text remains valid after rotate()"""
        dim = TextDimensions(font_size=12, font="Liberation Sans", height=0.8)
        text = create_text(dim, "A")

        text.rotate_multi((0, 0, 180))

        self.assertTrue(text.wrap_solid().is_valid)

    def test_text_is_valid_after_rotate_with_axis(self):
        """Test that text remains valid after rotate_with_axis()"""
        dim = TextDimensions(font_size=12, font="Liberation Sans", height=0.8)
        text = create_text(dim, "A")

        text.rotate(Axis.Z, 180)

        self.assertTrue(text.wrap_solid().is_valid)

        mesher = Mesher()
        mesher.add_shape(text.wrap_solid())

    def test_text_mesh_valid_after_rotate_with_axis(self):
        """Test that text can be meshed after rotate_with_axis()"""
        dim = TextDimensions(font_size=12, font="Liberation Sans", height=0.8)
        text = create_text(dim, "H")

        text.rotate(Axis.Z, 180)

        mesher = Mesher()
        mesher.add_shape(text.wrap_solid())

    def test_multiple_rotated_texts_combined_and_meshed(self):
        """Test combining multiple rotated texts into SmartSolid and meshing"""
        dim = TextDimensions(font_size=12, font="Liberation Sans", height=0.8)
        labels = ["A", "B", "C", "H", "I", "J"]
        texts = []

        for i, label in enumerate(labels):
            text = create_text(dim, label)
            text.move(i * 20, 0, 0)
            if i >= 3:
                text.rotate(Axis.Z, 180)
            texts.append(text)

        combined = SmartSolid(texts, label="socket types")

        self.assertTrue(combined.wrap_solid().is_valid)

        mesher = Mesher()
        mesher.add_shape(combined.wrap_solid())

    def test_multichar_text_rotate_fails(self):
        """Test that multi-char text (ShapeList) fails with rotate() - known limitation.

        Multi-character text creates a ShapeList which doesn't have .orientation attribute.
        Use rotate_with_axis() for multi-char text, or ensure multi-char text isn't rotated.
        """
        dim = TextDimensions(font_size=12, font="Liberation Sans", height=0.8)
        text = create_text(dim, "E/F")

        with self.assertRaises(AttributeError):
            text.rotate_multi((0, 0, 180))


if __name__ == '__main__':
    unittest.main()
