# GIS Cup Competition Reference

This is the compact operational reference for official constraints. If anything here conflicts with the official page, the official page wins.

Official page: `https://sigspatial2026.sigspatial.org/giscup.html`

**Re-verified against the live page 2026-08-10 — zero drift.** All five dates, the three-lines-per-
subproblem format, three taus x three ks, IEEE-754 doubles, and the no-holes/no-self-intersection
statement all match this file verbatim. Two operational facts recorded from that check:

- *"Participants will have 24 hours to run their programs and submit their results for each of the
  nine combinations."* — the window is 24 h, and it is per-submission, not per-subproblem.

**Re-checked again 2026-08-15 (release day). Three things that were open are now closed, and one
new artifact appeared:**

- **The submission link is published: EasyChair**,
  `https://easychair.org/conferences/?conf=giscup2026`. An account is required. The archive may be
  `.zip`, `.tgz`, `.tar`, or `.gz` and holds the solution text file plus a source folder with
  build/run instructions. *(Was "still unpublished" until today.)* Break-glass contacts remain
  `alowe@esri.com`, `ashashidharan@esri.com`.
- **The building ID field is named: `properties.id`, required unique.** *(Was "absent from the
  page".)* This does **not** retire `giscup inspect` on the day — the page naming a field is not the
  same as the extract carrying it, and the silent row-index fallback is still the failure that would
  make every claim reference a nonexistent building. Confirm against the file.
- **The dataset ships a companion `competition-parameters.txt`.** The taus and ks are therefore
  *published data*, not a documented constant. See "Final subproblems" below.
- **The official evaluator is source-available**, MIT: `https://github.com/alowe/gis-cup-2026-evaluator`.
  See the section below — this is a genuine change in what can be known before submitting.

## The official evaluator — added 2026-08-15

`https://github.com/alowe/gis-cup-2026-evaluator` (MIT) **is** the scorer. It sits between tier 1
and tier 2 of CLAUDE.md's source-of-truth order: it is more specific than the page's prose and it is
the thing that actually assigns the score, so where it and our reading of the rules disagree, **it
wins**. Where it and the *page* disagree, the page is still the specification and the gap is worth
escalating rather than silently coding to.

It runs headless under vitest — see `scripts/official_evaluator/README.md`. Facts confirmed by
reading the source on 2026-08-15, each of which contradicted or sharpened something in this repo:

| fact | source | our previous belief |
|---|---|---|
| Boundary tolerance is **`0.001` m**; within it an antenna is **snapped and accepted** | `constants.ts` `SPATIAL_TOLERANCE_METERS` | `1e-8`–`1e-7`, and assumed to be a *rejection* threshold |
| Beyond 1 mm: `ANTENNA_OFF_BOUNDARY`, visibility lost, **still counts against `k`** | `submission-validator.ts` | unknown |
| **Only claimed buildings are evaluated** | `evaluation-engine.ts` `initializeEvaluationState` | assumed all buildings were checked |
| Antennas past `k` are **truncated, first-`k` wins**, no backfill | `solution-parser.ts` `antennas.slice(0, k)` | unknown |
| Unknown claimed IDs are a **warning**, excluded, not fatal | `submission-validator.ts` `resolveClaims` | assumed fatal |
| Duplicate antennas **count toward `k`** but reuse visibility | `submission-validator.ts` | unknown |
| The loader **rejects hole-bearing polygons outright** | `dataset-loader.ts` `HOLES_NOT_ALLOWED` | we preserved holes as obstacles |
| Verification is `visibleLengthMeters >= tau * perimeterMeters` | `evaluation-engine.ts:277` | matches ours |
| Building IDs are canonicalised as `String(input).trim()` | `dataset-loader.ts` | matches ours |

The **implication of the 1 mm tolerance is that our eps is fine and should not be relaxed**: passing
at `1e-7` implies passing at `1e-3`. Do not loosen a tolerance to match a looser official bar.

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

**The real values arrive in `competition-parameters.txt`, shipped with the dataset** (confirmed
2026-08-15). Read it before solving; it outranks the values above. Since 2026-08-15 nothing
downstream hardcodes them — `giscup.assemble.subproblem_grid(taus, ks)` is the single source, and
`solve-all`, `scripts/audit_submission.py`, and `scripts/assemble_blocks.py` all take `--taus`/`--ks`.
Lever A's quantile schedule is a function of tau (`optimize.default_near_tau_quantile`) and adapts
on its own.

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

**Building IDs come from the `--id-property` field, default `id`** — and the official page named
`properties.id` on 2026-08-15, so the default is very likely right. If that field is absent, IDs
fall back to the row index — legitimate for a dataset with no ID field, catastrophic otherwise,
because every claim would be wrong while the output still passes every structural check. The
official evaluator would report this as a pile of `UNKNOWN_BUILDING_ID` warnings and a near-zero
score, **not** as an error.

**The fallback is visible on stderr only.** *(Corrected 2026-08-15.)* This section previously said
it "sets `DatasetInfo.id_fallback_used`, surfaced in diagnostics". The flag exists on the dataclass,
but `diagnostics.dataset_summary` does not emit it — the JSON carries `path, crs, feature_count,
geometry_types, id_property, bounds, holes_count, area, perimeter, exterior_vertices`, and its
`id_property` is only an echo of the argument. The real signal is a `UserWarning` from `io.py:15-23`.
**Run `giscup inspect` on the August dataset before solving, and capture stderr** — absence of that
warning is the test.

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
disagreed.

**Settled by evidence 2026-08-15: the page is right and our copy of the sample is the outlier.**
The official evaluator's loader rejects hole-bearing polygons outright. Feeding it
`data/GIS-cup-sample-dataset.geojson` produces:

```
DatasetValidationError: Building "9448" must contain exactly one ring and no holes.
{ code: 'HOLES_NOT_ALLOWED', featureIndex: 9447, buildingId: '9448' }
```

The evaluator ships its own copy of the same sample with that hole removed — the two files differ by
216 bytes. So "the polygons will not have holes" is not aspirational prose; it is enforced by the
scorer, and a hole-bearing dataset is one the organisers' own tooling cannot load.

**Operational consequence:** `holes_count > 0` on the August extract is a **stop-and-escalate**, not
a note. It would mean the published dataset cannot be scored, which is an upstream problem, not one
to fix locally by stripping rings. See the runbook §2.

The 2026-08-07 reasoning below is retained because its conclusions still hold and its defensive
behaviour is still what the code does:

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
