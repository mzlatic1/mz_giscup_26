"""Predicate-correctness and default-contract tests for visibility.

`relate_pattern(poly, "T********")` is exactly the official predicate: interior of the
segment meeting interior of the polygon. Since task #10 it is the *only* strategy --
`negative_buffer` and `hybrid` were removed 2026-08-08.

Pinned here:

1. The predicate returns the official answer on every degeneracy, including two
   non-convex self-blocking cases a square cannot express.
2. Visibility is symmetric, which the visibility matrix relies on.
3. `relate` is the default at every entry point and on the CLI, so a slower or
   unsafe alternative cannot creep back in silently.
"""

from __future__ import annotations

import inspect

import pytest
from shapely.geometry import Polygon

from giscup import cli, coverage, optimize, solver, validate, visibility
from giscup.geometry import make_building
from giscup.visibility import BlockerIndex, is_visible

STRATEGIES = ("relate",)

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
def test_predicate_returns_the_official_answer_on_degeneracies(name, polygon, a, b, expected, strategy):
    """The predicate must return the official answer on every degeneracy."""
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
