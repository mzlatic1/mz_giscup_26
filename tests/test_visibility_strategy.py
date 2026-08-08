"""Strategy-equivalence and default-contract tests for visibility predicates.

Task board #1. Two things are pinned here:

1. `relate` is the default everywhere, so the ~2.5x-slower `hybrid` cannot creep back
   in silently. `relate_pattern(poly, "T********")` is exactly the official predicate --
   interior-of-line meets interior-of-polygon.
2. All three strategies agree on the official degeneracy set, so switching the default
   cannot change a single visibility answer.
"""

from __future__ import annotations

import inspect

import pytest
from shapely.geometry import Polygon

from giscup import cli, coverage, optimize, solver, validate, visibility
from giscup.geometry import make_building
from giscup.visibility import BlockerIndex, is_visible

STRATEGIES = ("relate", "negative_buffer", "hybrid")

UNIT_SQUARE = Polygon([(0, 0), (1, 0), (1, 1), (0, 1)])

# An L-shape whose notch ([1,2] x [1,2]) is exterior. Exercises non-convex
# self-blocking, which a convex footprint cannot express.
L_SHAPE = Polygon([(0, 0), (2, 0), (2, 1), (1, 1), (1, 2), (0, 2)])

# The official degeneracy set: (name, polygon, point_a, point_b, expected_visible).
# Blocked iff the segment interior meets the polygon interior. Tangency, vertex
# contact, and boundary-only contact never block.
DEGENERACIES = [
    ("clear_no_contact", UNIT_SQUARE, (-1, 2), (2, 2), True),
    ("interior_crossing", UNIT_SQUARE, (-1, 0.5), (2, 0.5), False),
    ("collinear_along_edge", UNIT_SQUARE, (-1, 1), (2, 1), True),
    ("single_vertex_touch", UNIT_SQUARE, (-1, -1), (0, 0), True),
    ("corner_graze", UNIT_SQUARE, (-1, 1), (1, -1), True),
    ("adjacent_same_edge_points", UNIT_SQUARE, (0, 0), (1, 0), True),
    ("boundary_endpoint_ray_outward", UNIT_SQUARE, (0, 0), (-1, -1), True),
    ("boundary_endpoint_ray_inward", UNIT_SQUARE, (0, 0), (1, 1), False),
    ("self_blocking_opposite_sides", UNIT_SQUARE, (0, 0.5), (1, 0.5), False),
    ("nonconvex_self_blocking", L_SHAPE, (2, 0.5), (0.5, 2), False),
    ("nonconvex_around_notch", L_SHAPE, (2, 1), (1, 2), True),
]


def _index(polygon: Polygon) -> BlockerIndex:
    return BlockerIndex.from_buildings([make_building(1, polygon)])


@pytest.mark.parametrize("strategy", STRATEGIES)
@pytest.mark.parametrize(
    ("name", "polygon", "a", "b", "expected"),
    [pytest.param(*case, id=case[0]) for case in DEGENERACIES],
)
def test_strategies_agree_on_official_degeneracies(name, polygon, a, b, expected, strategy):
    """Every strategy must return the official answer on every degeneracy."""
    assert is_visible(a, b, _index(polygon), strategy=strategy) is expected


@pytest.mark.parametrize(
    ("name", "polygon", "a", "b", "expected"),
    [pytest.param(*case, id=case[0]) for case in DEGENERACIES],
)
def test_visibility_is_symmetric(name, polygon, a, b, expected):
    """Visibility is a symmetric relation; the matrix build will rely on this."""
    index = _index(polygon)
    assert is_visible(a, b, index) is is_visible(b, a, index)


def test_unknown_strategy_raises():
    with pytest.raises(ValueError, match="strategy must be one of"):
        is_visible((0, 0), (2, 2), _index(UNIT_SQUARE), strategy="teleport")


# --- default-contract tests -------------------------------------------------


def _default(func, param: str) -> object:
    return inspect.signature(func).parameters[param].default


