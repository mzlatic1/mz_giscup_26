"""Generate a full-scale synthetic building dataset matching the documented sample statistics.

The official sample dataset is not present in ``data/``, and the test dataset does
not exist until 2026-08-15. Every performance number for this solver is therefore
an extrapolation until something full-size can actually be run.

This generates a stand-in with the same *scale and shape* as the documented sample
(``docs/original_implementation_brief.md`` section 4), so feasibility work can start
now instead of on the day the real data lands.

Target statistics (documented sample):

===========================  ==========================
buildings                    12,860
exterior vertices            78,727  (min 4, median 6, mean 6.12, max 38)
total area                   3,416,147.87 m^2  (median 201.76, mean 265.64)
total perimeter              858,973.22 m      (median 62.13, mean 66.79)
bbox                         4,946.28 x 4,263.94 m
CRS                          EPSG:32611 (UTM 11N)
holes                        exactly one polygon (documented id 9448)
exterior ring orientation    clockwise
===========================  ==========================

This is NOT the official data and must never be presented as a substitute for it.
It reproduces the documented aggregate statistics; it does not reproduce the real
street grid, so absolute visibility numbers will differ. Use it for feasibility,
scaling, and regression work — not for tuning claims about solution quality.

Usage::

    python scripts/make_synthetic_dataset.py --output outputs/synthetic_full.geojson
    python scripts/make_synthetic_dataset.py --buildings 2000 --output outputs/synthetic_small.geojson
"""

from __future__ import annotations

import argparse
import json
import math
import random
from pathlib import Path

import numpy as np
from shapely.geometry import Polygon, mapping
from shapely.ops import orient

# --- documented sample targets -------------------------------------------------
N_BUILDINGS = 12_860
BBOX_W, BBOX_H = 4_946.2776384285535, 4_263.937068715226
ORIGIN_X, ORIGIN_Y = 480_722.890, 3_765_686.401  # max x/y in the brief minus width/height
AREA_MEDIAN, AREA_MEAN = 201.76432641873942, 265.64135854261986
AREA_MIN, AREA_MAX = 7.252682450690249, 17_956.716603489156
CRS_NAME = "urn:ogc:def:crs:EPSG::32611"
HOLE_BUILDING_INDEX = 9448  # documented id carrying the single interior ring

# Vertex-count distribution: median 6, mean ~6.12, min 4, max 38.
# Footprints are rectilinear, so counts are even; a chamfer pass supplies odd counts.
_VERTEX_CHOICES = [4, 6, 8, 10, 12, 16, 24, 38]
_VERTEX_WEIGHTS = [0.42, 0.34, 0.13, 0.055, 0.03, 0.015, 0.007, 0.003]


def _lognormal_params(median: float, mean: float) -> tuple[float, float]:
    """Return (mu, sigma) of a lognormal with the given median and mean."""
    mu = math.log(median)
    sigma = math.sqrt(2.0 * math.log(mean / median))
    return mu, sigma


def _rectangle(area: float, aspect: float) -> list[tuple[float, float]]:
    """Axis-aligned rectangle of the given area and width:height ratio, at the origin."""
    h = math.sqrt(area / aspect)
    w = area / h
    return [(0.0, 0.0), (w, 0.0), (w, h), (0.0, h)]


def _notch(coords: list[tuple[float, float]], rng: random.Random) -> list[tuple[float, float]]:
    """Cut a rectilinear notch out of one edge, adding two vertices.

    This is how real footprints gain vertices — L- and T-shaped buildings — and it
    keeps the polygon simple and axis-aligned.
    """
    n = len(coords)
    i = rng.randrange(n)
    p0 = np.array(coords[i], dtype=float)
    p1 = np.array(coords[(i + 1) % n], dtype=float)
    edge = p1 - p0
    length = float(np.hypot(*edge))
    if length < 2.0:
        return coords
    direction = edge / length
    normal = np.array([-direction[1], direction[0]])

    # Notch occupies a middle span of the edge, cut inward by a modest depth.
    span = length * rng.uniform(0.25, 0.55)
    depth = min(length, span) * rng.uniform(0.25, 0.6)
    start = (length - span) * rng.uniform(0.2, 0.8)

    a = p0 + direction * start
    b = a + direction * span
    inward = -normal * depth  # normal points outward for a CCW ring
    out = coords[: i + 1]
    out.extend([tuple(a), tuple(a + inward), tuple(b + inward), tuple(b)])
    out.extend(coords[i + 1 :])
    return [(float(x), float(y)) for x, y in out]


