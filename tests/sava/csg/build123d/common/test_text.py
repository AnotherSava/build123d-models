import unittest

from build123d import Axis, Mesher

from sava.csg.build123d.common.exporter import get_path
from sava.csg.build123d.common.smartsolid import SmartSolid
from sava.csg.build123d.common.text import TextDimensions, create_text


class TestTextSolidRotation(unittest.TestCase):

    def test_text_is_valid_after_orient(self) -> None:
        """Test that text remains valid after orient()"""
        dim = TextDimensions(font_size=12, font="Liberation Sans", height=0.8)
        text = create_text(dim, "A")

        text.orient((0, 0, 180))

        self.assertTrue(text.wrap_solid().is_valid)

    def test_text_is_valid_after_rotate(self) -> None:
        """Test that text remains valid after rotate()"""
        dim = TextDimensions(font_size=12, font="Liberation Sans", height=0.8)
        text = create_text(dim, "A")

        text.rotate_multi((0, 0, 180))

        self.assertTrue(text.wrap_solid().is_valid)

    def test_text_is_valid_after_rotate_with_axis(self) -> None:
        """Test that text remains valid after rotate_with_axis()"""
        dim = TextDimensions(font_size=12, font="Liberation Sans", height=0.8)
        text = create_text(dim, "A")

        text.rotate(Axis.Z, 180)

        self.assertTrue(text.wrap_solid().is_valid)

        mesher = Mesher()
        mesher.add_shape(text.wrap_solid())

    def test_text_mesh_valid_after_rotate_with_axis(self) -> None:
        """Test that text can be meshed after rotate_with_axis()"""
        dim = TextDimensions(font_size=12, font="Liberation Sans", height=0.8)
        text = create_text(dim, "H")

        text.rotate(Axis.Z, 180)

        mesher = Mesher()
        mesher.add_shape(text.wrap_solid())

    def test_multiple_rotated_texts_combined_and_meshed(self) -> None:
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

    def test_multichar_text_rotate_works(self) -> None:
        """Test that multi-char text (ShapeList) works with rotate_multi() after orientation replacement."""
        dim = TextDimensions(font_size=12, font="Liberation Sans", height=0.8)
        text = create_text(dim, "E/F")

        text.rotate_multi((0, 0, 180))

        self.assertTrue(text.wrap_solid().is_valid)


class TestTextSolidConnected(unittest.TestCase):

    def test_connected_joins_letters_into_one_solid(self) -> None:
        dim = TextDimensions(font_size=12, font="Liberation Sans", height=0.8)
        text = create_text(dim, "E/F")
        self.assertGreater(len(text.wrap_solid().solids()), 1)

        joined = text.connected()

        self.assertEqual(len(joined.wrap_solid().solids()), 1)
        self.assertTrue(joined.wrap_solid().is_valid)
        for axis in (Axis.X, Axis.Y, Axis.Z):
            self.assertAlmostEqual(joined.get_from(axis), text.get_from(axis), places=5)
            self.assertAlmostEqual(joined.get_to(axis), text.get_to(axis), places=5)


class TestCreateTextFontPath(unittest.TestCase):

    def test_glyph_occt_rejects_is_repaired(self) -> None:
        """Caveat's «н» comes out of OCCT as a face it reports invalid; extruded unrepaired, the solid is invalid too."""
        dim = TextDimensions(font_size=12.7, font="Caveat", height=0.6, font_path=get_path("input", "fonts", "caveat", "Caveat-Regular.ttf"))

        text = create_text(dim, "с днём")

        self.assertTrue(text.wrap_solid().is_valid)


if __name__ == '__main__':
    unittest.main()
