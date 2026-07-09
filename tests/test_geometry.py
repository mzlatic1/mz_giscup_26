import numpy as np
from shapely.geometry import Polygon

from giscup.geometry import make_building, ring_edges, segment_length


def test_ring_edges_closes_open_ring():
    coords = np.array([(0, 0), (1, 0), (1, 1), (0, 1)], dtype=float)
    assert len(ring_edges(coords)) == 4


def test_make_building_preserves_hole_and_perimeter():
    polygon = Polygon(shell=[(0, 0), (4, 0), (4, 4), (0, 4)], holes=[[(1, 1), (2, 1), (2, 2), (1, 2)]])
    building = make_building(9448, polygon)
    assert len(building.interiors) == 1
    assert building.perimeter == polygon.length


def test_segment_length():
    assert segment_length(np.array([0, 0]), np.array([3, 4])) == 5.0