def test_is_visible_defaults_to_relate():
    assert _default(visibility.is_visible, "strategy") == "relate"


@pytest.mark.parametrize(
    ("func", "param"),
    [
        (coverage.visible_sample_ids, "strategy"),
        (optimize.greedy_select, "strategy"),
        (solver.solve_one, "visibility_strategy"),
        (validate.validate_solution_file, "visibility_strategy"),
    ],
)
def test_pipeline_entry_points_default_to_relate(func, param):
    assert _default(func, param) == "relate"


@pytest.mark.parametrize(
    ("argv", "extra"),
    [
        (["solve-one", "--input", "x", "--tau", "0.5", "--k", "1", "--output", "o"], []),
        (["solve-all", "--input", "x", "--taus", "0.5", "--ks", "1", "--output", "o"], []),
        (["validate-output", "--input", "x", "--solution", "s"], []),
    ],
)
def test_cli_defaults_to_relate(argv, extra):
    args = cli.build_parser().parse_args(argv + extra)
    assert args.visibility_strategy == "relate"


# --- erosion hoisting -------------------------------------------------------


def test_eroded_polygons_are_memoized_per_epsilon():
    """`buffer(-eps)` must be computed once per building, not once per predicate call."""
    index = _index(UNIT_SQUARE)
    first = index.eroded_polygons(1e-9)
    second = index.eroded_polygons(1e-9)
    assert first is second, "eroded geometry must be cached, not rebuilt per call"


def test_eroded_polygons_align_with_buildings():
    buildings = [make_building(1, UNIT_SQUARE), make_building(2, L_SHAPE)]
    index = BlockerIndex.from_buildings(buildings)
    eroded = index.eroded_polygons(1e-9)
    assert len(eroded) == len(buildings)
    for original, shrunk in zip(buildings, eroded, strict=True):
        assert shrunk.area < original.polygon.area


def test_distinct_epsilons_get_distinct_caches():
    index = _index(UNIT_SQUARE)
    assert index.eroded_polygons(1e-9) is not index.eroded_polygons(1e-3)
    assert index.eroded_polygons(1e-3)[0].area < index.eroded_polygons(1e-9)[0].area


# --- numerical safety of the erosion strategies -----------------------------

# UTM 11N magnitudes, matching the real dataset's CRS (EPSG:32611). At these
# coordinates buffer(-1e-9) is below float64 relative precision and collapses
# the polygon to empty, which would make `negative_buffer` report everything
# visible. It must fail loudly instead of silently over-claiming.
UTM_X, UTM_Y = 500_000.0, 3_700_000.0
UTM_BUILDING = Polygon(
    [(UTM_X, UTM_Y), (UTM_X + 20, UTM_Y), (UTM_X + 20, UTM_Y + 20), (UTM_X, UTM_Y + 20)]
)


def test_degenerate_erosion_raises_instead_of_reporting_everything_visible():
    index = _index(UTM_BUILDING)
    a, b = (UTM_X - 5, UTM_Y + 10), (UTM_X + 25, UTM_Y + 10)  # straight through the interior
    with pytest.raises(ValueError, match="eroded to empty"):
        is_visible(a, b, index, strategy="negative_buffer", eps=1e-9)


def test_relate_is_unaffected_by_coordinate_magnitude():
    """The official predicate must block an interior crossing at any CRS magnitude."""
    index = _index(UTM_BUILDING)
    a, b = (UTM_X - 5, UTM_Y + 10), (UTM_X + 25, UTM_Y + 10)
    assert is_visible(a, b, index, strategy="relate") is False
    assert is_visible(a, b, index, strategy="hybrid") is False


def test_erosion_with_a_workable_epsilon_still_succeeds():
    """A well-scaled eps must keep working -- the guard targets degeneracy, not erosion."""
    index = _index(UTM_BUILDING)
    a, b = (UTM_X - 5, UTM_Y + 10), (UTM_X + 25, UTM_Y + 10)
    assert is_visible(a, b, index, strategy="negative_buffer", eps=1e-4) is False
