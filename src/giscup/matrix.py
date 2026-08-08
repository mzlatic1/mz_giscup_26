"""Radius-culled, cached visibility matrix.

The matrix is the core feasibility device (task board #2). Without it the solver
recomputes every candidate's visible set on every greedy iteration, which projects
to ~666,000 days for the nine subproblems. Two compounding effects fix that:

1. A candidate's visible set never changes during greedy -- only the covered union
   subtracted from it does. Computing the set once removes the `k` factor entirely.
2. Visibility-check throughput scales inversely with blockers per STRtree query,
   which scales with segment length. Restricting to pairs within a cull radius took
   measured throughput from ~550 to ~17,500 checks/s at 400 m.

Storage is a dense bit matrix, candidate-major: bit `s` of row `c` is set when
candidate `c` can see sample `s`. Rows are `uint64` words, so marginal gains are a
hardware popcount of `row & ~covered`.

The matrix is memmap-backed. That makes it survive across the nine subproblems and
across processes, and lets parallel workers write disjoint candidate ranges into one
file rather than shipping gigabytes back through pickle.

Bit layout is little-endian: sample `s` lives in word `s >> 6` at bit `s & 63`.
`visible_sample_ids` unpacks with `bitorder="little"`, which matches that layout only
on a little-endian host; `_check_byteorder` enforces it.
"""

from __future__ import annotations

import hashlib
import json
import math
import multiprocessing as mp
import os
import sys
import time
from dataclasses import asdict, dataclass
from pathlib import Path

import numpy as np
import shapely
from scipy.spatial import cKDTree

from giscup.models import BoundarySample, Building, Candidate
from giscup.visibility import BlockerIndex, is_visible

BITS_PER_WORD = 64
# Rows processed per marginal-gain chunk. 8192 x 2158 words x 8 B ~ 140 MB of
# temporary, which keeps the intermediate inside cache-friendly territory instead
# of allocating a second copy of the whole 2.76 GB matrix.
GAIN_CHUNK = 8192


def _check_byteorder() -> None:
    if sys.byteorder != "little":
        raise RuntimeError(
            "VisibilityMatrix assumes a little-endian host: the packed bit layout and "
            f"np.unpackbits(bitorder='little') would disagree on {sys.byteorder}-endian."
        )


def _words_for(n_samples: int) -> int:
    return (n_samples + BITS_PER_WORD - 1) // BITS_PER_WORD


def _digest_floats(values: np.ndarray) -> str:
    h = hashlib.blake2b(digest_size=16)
    h.update(np.ascontiguousarray(values, dtype=np.float64).tobytes())
    return h.hexdigest()


def _digest_buildings(buildings: list[Building]) -> str:
    """Exact geometric digest. WKB, so a moved vertex cannot alias to the same key."""
    h = hashlib.blake2b(digest_size=16)
    for wkb in shapely.to_wkb(np.array([b.polygon for b in buildings], dtype=object)):
        h.update(wkb)
    h.update(repr([b.id for b in buildings]).encode())
    return h.hexdigest()


@dataclass(frozen=True, slots=True)
class MatrixSpec:
    """Everything a matrix's validity depends on. Any change must change the key."""

    n_candidates: int
    n_samples: int
    radius: float
    strategy: str
    eps: float
    dataset_digest: str
    candidate_digest: str
    sample_digest: str

    @property
    def words(self) -> int:
        return _words_for(self.n_samples)

    @property
    def shape(self) -> tuple[int, int]:
        return (self.n_candidates, self.words)

    @property
    def key(self) -> str:
        canonical = json.dumps(asdict(self), sort_keys=True, separators=(",", ":"))
        return hashlib.blake2b(canonical.encode(), digest_size=16).hexdigest()

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, payload: dict) -> "MatrixSpec":
        return cls(**{f: payload[f] for f in cls.__slots__})


def _spec_for(
    buildings: list[Building],
    candidates: list[Candidate],
    samples: list[BoundarySample],
    radius: float,
    strategy: str,
    eps: float,
) -> MatrixSpec:
    return MatrixSpec(
        n_candidates=len(candidates),
        n_samples=len(samples),
        radius=float(radius),
        strategy=strategy,
        eps=float(eps),
        dataset_digest=_digest_buildings(buildings),
        candidate_digest=_digest_floats(np.array([[c.x, c.y] for c in candidates])),
        sample_digest=_digest_floats(np.array([[s.x, s.y] for s in samples])),
    )


