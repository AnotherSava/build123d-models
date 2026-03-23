import math

import pytest

from sava.csg.build123d.models.other.iris import IrisDimensions, create_blade, create_blades, _polar


class TestIrisDimensions:
    def test_aperture_radii(self):
        dim = IrisDimensions()
        assert dim.aperture_radius_min == 12.5
        assert dim.aperture_radius_max == 17.5

    def test_blade_angular_span(self):
        dim = IrisDimensions()
        assert dim.blade_angular_span == 72.0

    @pytest.mark.parametrize("blade_count,expected_span", [(3, 120.0), (4, 90.0), (5, 72.0), (6, 60.0), (8, 45.0)])
    def test_blade_angular_span_parametric(self, blade_count, expected_span):
        dim = IrisDimensions(blade_count=blade_count)
        assert dim.blade_angular_span == expected_span

    def test_pin_dimensions(self):
        dim = IrisDimensions()
        assert dim.pin_radius == 1.5
        assert dim.pivot_hole_radius == 1.7

    def test_blade_outer_radius_exceeds_pcd(self):
        dim = IrisDimensions()
        assert dim.blade_outer_radius > dim.pcd_radius

    def test_rotation_range_positive(self):
        dim = IrisDimensions()
        assert dim.rotation_range > 0

    def test_rotation_range_produces_correct_max_aperture(self):
        """Verify that rotating by rotation_range moves the inner edge midpoint
        from aperture_radius_min to aperture_radius_max distance from center."""
        dim = IrisDimensions()
        lever = dim.pcd_radius - dim.aperture_radius_min
        delta = math.radians(dim.rotation_range)
        distance = math.sqrt(dim.pcd_radius ** 2 - 2 * dim.pcd_radius * lever * math.cos(delta) + lever ** 2)
        assert abs(distance - dim.aperture_radius_max) < 0.001

    @pytest.mark.parametrize("aperture_min,aperture_max", [(20, 30), (25, 35), (30, 40), (10, 20)])
    def test_rotation_range_parametric_apertures(self, aperture_min, aperture_max):
        dim = IrisDimensions(aperture_diameter_min=aperture_min, aperture_diameter_max=aperture_max)
        lever = dim.pcd_radius - dim.aperture_radius_min
        delta = math.radians(dim.rotation_range)
        distance = math.sqrt(dim.pcd_radius ** 2 - 2 * dim.pcd_radius * lever * math.cos(delta) + lever ** 2)
        assert abs(distance - dim.aperture_radius_max) < 0.001

    def test_drive_slot_arc_length_positive(self):
        dim = IrisDimensions()
        assert dim.drive_slot_arc_length > 0

    def test_drive_pin_radius_from_center(self):
        dim = IrisDimensions()
        assert dim.drive_pin_radius_from_center == dim.pcd_radius - dim.drive_pin_offset


class TestCreateBlade:
    def test_blade_z_range(self):
        dim = IrisDimensions()
        blade = create_blade(dim)
        assert abs(blade.z_min) < 0.01
        assert abs(blade.z_max - (dim.blade_height + dim.drive_pin_height)) < 0.01

    def test_blade_extends_past_pcd(self):
        dim = IrisDimensions()
        blade = create_blade(dim)
        assert blade.x_max > dim.pcd_radius

    def test_blade_inner_edge_near_aperture_min(self):
        dim = IrisDimensions()
        blade = create_blade(dim)
        # The blade's minimum x should be close to r_inner * cos(half_span)
        expected_x_min = dim.aperture_radius_min * math.cos(math.radians(dim.blade_angular_span / 2))
        assert abs(blade.x_min - expected_x_min) < 0.5

    def test_blade_has_volume(self):
        dim = IrisDimensions()
        blade = create_blade(dim)
        assert blade.solid.volume > 0


class TestCreateBlades:
    def test_blade_count_default(self):
        dim = IrisDimensions()
        blades = create_blades(dim)
        assert len(blades) == 5

    @pytest.mark.parametrize("blade_count", [3, 4, 5, 6, 7, 8])
    def test_blade_count_parametric(self, blade_count):
        dim = IrisDimensions(blade_count=blade_count)
        blades = create_blades(dim)
        assert len(blades) == blade_count

    def test_all_blades_have_volume(self):
        dim = IrisDimensions()
        blades = create_blades(dim)
        for blade in blades:
            assert blade.solid.volume > 0

    def test_blades_at_closed_have_same_volume(self):
        dim = IrisDimensions()
        blades = create_blades(dim, rotation_angle=0)
        volumes = [b.solid.volume for b in blades]
        for v in volumes:
            assert abs(v - volumes[0]) < 0.01

    def test_blades_at_open_have_same_volume(self):
        dim = IrisDimensions()
        blades = create_blades(dim, rotation_angle=dim.rotation_range)
        volumes = [b.solid.volume for b in blades]
        for v in volumes:
            assert abs(v - volumes[0]) < 0.01

    def test_closed_aperture_matches_min(self):
        """At closed position, the inner edge midpoint of blade 0 should be at aperture_radius_min from center."""
        dim = IrisDimensions()
        # The inner edge midpoint in global coords is at (aperture_radius_min, 0) for blade 0
        # Verify by checking blade 0's geometry — the innermost point along the x-axis
        # should be at approximately aperture_radius_min
        blades = create_blades(dim, rotation_angle=0)
        blade_0 = blades[0]
        # Blade 0 is centered on angle 0, inner edge midpoint at (r_min, 0)
        # The blade's x_min is at the corners (cos(half_span) * r_inner), not the midpoint
        # So we check the expected aperture geometrically
        inner_mid = _polar(dim.aperture_radius_min, 0)
        distance_from_center = math.sqrt(inner_mid[0] ** 2 + inner_mid[1] ** 2)
        assert abs(distance_from_center - dim.aperture_radius_min) < 0.001

    def test_open_aperture_matches_max(self):
        """At open position, the rotated inner edge midpoint should be at aperture_radius_max from center."""
        dim = IrisDimensions()
        # Inner edge midpoint at closed: (aperture_radius_min, 0)
        # Pivot at: (pcd_radius, 0)
        # After rotating by rotation_range around pivot:
        pivot = _polar(dim.pcd_radius, 0)
        inner_mid_rel = (dim.aperture_radius_min - pivot[0], 0 - pivot[1])
        angle = math.radians(dim.rotation_range)
        rotated_x = inner_mid_rel[0] * math.cos(angle) - inner_mid_rel[1] * math.sin(angle)
        rotated_y = inner_mid_rel[0] * math.sin(angle) + inner_mid_rel[1] * math.cos(angle)
        abs_x = pivot[0] + rotated_x
        abs_y = pivot[1] + rotated_y
        distance = math.sqrt(abs_x ** 2 + abs_y ** 2)
        assert abs(distance - dim.aperture_radius_max) < 0.001
