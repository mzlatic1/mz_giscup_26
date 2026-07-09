from shapely.geometry import Polygon

from giscup.geometry import make_building
from giscup.sampling import sample_building_boundary


def test_sampling_uses_weighted_midpoints():
    building = make_building(1, Polygon([(0, 0), (10, 0), (10, 10), (0, 10)]))
    samples = sample_building_boundary(building, spacing=10.0, min_samples_per_building=4)
    assert len(samples) == 4
    assert sum(s.weight for s in samples) == building.polygon.exterior.length
    assert samples[0].point == (5.0, 0.0)


def test_sampling_includes_hole_boundaries_to_match_shapely_perimeter():
    polygon = Polygon(
        shell=[(0, 0), (4, 0), (4, 4), (0, 4)],
        holes=[[(1, 1), (2, 1), (2, 2), (1, 2)]],
    )
    building = make_building(9448, polygon)

    samples = sample_building_boundary(building, spacing=10.0, min_samples_per_building=4)

    assert sum(s.weight for s in samples) == building.perimeter
