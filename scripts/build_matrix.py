#!/usr/bin/env python
"""Build (or reuse) the radius-culled visibility matrix at full scale.

Task board #2. The matrix is computed once and reused across all nine subproblems,
so this is the one long-running step in the pipeline. It is cached on disk and keyed
on dataset / candidate-set / sampling-profile / strategy / radius, so re-running is
free unless one of those changed.

    python scripts/build_matrix.py --input outputs/synthetic_full.geojson \
        --radius 400 --workers 8

Storage is dense: n_candidates x ceil(n_samples/64) uint64 words. At full scale that
is ~2.76 GB on disk, which stays in page cache on a 24 GB host.
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from giscup.candidates import generate_boundary_candidates, prune_candidates  # noqa: E402
from giscup.io import load_buildings  # noqa: E402
from giscup.matrix import build_visibility_matrix  # noqa: E402
from giscup.sampling import get_profile, sample_boundaries  # noqa: E402

DEFAULT_CACHE = "outputs/cache"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--input", required=True)
    parser.add_argument("--radius", type=float, required=True, help="Cull radius in CRS units (metres)")
    parser.add_argument("--sampling-profile", default="balanced")
    parser.add_argument("--candidate-mode", default="basic")
    parser.add_argument("--candidate-spacing", type=float, default=25.0)
    parser.add_argument(
        "--candidate-stride",
        type=int,
        default=1,
        help=(
            "Keep every Nth candidate within each building (task #9). Must match the "
            "stride the solver will run at -- the candidate set is part of the cache "
            "key, so a mismatch rebuilds rather than reuses."
        ),
    )
    parser.add_argument("--visibility-strategy", default="relate")
    parser.add_argument("--eps", type=float, default=1e-9)
    parser.add_argument("--workers", type=int, default=8)
    parser.add_argument("--cache-dir", default=DEFAULT_CACHE)
    parser.add_argument("--rebuild", action="store_true", help="Ignore any cached matrix")
    args = parser.parse_args(argv)

    t0 = time.perf_counter()
    buildings, info = load_buildings(args.input)
    profile = get_profile(args.sampling_profile)
    samples = sample_boundaries(buildings, profile)
    candidates = prune_candidates(
        generate_boundary_candidates(
            buildings, mode=args.candidate_mode, candidate_spacing=args.candidate_spacing
        ),
        stride=args.candidate_stride,
    )
    print(f"dataset      : {info.path}")
    print(f"CRS          : {info.crs}")
    print(f"buildings    : {len(buildings):,}")
    print(f"samples      : {len(samples):,}  (profile {args.sampling_profile})")
    print(f"candidates   : {len(candidates):,}  (mode {args.candidate_mode}, stride {args.candidate_stride})")
    print(f"setup        : {time.perf_counter() - t0:.1f} s\n")

    matrix = build_visibility_matrix(
        buildings,
        candidates,
        samples,
        radius=args.radius,
        strategy=args.visibility_strategy,
        eps=args.eps,
        workers=args.workers,
        cache_dir=args.cache_dir,
        rebuild=args.rebuild,
        progress=True,
    )

    print(f"\nkey          : {matrix.spec.key}")
    print(f"cached       : {matrix.loaded_from_cache}")
    print(f"bits file    : {matrix.bits_path(args.cache_dir)}")
    per_candidate = matrix.nonzeros() / max(matrix.n_candidates, 1)
    print(f"mean visible samples per candidate : {per_candidate:.1f}")
    print(f"total elapsed: {(time.perf_counter() - t0) / 60:.1f} min")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