@dataclass(slots=True)
class VisibilityMatrix:
    """Dense candidate-major bit matrix of sampled visibility."""

    spec: MatrixSpec
    bits: np.ndarray
    loaded_from_cache: bool = False
    build_seconds: float = 0.0

    @property
    def n_candidates(self) -> int:
        return self.spec.n_candidates

    @property
    def n_samples(self) -> int:
        return self.spec.n_samples

    @property
    def words(self) -> int:
        return self.spec.words

    # --- row access ---------------------------------------------------------

    def visible_sample_ids(self, candidate_index: int) -> np.ndarray:
        """Sample ids visible from `candidate_index`, ascending."""
        row = np.asarray(self.bits[candidate_index])
        unpacked = np.unpackbits(row.view(np.uint8), bitorder="little")
        return np.flatnonzero(unpacked[: self.n_samples])

    def is_pair_visible(self, candidate_index: int, sample_index: int) -> bool:
        word = self.bits[candidate_index, sample_index >> 6]
        return bool(word >> np.uint64(sample_index & 63) & np.uint64(1))

    def nonzeros(self) -> int:
        total = 0
        for lo in range(0, self.n_candidates, GAIN_CHUNK):
            block = np.asarray(self.bits[lo : lo + GAIN_CHUNK])
            total += int(np.bitwise_count(block).sum(dtype=np.int64))
        return total

    # --- covered-set algebra for greedy -------------------------------------

    def empty_covered(self) -> np.ndarray:
        return np.zeros(self.words, dtype=np.uint64)

    def add_to_covered(self, covered: np.ndarray, candidate_index: int) -> None:
        covered |= np.asarray(self.bits[candidate_index])

    def covered_count(self, covered: np.ndarray) -> int:
        return int(np.bitwise_count(covered).sum(dtype=np.int64))

    def covered_sample_ids(self, covered: np.ndarray) -> np.ndarray:
        unpacked = np.unpackbits(covered.view(np.uint8), bitorder="little")
        return np.flatnonzero(unpacked[: self.n_samples])

    def marginal_gains(self, covered: np.ndarray, chunk: int = GAIN_CHUNK) -> np.ndarray:
        """Newly visible sample count for every candidate, given `covered`.

        This is the greedy inner loop: one pass over the matrix per iteration,
        chunked so the `row & ~covered` temporary never approaches matrix size.
        """
        inverse = ~np.asarray(covered, dtype=np.uint64)
        gains = np.empty(self.n_candidates, dtype=np.int64)
        for lo in range(0, self.n_candidates, chunk):
            hi = min(lo + chunk, self.n_candidates)
            block = np.asarray(self.bits[lo:hi]) & inverse
            gains[lo:hi] = np.bitwise_count(block).sum(axis=1, dtype=np.int64)
        return gains

    # --- persistence --------------------------------------------------------

    def bits_path(self, cache_dir: str | os.PathLike) -> Path:
        return Path(cache_dir) / f"visibility-{self.spec.key}.bits"

    def meta_path(self, cache_dir: str | os.PathLike) -> Path:
        return Path(cache_dir) / f"visibility-{self.spec.key}.json"


def _bits_path(cache_dir: str | os.PathLike, key: str) -> Path:
    return Path(cache_dir) / f"visibility-{key}.bits"


def _meta_path(cache_dir: str | os.PathLike, key: str) -> Path:
    return Path(cache_dir) / f"visibility-{key}.json"


def load_matrix(cache_dir: str | os.PathLike, key: str) -> VisibilityMatrix:
    """Load a completed cached matrix. Raises if the completion marker is absent."""
    meta_file, bits_file = _meta_path(cache_dir, key), _bits_path(cache_dir, key)
    if not meta_file.exists() or not bits_file.exists():
        raise FileNotFoundError(f"no completed visibility matrix for key {key} in {cache_dir}")
    payload = json.loads(meta_file.read_text())
    spec = MatrixSpec.from_dict(payload["spec"])
    bits = np.memmap(bits_file, dtype=np.uint64, mode="r", shape=spec.shape)
    return VisibilityMatrix(
        spec=spec, bits=bits, loaded_from_cache=True, build_seconds=payload.get("build_seconds", 0.0)
    )


