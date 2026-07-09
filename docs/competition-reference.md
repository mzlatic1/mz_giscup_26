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

Official page says building footprints are simplified simple polygons without holes. The preserved sample inspection reports one hole-containing polygon. Therefore:

- Code should defensively preserve holes.
- Official rules and final evaluator expectations take precedence.
- Current sampling includes all Shapely boundary rings to match `polygon.length`.
- Candidate antennas currently remain boundary-derived; avoid relying on hole-boundary antenna placement unless official clarification supports it.
