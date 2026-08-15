# mz_giscup_26 — ACM SIGSPATIAL 2026 GIS Cup

A solver for the 2026 GIS Cup antenna-placement problem: given a set of building
footprints, place **exactly `k` antennas on building boundaries** so as to maximize the number
of buildings whose visible perimeter fraction is at least `tau`.

The competition poses nine independent subproblems — three thresholds crossed with three antenna
budgets — and scores them relatively, so a subproblem that fails to finish is worth approximately
nothing. That fact drove most of the engineering here: this repository is organized around
*proving* that a full nine-block run completes inside the submission window, and only then around
making its answers better.

---

## The problem, stated precisely

Given building footprints `B`, a threshold `tau`, and a budget `k`:

- Choose a set `A` of exactly `k` points, each lying on the boundary of some building in `B`.
- A point `p` on a building's boundary is **visible** if the open segment from `p` to some antenna
  in `A` does not pass through the *interior* of any footprint. Tangency, vertex contact, and
  boundary-only contact do **not** block visibility.
- A building is **serviced** when its visible boundary length divided by its total perimeter is
  at least `tau`.
- Maximize the number of serviced buildings.

Two properties make this harder than it first reads. The objective is a coverage function over a
continuous domain — every point of every boundary, not a finite set of targets — so the visible
fraction has to be either sampled or integrated exactly. And antennas must sit *on* boundaries,
which means the candidate set is itself continuous and must be discretized before any combinatorial
method can touch it.

## Approach

The pipeline is five stages, each of which is a separate module and separately tested:

1. **Sampling** (`sampling.py`) — weighted points along every boundary, including interior rings,
   at a density chosen so that the sampled coverage fraction tracks the true one.
2. **Candidate generation** (`candidates.py`) — antenna positions derived from boundary vertices and
   edge subdivisions, deduplicated, with an optional per-building stride for pruning.
3. **Visibility matrix** (`matrix.py`) — a dense bitset of `candidate x sample` visibility, built in
   parallel, radius-culled, memory-mapped, and cached on disk under a key covering the dataset
   digest and every parameter that could change the answer.
4. **Optimization** (`optimize.py`) — greedy maximum-coverage selection over the matrix, driven by
   popcount marginal gains. Two objectives ship (see below).
5. **Verification** (`verify.py`, `exact_coverage.py`) — near-threshold buildings are re-measured
   with a grid-free exact visible-interval computation at a wider radius than the solver used, so a
   building is only claimed if it survives a stricter test than the one that selected it.

### Two objectives, both implemented

`--objective near-tau` (the default) biases greedy toward buildings already close to the threshold,
on the theory that marginal boundary length is worth more where it can actually flip a building into
service. `--objective baseline` is plain coverage maximization. Neither dominates: on the March
sample, `near-tau` wins eight of nine blocks and measurably *loses* one, so the escape hatch is
load-bearing rather than vestigial.

### Radius culling

Visibility is only computed within a cull radius (400 m in the shipped configuration). This is a
heuristic and is documented as one. It is bounded, though: the verification pass re-measures
near-threshold buildings at double the radius, so the buildings that actually decide the score are
the ones that get the wide view.

---

## Correctness posture

The competition's scoring is unforgiving in specific ways, and most of this repository's test
surface exists to hold particular lines against them.

**Exactly `k` points.** Extra points are truncated to the first `k` rather than rejected, and an
invalid early point is not backfilled — so an off-by-one silently discards a real antenna.
`output.py` enforces the count as a hard guard.

**Coordinates are emitted at full precision.** `format(x, ".17g")` — seventeen significant digits,
enough to round-trip an IEEE-754 double exactly. Rounding to six decimals can move an antenna off
the boundary it was placed on, which forfeits it.

**Every geometric tolerance is absolute, in CRS units.** This one is worth spelling out, because
getting it wrong is silent. The sample data is UTM 11N, with northings around 3.7e6. NumPy's
`allclose`/`isclose` default to a *relative* tolerance of `1e-5`, which at that magnitude is
**37 metres** — enough to declare a 16 m building edge zero-length, or to call a 37 m gap in a ring
"closed". Likewise `buffer(-1e-9)` collapses whole footprints to empty, because 1e-9 is below
float64's relative resolution there; `buffer(-1e-6)` is correct. Unit-square tests cannot see any of
this, which is why `tests/test_projected_tolerances.py` works at real projected magnitudes with
irregular coordinates.

**Interpolated points land off the line.** A midpoint `(p0 + p1) / 2` sits an ULP away from the true
segment and therefore falls *inside* the polygon roughly half the time. Predicates have to tolerate
that and emitted antennas have to be nudged out of it — `tests/test_antenna_placement.py` and
`tests/test_boundary_jitter.py` pin both halves.

**Claims are verified before they are made.** Under the official scoring rules only *claimed*
buildings are evaluated, so overclaiming is the only way to lose points and underclaiming is free.
`scripts/audit_submission.py` re-derives every claim independently of the solver, using a cheap
screen followed by a wide confirmation pass.

---

## Validation