# --- parallel build ---------------------------------------------------------

_SHARED: dict = {}


def _init_worker(payload: dict) -> None:
    """Rebuild per-process spatial indexes. GEOS objects do not survive fork cleanly."""
    _SHARED.update(payload)
    _SHARED["index"] = BlockerIndex.from_buildings(payload["buildings"])
    _SHARED["tree"] = cKDTree(payload["sample_xy"])


def _fill_rows(bounds: tuple[int, int]) -> int:
    lo, hi = bounds
    spec: MatrixSpec = _SHARED["spec"]
    candidates: list[Candidate] = _SHARED["candidates"]
    samples: list[BoundarySample] = _SHARED["samples"]
    index: BlockerIndex = _SHARED["index"]
    tree: cKDTree = _SHARED["tree"]
    strategy, eps, radius = spec.strategy, spec.eps, spec.radius

    bits = np.memmap(_SHARED["bits_file"], dtype=np.uint64, mode="r+", shape=spec.shape)
    one = np.uint64(1)
    found = 0
    for ci in range(lo, hi):
        candidate = candidates[ci]
        point = candidate.point
        neighbours = tree.query_ball_point(point, radius)
        if not neighbours:
            continue
        visible = [
            si
            for si in neighbours
            if is_visible(point, samples[si].point, index, strategy=strategy, eps=eps)
        ]
        if not visible:
            continue
        found += len(visible)
        ids = np.asarray(visible, dtype=np.int64)
        # bitwise_or.at accumulates correctly when several ids share a word.
        np.bitwise_or.at(bits[ci], ids >> 6, one << (ids & 63).astype(np.uint64))
    bits.flush()
    del bits
    return found


