# Geometry, Visibility, Precision, and Scoring Rules

## Antenna Legality

- Every output antenna point must lie on a building boundary.
- Generate exact boundary-derived coordinates whenever possible.
- Validate with `polygon.boundary.distance(Point(x, y)) <= eps`.
- Use a small tolerance such as `1e-8` to `1e-7` for validation.
- Do not snap final coordinates unless running an explicit repair step.

## Point Visibility

Point `p` is visible from point `q` if the line segment `pq` does **not** intersect the interior of any building footprint.

Important edge cases:

- Tangency to a building does not block visibility.
- Touching a building boundary at a vertex does not block visibility.
- Boundary-only contact does not block visibility.
- Crossing or lying within a building interior blocks visibility.

## Segment and Building Coverage

- Segment visibility is continuous in the official problem definition.
- The repository approximates continuous visibility using weighted boundary samples.
- Coverage for building `b` is `visible_boundary_length(b) / total_perimeter_length(b)`.
- A building is serviced when coverage is `>= tau`.

## Holes

- The official problem says no holes, but the sample brief notes one sample polygon with a hole.
- Preserve holes in loaded geometries.
- Include holes in obstacle/interior geometry for visibility.
- Default perimeter accounting follows Shapely `polygon.length` unless official clarification requires exterior-only perimeter.

## Precision

- Store coordinates as Python floats / NumPy `float64`.
- Output coordinates with 17 significant digits using `format(x, ".17g")`.
- Do not round final coordinates to six decimals.

## Scoring

For each subproblem:

```text
points = team service score / highest service score among all submitted answers
```

Total score is the sum over all 9 subproblems. Optimize each `(tau, k)` combination independently.

## Documentation Maintenance

If official geometry, visibility, precision, or scoring rules change or are clarified, update `docs/competition-reference.md`, `docs/codex-startup-brief.md`, and `docs/session-state.md` before ending the session. Follow `docs/context-maintenance.md` and repeat QA/QC until the final documentation pass yields no changes.