The organisers' evaluator is source-available (`github.com/alowe/gis-cup-2026-evaluator`, MIT) and
runs headless here via `scripts/official_evaluator/`. It was validated against every expected result
it ships before being trusted, then run against a full nine-block solution for the March sample
dataset:

| | result |
|---|---|
| claims made | 42,728 |
| claims verified by the official evaluator | **42,728** |
| overclaims | **0** |
| unknown building IDs | **0** |
| antennas rejected as off-boundary | **0** |

That is a statement about the *predicate*, not about rank — scoring is relative, and no local
measurement can see what anyone else submitted. What it does establish is that nothing will be lost
to a disagreement about whether a building is serviced.

---

## Installation

Requires Python 3.11+, NumPy 2.0+ (for `np.bitwise_count`), Shapely 2.x, GeoPandas, and SciPy.

```bash
conda env create -f environment.yml
conda activate mz-giscup-26
pip install -e .
```

Or with pip alone:

```bash
pip install -r requirements.txt
pip install -e .
```

Verify:

```bash
python -m pytest -q
```

## Usage

Inspect a dataset first — this confirms the CRS, the geometry types, the building-ID property, and
whether any footprint carries holes:

```bash
giscup inspect --input path/to/dataset.geojson
```

> The ID property matters more than it looks. If the named property is missing, the loader falls
> back to the row index and warns **on stderr only** — at which point every claim references a
> building that does not exist while passing every structural check. Capture stderr.

Solve a single subproblem:

```bash
giscup solve-one --input path/to/dataset.geojson \
    --tau 0.49 --k 49 \
    --output solution.txt --diagnostics diagnostics.json
```

Solve a full nine-block grid:

```bash
giscup solve-all --input path/to/dataset.geojson \
    --taus 0.32 0.49 0.68 --ks 9 49 484 \
    --visibility-radius 400 \
    --cache-dir outputs/cache --matrix-workers 8 \
    --verify-band 0.10 --verify-max-buildings 2000 --verify-workers 12 \
    --output solution.txt --diagnostics diagnostics.json
```

The `(tau, k)` grid is competition-published data rather than a constant, so it is an argument
everywhere it appears — nothing in the codebase hardcodes the nine subproblems.

`--visibility-radius` and `--cache-dir` are effectively required at full scale: without a radius the
solver recomputes visibility on every greedy iteration. `--matrix-workers` defaults to 1 and wants
raising. Partial output is written after every completed block, and `scripts/assemble_blocks.py`
merges a re-solve of only the missing blocks.

Validate a solution against a dataset:

```bash
giscup validate-output --input path/to/dataset.geojson --solution solution.txt
```

## Output format

Three lines per subproblem, nine subproblems, no separators:

```text
(tau, k)
x1 y1 x2 y2 ... xk yk
id1 id2 id3 ...
```

The third line may be empty but must still be present.

---

## Scale

The competition extract is roughly four times the published sample, and the visibility matrix grows
with the product of candidates and samples:

| | sample | competition extract |
|---|---|---|
| buildings | 12,860 | 50,000 |
| antenna candidates | 157,454 | 613,666 |
| boundary samples | 133,417 | 512,589 |
| visibility matrix @ 400 m | 2.63 GB | 39.3 GB |

A 39.3 GB matrix on a 24 GB machine looks like a hard stop and is not one. The greedy loop walks the
memory map **sequentially**, in 4096-row chunks, which kernel readahead predicts perfectly — measured
scan rates were 4.07 GB/s with pages cached and 4.09 GB/s with pages actively dropped, against 4.2
GB/s raw sequential disk. The workload is bandwidth-bound, not residency-bound. Had the access
pattern been random, the same ratio would have been fatal; the access pattern, not the ratio, is what
decides it.

## Repository layout

```text
src/giscup/        solver library -- see docs/codebase-map.md for a per-module map
scripts/           audit, packaging, rehearsal, block assembly, official-evaluator driver
tests/             32 test files, run with `python -m pytest -q`
docs/              competition reference, engineering decisions, operational runbooks
configs/           example experiment configuration
```

### Documentation

- `docs/competition-reference.md` — the official constraints, format, and scoring rules
- `docs/reference/geometry-and-scoring-rules.md` — the geometric predicates in detail
- `docs/codebase-map.md` — module-by-module map and the current implementation limits
- `docs/task-board.md` — the full decision history, including the measurements that closed each
  question and the ones that reversed an earlier conclusion
- `docs/original_implementation_brief.md` — the original specification, preserved unedited

`docs/task-board.md` and `docs/session-state.md` are working engineering logs rather than polished
prose. They are kept because the reasoning behind a rejected option is usually more useful than the
conclusion, and because several conclusions in this project were reversed by measurement — the record
of *which* ones is the point.

## Implementation state

`greedy` is the only search implemented. `lazy-greedy`, `stochastic-greedy`, and `hybrid` appear
nowhere in the codebase; unimplemented modes raise rather than silently falling back. Both
objectives (`near-tau`, `baseline`) are implemented and tested. Current limitations are tracked in
`docs/codebase-map.md`.

## License

MIT. Copyright (c) 2026 Marko Zlatic. See `LICENSE`.
