# GIS Cup Competition Reference

This is the compact operational reference for official constraints. If anything here conflicts with the official page, the official page wins.

Official page: `https://sigspatial2026.sigspatial.org/giscup.html`

## Event

- Competition: 2026 GIS Cup
- Conference: 34th ACM SIGSPATIAL International Conference on Advances in Geographic Information Systems
- Location: Riverside, CA, USA
- Conference dates: Tuesday Nov 3 – Friday Nov 6, 2026

## Task

Input:

- `B`: building footprints in 2D Euclidean/projected coordinates
- `tau`: threshold, `0 < tau <= 1`
- `k`: number of antennas

Output:

- Set `P` of exactly `k` antenna points.
- Every point must lie on a building boundary.
- Maximize number of serviced buildings.

## Visibility

Point `p` is visible from `q` if the segment `pq` does not intersect any building interior.

Important edge cases:

- Tangency does not block.
- Vertex touch does not block.
- Boundary-only contact does not block.
- Interior intersection blocks.
- Same-building self-blocking matters if the segment from one side to another enters the building interior.

## Segment/building coverage

- Segment visibility is continuous: every point along the segment must be visible from at least one antenna.
- Building coverage is visible boundary length divided by total perimeter.
- A building is serviced when coverage `>= tau`.

## Final subproblems

The final contest is expected to provide:

- one dataset `B`;
- three threshold values;
- three antenna counts;
- all 3 × 3 = 9 subproblem combinations.

Sample-page values are examples only:

- `tau`: `0.25`, `0.5`, `0.75`
- `k`: `50`, `500`, `1000`

## Submission format

For each subproblem, output exactly three lines:

```text
(tau, k)
(x1, y1), (x2, y2), ..., (xk, yk)
id1, id2, id3, ...
```

The third line may be empty if no buildings are claimed, but the line itself must still exist.

## Output format contract — audited 2026-08-08

Verified against the official page, then against 9,300 emitted coordinates from a real
nine-block run. Everything below is either **spec-confirmed** or a **labelled assumption**.

Spec-confirmed:

- **"There should be three lines for each of the 9 sub-problems."** Nine blocks, 27 lines,
  **no blank separators**. Separators are not merely untidy: the spec also allows an empty
  third line, so a block claiming nothing followed by a separator yields two consecutive
  blank lines that no parser can attribute. Fixed 2026-08-08; files written before that
  carry separators and need `--normalize-legacy`.
- Line 2 is "a comma-separated list of the k coordinates ... `(x1, y1), (x2, y2), ...`".
- Line 3 is "a comma-separated list of the ID of each building you claim is serviced".
- "Results remain at 64-bit precision; we will be using standard IEEE 754 doubles."
  `format(x, ".17g")` is correct: 17 significant digits is the guaranteed round-trip width
  for float64. Verified — 9,300 coordinates re-emit bit-identically.

Assumptions, because the page is silent on each:

- **Block order** is tau-outer, k-inner, matching the order arguments are supplied. The page
  states no required order; an evaluator almost certainly keys on the `(tau, k)` header.
- **Claim IDs are emitted sorted numerically.** No order is required. Sorting is free, and
  it makes the file reproducible — the bundle ships source, so an evaluator may re-run and
  diff. Before 2026-08-08 the order was incidental (`list(set)` in `verify.py`).
- **ASCII, LF line endings, trailing newline at EOF.** Verified present; not required.
- `.17g` emits scientific notation below ~1e-4. Harmless for projected coordinates and our
  own parser round-trips it, but it would appear if the test data used small magnitudes.

Verified clean on the real nine-block run: exactly `k` points per block, zero duplicate
antennas, zero claimed IDs absent from the dataset, no CRLF, no tabs, no trailing spaces,
no non-ASCII bytes.

**Building IDs come from the `--id-property` field, default `id`.** If that field is
absent, IDs fall back to the row index — legitimate for a dataset with no ID field,
catastrophic otherwise, because every claim would be wrong while the output still passes
every structural check. Since 2026-08-08 this warns and sets
`DatasetInfo.id_fallback_used`, surfaced in diagnostics. **Run `giscup inspect` on the
August dataset before solving** and confirm the ID field name.

## Precision

- Preserve 64-bit precision.
- Store coordinates as Python floats / NumPy float64.
- Emit coordinates with `format(x, ".17g")`.
- Do not round to six decimals.
- Avoid reprojection, snapping, or normalization in final output unless explicitly required by official rules.

## Scoring

For each subproblem:

```text
points = team service score / highest service score among all submitted answers
```

Total score is the sum across nine subproblems.

## Dates

- Sample dataset: March 31, 2026
- Test dataset / competition begins: August 15, 2026
- Submission deadline: August 16, 2026
- Final results / invited-paper notifications: September 15, 2026
- Invited-paper deadline: 11:59 PM AoE, September 30, 2026

## Dataset handling

Official page, verbatim (re-checked 2026-08-07): **"the polygons will not self-intersect and
will not have holes."** Coverage is **"the ratio of the length of visible segments on the boundary
to the total perimeter of b."**

The preserved sample inspection reports one hole-containing polygon (id 9448), so the sources
disagree. Resolved 2026-08-07 (task #11):

- **On official data the question is moot.** With no interior rings, `polygon.length` (all rings,
  what `sampling.py` uses) and exterior-only perimeter are the same number. The two readings can
  only diverge on a hole-bearing polygon, which the official spec says will not occur.
- **The defensive behaviour stays**, because the sample contradicts the page and costs nothing:
  sampling includes all Shapely boundary rings so the represented weight matches
  `Building.perimeter == polygon.length`.
- **Recorded assumption:** if a hole-bearing polygon does appear, our coverage denominator
  includes the hole perimeter while `candidates.py` generates candidates only from
  `exterior_edges`. Coverage for that building is therefore **underestimated**. That is the safe
  direction — it can only forfeit a claim, never produce an overclaim that invalidates a block.
  Cost is bounded by the number of hole-bearing polygons (one, in the sample).
- Avoid relying on hole-boundary antenna placement unless official clarification supports it.
