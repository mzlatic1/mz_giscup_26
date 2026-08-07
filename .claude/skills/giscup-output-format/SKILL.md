---
name: giscup-output-format
description: The non-negotiable GIS Cup submission output rules — three-line subproblem blocks, exactly-k antenna counts, 17-significant-digit IEEE-754 coordinates, boundary legality, and claimed-serviced-ID validation. Use when writing, parsing, formatting, or validating solution text; when touching src/giscup/output.py, validate.py, or solver.py; when handling coordinate precision or rounding; or when deciding whether a building may be claimed as serviced.
---

# GIS Cup submission output format

These rules are scored. Violating one silently zeroes a subproblem — there is no partial credit
for a block with `k-1` antennas. Never reconstruct these from memory or from a docstring; check
them here.

Authority order: the [official page](https://sigspatial2026.sigspatial.org/giscup.html) outranks
this file. If they disagree, the official page wins and this file is wrong and must be updated.

## Block structure

Nine blocks total (3 `tau` × 3 `k`), each **exactly three lines**, blocks separated by a blank line:

```text
(tau, k)
(x1, y1), (x2, y2), ..., (xk, yk)
id1, id2, id3, ...
```

Line 3 may be **empty** when no buildings are claimed — but the line must still exist. This is the
single most common parsing bug: stripping empty lines destroys valid solutions. `src/giscup/validate.py`
preserves empty claimed-ID lines while skipping blank block separators, and
`tests/test_validate.py` has the regression covering it. Do not "clean up" that logic.

## Exactly k

The coordinate line must contain **exactly `k`** points. Not `k-1`, not `k+1`, and not "as many as
the solver found."

`format_solution_block()` in `src/giscup/output.py:17` raises when
`len(solution.antenna_points) != solution.k`. The solver also rejects `max_candidates < k` and
candidate pools smaller than `k`. Keep both guards — they are the last line of defense against a
silently truncated submission.

If the solver cannot find `k` good positions, it must still emit `k` legal positions. Padding with
redundant-but-legal boundary points scores no worse than a short block; a short block scores zero.

## Coordinate precision

```python
def format_float(value: float) -> str:
    return format(float(value), ".17g")   # src/giscup/output.py:12
```

- Store as Python `float` / NumPy `float64` throughout. No `float32` anywhere in the pipeline.
- Emit with `format(x, ".17g")` — 17 significant digits round-trips an IEEE-754 double exactly.
- **Never** round to six decimals, and never `f"{x:.6f}"` a final coordinate.
- **Never** reproject, snap, or normalize output coordinates. The output CRS is the input CRS.

Precision loss is invisible in testing and fatal in scoring: a coordinate rounded off the boundary
fails the legality check.

## Boundary legality

Every antenna must lie on a building boundary:

```python
polygon.boundary.distance(Point(x, y)) <= eps    # eps in 1e-8 .. 1e-7
```

Generate exact boundary-derived coordinates wherever possible rather than generating-then-snapping.
Do not snap final coordinates outside an explicit, deliberate repair step — snapping after
formatting reintroduces the precision problem above.

## Claimed serviced IDs

A building may be claimed only when it is genuinely serviced:

- Coverage = **visible boundary length / total perimeter** (Shapely `polygon.length`, including
  interior rings — sampling includes holes so sample weights match the perimeter).
- Serviced when coverage `>= tau`.
- Visibility is blocked **only** by a segment intersecting a building **interior**. Tangency,
  vertex contact, and boundary-only contact do not block. A segment crossing the interior of its
  own building does block.

Coverage is approximated by weighted boundary samples, so a claim near `tau` may be an artifact of
sample placement. **Validate at a denser sampling profile than you solved with**, and apply a
conservative claim margin:

```bash
giscup validate-output --input <geojson> --solution <txt> --sampling-profile accurate
```

Overclaiming is worse than underclaiming — an unsupported claim risks the whole block's
credibility, while an unclaimed serviced building costs only that one building.

## Scoring context

```text
points_per_subproblem = team service score / best submitted service score
total = sum over all 9 subproblems
```

Each `(tau, k)` is scored independently. Optimize and validate each one on its own.

## Checklist before declaring output ready

- [ ] All 9 blocks present, none duplicated
- [ ] Each block exactly three lines; third line present even when empty
- [ ] Exactly `k` coordinates per block — counted, not assumed from the header
- [ ] All coordinates at 17 significant digits, no six-decimal rounding
- [ ] All antennas within `eps` of a building boundary
- [ ] Every claimed ID exists in the source dataset
- [ ] Claims validated at `--sampling-profile accurate` with a conservative margin
- [ ] `giscup validate-output` passes and its output was actually read

Never hand-edit a solution file to make validation pass.