def _corner_notch(coords: list[tuple[float, float]], rng: random.Random) -> list[tuple[float, float]]:
    """Cut a rectangular bite out of one corner, adding exactly two vertices (an L-shape)."""
    n = len(coords)
    i = rng.randrange(n)
    prev = np.array(coords[(i - 1) % n], dtype=float)
    cur = np.array(coords[i], dtype=float)
    nxt = np.array(coords[(i + 1) % n], dtype=float)
    a = cur + (prev - cur) * rng.uniform(0.2, 0.5)
    b = cur + (nxt - cur) * rng.uniform(0.2, 0.5)
    inner = a + b - cur  # fourth corner of the removed rectangle
    return [
        *coords[:i],
        (float(a[0]), float(a[1])),
        (float(inner[0]), float(inner[1])),
        (float(b[0]), float(b[1])),
        *coords[i + 1 :],
    ]


def _chamfer(coords: list[tuple[float, float]], rng: random.Random) -> list[tuple[float, float]]:
    """Clip one corner, adding a single vertex so odd vertex counts can occur."""
    n = len(coords)
    i = rng.randrange(n)
    prev = np.array(coords[(i - 1) % n], dtype=float)
    cur = np.array(coords[i], dtype=float)
    nxt = np.array(coords[(i + 1) % n], dtype=float)
    f = rng.uniform(0.15, 0.35)
    a = cur + (prev - cur) * f
    b = cur + (nxt - cur) * f
    return [
        *coords[:i],
        (float(a[0]), float(a[1])),
        (float(b[0]), float(b[1])),
        *coords[i + 1 :],
    ]


def _make_footprint(area: float, rng: random.Random) -> Polygon:
    """Build one rectilinear footprint of approximately the requested area."""
    target_vertices = rng.choices(_VERTEX_CHOICES, weights=_VERTEX_WEIGHTS, k=1)[0]
    aspect = math.exp(rng.gauss(math.log(2.35), 0.45))
    aspect = min(max(aspect, 1.05), 8.0)
    coords = _rectangle(area, aspect)

    # _notch adds 4 vertices (a bite out of an edge), _corner_notch adds 2 (an L).
    # Spend the vertex budget with the larger operation first, then top up.
    need = target_vertices - 4
    guard = 0
    while need >= 2 and guard < 40:
        guard += 1
        grow = _notch if (need >= 4 and rng.random() < 0.6) else _corner_notch
        grown = grow(coords, rng)
        candidate = Polygon(grown)
        if candidate.is_valid and not candidate.is_empty and candidate.area > 0:
            need -= len(grown) - len(coords)
            coords = grown
    if rng.random() < 0.08:
        chamfered = _chamfer(coords, rng)
        candidate = Polygon(chamfered)
        if candidate.is_valid and candidate.area > 0:
            coords = chamfered

    poly = Polygon(coords)
    if not poly.is_valid or poly.area <= 0:
        poly = Polygon(_rectangle(area, aspect))

    # Notching removes area; rescale about the centroid to hit the target.
    if poly.area > 0:
        scale = math.sqrt(area / poly.area)
        cx, cy = poly.centroid.x, poly.centroid.y
        poly = Polygon([((x - cx) * scale + cx, (y - cy) * scale + cy) for x, y in poly.exterior.coords[:-1]])
    return poly


def _add_hole(poly: Polygon, rng: random.Random) -> Polygon:
    """Insert one interior ring, reproducing the documented single hole-bearing polygon."""
    minx, miny, maxx, maxy = poly.bounds
    cx, cy = (minx + maxx) / 2.0, (miny + maxy) / 2.0
    w, h = (maxx - minx) * 0.22, (maxy - miny) * 0.22
    ring = [(cx - w, cy - h), (cx + w, cy - h), (cx + w, cy + h), (cx - w, cy + h)]
    holed = Polygon(poly.exterior.coords, [ring])
    return holed if holed.is_valid and not holed.is_empty else poly


