import pytest

from sava.csg.build123d.models.other.iris import (
    IrisDimensions,
    create_blade,
    create_blades,
    create_cover,
    create_diaphragm_plate,
    _pin_along_stadium_axis,
)


@pytest.fixture(scope='module')
def dim():
    return IrisDimensions()


@pytest.fixture(scope='module')
def slot(dim):
    _, slot = create_diaphragm_plate(dim)
    return slot


class TestIrisDimensions:
    @pytest.mark.parametrize("plate_thickness,min_thickness,expected", [
        (2.999, 0.8, 2.199),
        (3.0, 1.0, 2.0),
        (5.0, 0.5, 4.5),
    ])
    def test_protrusion_thickness_derivation(self, plate_thickness, min_thickness, expected):
        dim = IrisDimensions(plate_thickness=plate_thickness, min_thickness=min_thickness)
        assert abs(dim.protrusion_thickness - expected) < 1e-9

    @pytest.mark.parametrize("pin_diameter,expected_radius", [(3.64, 1.82), (4.0, 2.0), (5.0, 2.5)])
    def test_pin_radius_derivation(self, pin_diameter, expected_radius):
        dim = IrisDimensions(pin_diameter=pin_diameter)
        assert abs(dim.pin_radius - expected_radius) < 1e-9

    @pytest.mark.parametrize("pin_diameter,pin_padding,expected", [
        (3.64, 0.2, 4.04),
        (4.0, 0.3, 4.6),
        (5.0, 0.0, 5.0),
    ])
    def test_cover_slot_width_derivation(self, pin_diameter, pin_padding, expected):
        dim = IrisDimensions(pin_diameter=pin_diameter, pin_padding=pin_padding)
        assert abs(dim.cover_slot_width - expected) < 1e-9


class TestCreateBlade:
    @pytest.mark.parametrize("slot_position", [0.0, 0.5, 1.0])
    def test_blade_z_range(self, dim, slot, slot_position):
        """Aligned blade: back protrusion sits in the slot pocket, body and
        pin stack above. Total Z span is back + body + pin."""
        blade = create_blade(dim, slot, slot_position)
        expected_height = dim.protrusion_thickness + dim.blade_thickness + dim.pin_height
        assert abs(blade.z_min - slot.z_min) < 0.01
        assert abs((blade.z_max - blade.z_min) - expected_height) < 0.01

    @pytest.mark.parametrize("slot_position", [0.0, 0.5, 1.0])
    def test_blade_has_volume(self, dim, slot, slot_position):
        blade = create_blade(dim, slot, slot_position)
        assert blade.solid.volume > 0


class TestCreateBlades:
    def test_blade_count_default(self, dim, slot):
        blades = create_blades(dim, slot)
        assert len(blades) == 6

    @pytest.mark.parametrize("slot_position", [0.0, 0.5, 1.0])
    def test_all_blades_have_volume(self, dim, slot, slot_position):
        blades = create_blades(dim, slot, slot_position=slot_position)
        for blade in blades:
            assert blade.solid.volume > 0

    @pytest.mark.parametrize("slot_position", [0.0, 0.5, 1.0])
    def test_blades_have_equal_volume(self, dim, slot, slot_position):
        """All blades come from the same template, just rotated — volumes must match."""
        blades = create_blades(dim, slot, slot_position=slot_position)
        volumes = [b.solid.volume for b in blades]
        for v in volumes:
            assert abs(v - volumes[0]) < 0.01


class TestCreateDiaphragmPlate:
    def test_plate_has_volume(self, dim):
        plate, _ = create_diaphragm_plate(dim)
        assert plate.solid.volume > 0

    @pytest.mark.parametrize("plate_thickness", [2.0, 2.999, 5.0])
    def test_plate_thickness_drives_z_extent(self, plate_thickness):
        dim = IrisDimensions(plate_thickness=plate_thickness)
        plate, _ = create_diaphragm_plate(dim)
        assert abs((plate.z_max - plate.z_min) - plate_thickness) < 0.01


class TestCreateCover:
    def test_cover_has_volume(self, dim):
        cover = create_cover(dim)
        assert cover.solid.volume > 0

    @pytest.mark.parametrize("cover_thickness", [1.5, 2.0, 3.5])
    def test_cover_thickness_drives_z_extent(self, cover_thickness):
        dim = IrisDimensions(cover_thickness=cover_thickness)
        cover = create_cover(dim)
        assert abs((cover.z_max - cover.z_min) - cover_thickness) < 0.01

    @pytest.mark.parametrize("pin_padding", [0.1, 0.2, 0.5])
    @pytest.mark.parametrize("pin_diameter", [2.5, 3.0, 3.64])
    def test_both_extremes_have_exact_pin_padding_clearance(self, pin_diameter, pin_padding):
        """Stadium centre is shifted along the long axis so pin travel is
        symmetric — both extremes (sp=0 and sp=1) get exactly `pin_padding`
        of clearance from the pin OD to the stadium end."""
        dim = IrisDimensions(pin_diameter=pin_diameter, pin_padding=pin_padding)
        a_0 = _pin_along_stadium_axis(dim, 0.0)
        a_1 = _pin_along_stadium_axis(dim, 1.0)
        # Symmetric around the (shifted) stadium centre
        assert abs(a_0 + a_1) < 1e-9
        slot_length = 2 * abs(a_0) + dim.cover_slot_width
        gap_at_sp0 = slot_length / 2 - (abs(a_0) + dim.pin_radius)
        gap_at_sp1 = slot_length / 2 - (abs(a_1) + dim.pin_radius)
        assert abs(gap_at_sp0 - pin_padding) < 1e-9
        assert abs(gap_at_sp1 - pin_padding) < 1e-9
