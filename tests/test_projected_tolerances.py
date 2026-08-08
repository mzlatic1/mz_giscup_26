"""Tolerances must be ABSOLUTE at projected-CRS magnitudes (task board #16).

Three separate defects in this project came from the same mistake: using a relative
tolerance, or a precision finer than float64 offers, on coordinates of ~1e5-1e6.

  - buffer(-1e-9) collapsed footprints to empty      (#10 / #14)
  - np.allclose declared 16 m edges zero-length      (#13)
  - (p0+p1)/2 landed inside footprints               (#14 / #15)

At an easting of 5e5 the ULP is ~5.8e-11 m; at a northing of 3.7e6 it is ~4.7e-10 m.
Any tolerance below that is meaningless, and any *relative* tolerance is enormous:
numpy's default rtol of 1e-5 is 37 metres at 3.7e6.

These tests pin the remaining places that make such comparisons.
"""

from __future__ import annotations

import numpy as np

from giscup.candidates import generate_boundary_candidates
from giscup.geometry import make_building, ring_edges
from shapely.geometry import Polygon

X0, Y0 = 500_000.0, 3_700_000.0


def test_an_open_ring_is_closed_even_at_utm_magnitudes():
    """A 10 m gap must be closed, not mistaken for a coincident endpoint.

    np.allclose's default rtol=1e-5 calls a 37 m gap 'equal' at a northing of 3.7e6,
    which would silently drop the closing edge and shorten the perimeter.
    """
    open_ring = np.array(
        [[X0, Y0], [X0 + 20.0, Y0], [X0 + 20.0, Y0 + 20.0], [X0, Y0 + 10.0]],
        dtype=np.float64,
    )
    edges = ring_edges(open_ring)
    assert len(edges) == 4, "the closing edge is missing"
    last_start, last_end = edges[-1]
    assert np.array_equal(last_end, open_ring[0]), "ring does not close back to its start"


def test_an_already_closed_ring_gains_no_duplicate_edge():
    closed = np.array(
        [[X0, Y0], [X0 + 20.0, Y0], [X0 + 20.0, Y0 + 20.0], [X0, Y0]],
        dtype=np.float64,
    )
    assert len(ring_edges(closed)) == 3


def test_shapely_rings_are_handled_unchanged():
    """The real data path: Shapely always returns a closed ring."""
    poly = Polygon([(X0, Y0), (X0 + 13.4, Y0), (X0 + 13.4, Y0 + 16.6), (X0, Y0 + 16.6)])
    building = make_building(0, poly)
    assert len(building.exterior_edges) == 4
    assert building.perimeter == poly.length


def test_candidate_dedupe_merges_points_closer_than_float_resolution():
    """Two footprints sharing a corner must not yield two coincident candidates."""
    a = Polygon([(X0, Y0), (X0 + 10, Y0), (X0 + 10, Y0 + 10), (X0, Y0 + 10)])
    b = Polygon([(X0 + 10, Y0 + 10), (X0 + 20, Y0 + 10), (X0 + 20, Y0 + 20), (X0 + 10, Y0 + 20)])
    buildings = [make_building(0, a), make_building(1, b)]
    candidates = generate_boundary_candidates(buildings, mode="basic")
    points = [(round(c.x, 6), round(c.y, 6)) for c in candidates]
    assert len(points) == len(set(points)), "coincident candidates were not deduplicated"