def _chunk_bounds(n: int, chunks: int) -> list[tuple[int, int]]:
    if chunks <= 1 or n == 0:
        return [(0, n)]
    size = max(1, (n + chunks - 1) // chunks)
    return [(lo, min(lo + size, n)) for lo in range(0, n, size)]


def build_visibility_matrix(
    buildings: list[Building],
    candidates: list[Candidate],
    samples: list[BoundarySample],
    *,
    radius: float,
    strategy: str = "relate",
    eps: float = 1e-9,
    workers: int = 1,
    cache_dir: str | os.PathLike | None = None,
    rebuild: bool = False,
    progress: bool = False,
) -> VisibilityMatrix:
    """Build (or load) the radius-culled visibility matrix.

    `cache_dir` is required for `workers > 1`: parallel workers coordinate by writing
    disjoint candidate ranges into one memmapped file.
    """
    _check_byteorder()
    if radius <= 0:
        raise ValueError(f"radius must be positive, got {radius}")
    if workers > 1 and cache_dir is None:
        raise ValueError("workers > 1 requires cache_dir; parallel build writes through a memmap")

    spec = _spec_for(buildings, candidates, samples, radius, strategy, eps)

    if cache_dir is not None:
        cache_path = Path(cache_dir)
        cache_path.mkdir(parents=True, exist_ok=True)
        if not rebuild and _meta_path(cache_path, spec.key).exists():
            matrix = load_matrix(cache_path, spec.key)
            if matrix.spec == spec:
                if progress:
                    print(f"visibility matrix: reusing cache {spec.key}")
                return matrix

    start = time.perf_counter()
    if cache_dir is None:
        bits = np.zeros(spec.shape, dtype=np.uint64)
        bits_file = None
    else:
        bits_file = _bits_path(cache_path, spec.key)
        # A stale partial from a crashed run has no completion marker; overwrite it.
        bits = np.memmap(bits_file, dtype=np.uint64, mode="w+", shape=spec.shape)
        bits[:] = 0
        bits.flush()
        del bits

    sample_xy = np.array([[s.x, s.y] for s in samples], dtype=np.float64)
    payload = {
        "spec": spec,
        "buildings": buildings,
        "candidates": candidates,
        "samples": samples,
        "sample_xy": sample_xy,
        "bits_file": str(bits_file) if bits_file else None,
    }

    if progress:
        dense_gb = spec.n_candidates * spec.words * 8 / 1e9
        print(
            f"visibility matrix: {spec.n_candidates:,} candidates x {spec.n_samples:,} samples "
            f"({dense_gb:.2f} GB), radius {radius:g} m, strategy {strategy}, {workers} workers"
        )

    if bits_file is None:
        # Serial, in-memory: no memmap to coordinate through.
        _SHARED.clear()
        _init_worker(payload)
        in_memory = np.zeros(spec.shape, dtype=np.uint64)
        _SHARED["bits_array"] = in_memory
        nonzeros = _fill_rows_in_memory((0, spec.n_candidates), in_memory)
        bits = in_memory
    else:
        bounds = _chunk_bounds(spec.n_candidates, max(1, workers * 4))
        if workers <= 1:
            _SHARED.clear()
            _init_worker(payload)
            nonzeros = 0
            for i, chunk in enumerate(bounds, 1):
                nonzeros += _fill_rows(chunk)
                if progress:
                    _report(i, len(bounds), start, workers)
        else:
            ctx = mp.get_context("fork")
            nonzeros = 0
            with ctx.Pool(workers, initializer=_init_worker, initargs=(payload,)) as pool:
                for i, found in enumerate(pool.imap_unordered(_fill_rows, bounds), 1):
                    nonzeros += found
                    if progress:
                        _report(i, len(bounds), start, workers)
        bits = np.memmap(bits_file, dtype=np.uint64, mode="r", shape=spec.shape)

    elapsed = time.perf_counter() - start
    if cache_dir is not None:
        _meta_path(cache_path, spec.key).write_text(
            json.dumps(
                {
                    "spec": spec.to_dict(),
                    "key": spec.key,
                    "nonzeros": int(nonzeros),
                    "build_seconds": elapsed,
                    "workers": workers,
                    "created": time.strftime("%Y-%m-%dT%H:%M:%S"),
                },
                indent=2,
            )
        )
    if progress:
        density = nonzeros / max(spec.n_candidates * spec.n_samples, 1) * 100
        print(
            f"visibility matrix: built in {elapsed / 60:.1f} min, "
            f"{nonzeros:,} visible pairs (density {density:.5f}%)"
        )
    return VisibilityMatrix(spec=spec, bits=bits, loaded_from_cache=False, build_seconds=elapsed)


def _fill_rows_in_memory(bounds: tuple[int, int], bits: np.ndarray) -> int:
    lo, hi = bounds
    spec: MatrixSpec = _SHARED["spec"]
    candidates = _SHARED["candidates"]
    samples = _SHARED["samples"]
    index = _SHARED["index"]
    tree = _SHARED["tree"]
    one = np.uint64(1)
    found = 0
    for ci in range(lo, hi):
        point = candidates[ci].point
        neighbours = tree.query_ball_point(point, spec.radius)
        visible = [
            si
            for si in neighbours
            if is_visible(point, samples[si].point, index, strategy=spec.strategy, eps=spec.eps)
        ]
        if not visible:
            continue
        found += len(visible)
        ids = np.asarray(visible, dtype=np.int64)
        np.bitwise_or.at(bits[ci], ids >> 6, one << (ids & 63).astype(np.uint64))
    return found


def _report(done: int, total: int, start: float, workers: int = 1) -> None:
    """Progress line with a parallelism-aware ETA.

    Chunks complete in waves of `workers`, so dividing elapsed time by completed
    chunks overstates the remaining time by roughly the worker count until the last
    wave. Estimate in waves instead.
    """
    elapsed = time.perf_counter() - start
    waves_done = max(1, math.ceil(done / workers))
    waves_total = math.ceil(total / workers)
    projected = elapsed * waves_total / waves_done
    remaining = max(0.0, projected - elapsed)
    print(
        f"  chunk {done}/{total}  elapsed {elapsed / 60:5.1f} min  "
        f"eta {remaining / 60:5.1f} min  (total ~{projected / 60:.0f} min)",
        flush=True,
    )
