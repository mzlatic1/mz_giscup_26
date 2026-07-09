from shapely.geometry import Polygon

from giscup.geometry import make_building
from giscup.visibility import BlockerIndex, is_visible


def _idx():
    return BlockerIndex.from_buildings([make_building(1, Polygon([(0, 0), (1, 0), (1, 1), (0, 1)]))])


def test_clear_line_of_sight():
    assert is_visible((-1, 2), (2, 2), _idx())


def test_crossing_interior_blocks():
    assert not is_visible((-1, 0.5), (2, 0.5), _idx())


def test_tangent_line_does_not_block():
    assert is_visible((-1, 1), (2, 1), _idx())


def test_vertex_touch_does_not_block():
    assert is_visible((-1, -1), (0, 0), _idx())


def test_boundary_overlap_does_not_block():
    assert is_visible((0, 0), (1, 0), _idx())