def generate(n_buildings: int, seed: int) -> tuple[list[Polygon], dict]:
    """Generate footprints and return them with achieved-vs-target statistics."""
    rng = random.Random(seed)
    mu, sigma = _lognormal_params(AREA_MEDIAN, AREA_MEAN)

    # Jittered grid sized to the documented bbox, scaled if a smaller run is requested.
    scale = math.sqrt(n_buildings / N_BUILDINGS)
    width, height = BBOX_W * scale, BBOX_H * scale
    cols = max(1, int(round(math.sqrt(n_buildings * width / height))))
    rows = max(1, math.ceil(n_buildings / cols))
    cell_w, cell_h = width / cols, height / rows

    polygons: list[Polygon] = []
    for idx in range(n_buildings):
        r, c = divmod(idx, cols)
        area = min(max(math.exp(rng.gauss(mu, sigma)), AREA_MIN), AREA_MAX)
        # Keep footprints inside their cell so the grid does not self-overlap.
        area = min(area, cell_w * cell_h * 0.55)
        poly = _make_footprint(area, rng)

        pminx, pminy, pmaxx, pmaxy = poly.bounds
        pad_x = max(cell_w - (pmaxx - pminx), 0.0)
        pad_y = max(cell_h - (pmaxy - pminy), 0.0)
        ox = ORIGIN_X + c * cell_w + rng.uniform(0, pad_x) - pminx
        oy = ORIGIN_Y + r * cell_h + rng.uniform(0, pad_y) - pminy
        poly = Polygon([(x + ox, y + oy) for x, y in poly.exterior.coords[:-1]])

        if idx == HOLE_BUILDING_INDEX % max(n_buildings, 1):
            poly = _add_hole(poly, rng)
        # Documented sample rings are clockwise.
        polygons.append(orient(poly, sign=-1.0))

    areas = np.array([p.area for p in polygons])
    perims = np.array([p.length for p in polygons])
    verts = np.array([len(p.exterior.coords) - 1 for p in polygons])
    bounds = np.array([p.bounds for p in polygons])
    stats = {
        "buildings": {"achieved": len(polygons), "target": N_BUILDINGS},
        "exterior_vertices": {"achieved": int(verts.sum()), "target": 78_727},
        "vertices_min_median_mean_max": {
            "achieved": [int(verts.min()), float(np.median(verts)), round(float(verts.mean()), 3), int(verts.max())],
            "target": [4, 6.0, 6.122, 38],
        },
        "total_area_m2": {"achieved": round(float(areas.sum()), 2), "target": 3_416_147.87},
        "area_median_mean": {
            "achieved": [round(float(np.median(areas)), 2), round(float(areas.mean()), 2)],
            "target": [201.76, 265.64],
        },
        "total_perimeter_m": {"achieved": round(float(perims.sum()), 2), "target": 858_973.22},
        "perimeter_median_mean": {
            "achieved": [round(float(np.median(perims)), 2), round(float(perims.mean()), 2)],
            "target": [62.13, 66.79],
        },
        "bbox_w_h_m": {
            "achieved": [
                round(float(bounds[:, 2].max() - bounds[:, 0].min()), 2),
                round(float(bounds[:, 3].max() - bounds[:, 1].min()), 2),
            ],
            "target": [round(BBOX_W, 2), round(BBOX_H, 2)],
        },
        "valid_polygons": {"achieved": int(sum(p.is_valid for p in polygons)), "target": len(polygons)},
        "polygons_with_holes": {"achieved": int(sum(len(p.interiors) > 0 for p in polygons)), "target": 1},
    }
    return polygons, stats


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--output", required=True, help="Destination GeoJSON path")
    parser.add_argument("--buildings", type=int, default=N_BUILDINGS)
    parser.add_argument("--seed", type=int, default=20260806)
    args = parser.parse_args(argv)

    out = Path(args.output)
    if out.resolve().is_relative_to(Path("data").resolve()) if Path("data").exists() else False:
        raise SystemExit("refusing to write synthetic data into data/; that directory is for official datasets")

    polygons, stats = generate(args.buildings, args.seed)
    features = [
        {"type": "Feature", "properties": {"id": i}, "geometry": mapping(p)} for i, p in enumerate(polygons)
    ]
    payload = {
        "type": "FeatureCollection",
        "crs": {"type": "name", "properties": {"name": CRS_NAME}},
        "features": features,
    }
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload), encoding="utf-8")

    print(f"wrote {out}  ({out.stat().st_size / 1e6:.1f} MB)")
    print(f"{'statistic':32s} {'achieved':>26s} {'target':>26s}")
    for key, value in stats.items():
        print(f"{key:32s} {str(value['achieved']):>26s} {str(value['target']):>26s}")
    print("\nSYNTHETIC — reproduces documented aggregate statistics only.")
    print("Not a substitute for the official dataset; do not tune solution-quality claims on it.")
    print("Known fidelity gaps: footprints are clamped to their grid cell, so the documented")
    print("large tail (max area 17,957 m2 / max perimeter 1,066 m) is absent; total perimeter")
    print("runs ~5% high because notching adds perimeter after area is rescaled. Both make this")
    print("a slightly conservative performance proxy, which is the safe direction.")


if __name__ == "__main__":
    main()
