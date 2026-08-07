# Research Synthesis Notes

This file stores durable project-specific synthesis produced by the `geospatial-scientist` agent. Keep it concise and implementation-oriented.

## Current High-Level Synthesis

The GIS Cup problem is best treated as a perimeter-guarding variant with polygonal obstacles:

- **Official objective:** maximize thresholded building service count, not raw visible perimeter.
- **Continuous problem:** visibility and coverage are continuous along building boundaries.
- **Practical model:** discretize boundaries into weighted samples, then solve a maximum-coverage-style problem with a cardinality constraint.
- **Risk:** sampled coverage can overclaim buildings near `tau`; dense final validation and claim margins are necessary.

## July 2026 Official-Page Resynthesis

The official GIS Cup page was rechecked during the resynthesis. Current official facts:

- The contest is in 2D Euclidean space using building footprints.
- Antennas must be placed on building sides/perimeters/boundaries.
- Point visibility is blocked only by intersection with a building interior; tangency, vertex contact, and boundary-only contact do not block visibility.
- Segment visibility is continuous: every point along the segment must be visible from at least one antenna.
- Building coverage is visible boundary length divided by total perimeter.
- Service score is the number of buildings with coverage at least `tau`.
- Final evaluation will have one dataset, three `tau` values, three `k` values, and therefore nine subproblems.
- Output requires three lines per subproblem and coordinates must preserve IEEE-754 double precision.

The official page says datasets are simplified simple polygons without holes. The project still keeps defensive hole handling because the preserved sample-dataset inspection reported one hole anomaly. Official rules win if future clarification conflicts with the local anomaly.

## Mathematics Map

### Visibility Geometry

Core issue: a line segment is blocked only if it intersects a building interior. This makes boundary degeneracies central:

- Tangency must remain visible.
- Vertex contact must remain visible.
- Boundary overlap must remain visible unless the segment enters interior.
- Same-building self-blocking must be considered because an antenna on one side may not see the opposite side.

Implementation impact:

- Keep multiple predicate strategies in `src/giscup/visibility.py`.
- Test every official degeneracy before optimizing performance.
- Consider exact/robust predicates or controlled epsilon strategies if Shapely predicates disagree with expected semantics.
- Add robust-predicate research before implementing any custom non-GEOS predicate; Shewchuk-style adaptive predicates are now listed as a P1 candidate in `docs/reference/research-papers.md`.

### Discretization

The continuous perimeter objective is approximated through weighted boundary samples. This converts the problem into a finite candidate/witness model:

- antenna candidates are guards;
- boundary samples are witnesses;
- sample weights approximate visible boundary length;
- building service is a grouped threshold over weighted witnesses.

Implementation impact:

- `src/giscup/sampling.py` owns witness generation.
- `src/giscup/candidates.py` owns guard generation.
- `src/giscup/coverage.py` owns grouped weighted coverage.
- Adaptive refinement should focus on buildings near `tau`.
- Hole handling must keep sample weights and perimeter denominators consistent. The current default samples all Shapely boundary rings to match `polygon.length`; antenna candidates remain exterior-derived unless official expectations for hole-boundary antennas are clarified.

### Optimization

The service objective is thresholded and therefore not identical to plain maximum coverage. A useful practical objective should reward:

- newly serviced buildings;
- progress toward `tau`;
- complementary coverage for near-threshold buildings;
- spatial diversity and reduced redundancy.

Implementation impact:

- Baseline greedy is useful for correctness but not final performance.
- Lazy greedy and stochastic greedy should be added for larger candidate pools.
- Local search should focus on low-unique-contribution selected antennas and candidates near near-threshold buildings.
- Until lazy/stochastic/hybrid optimizers are implemented, CLI/configs should not silently accept those names as if they were implemented.

## Paper-by-Paper Implementation Synthesis

### Art-gallery and visibility foundations

- **O'Rourke, Art Gallery Theorems and Algorithms:** Use as conceptual foundation for guarding, triangulation, visibility graphs, and exterior/prison-yard variants. Do not assume classical interior-guard theorems transfer directly to GIS Cup perimeter coverage.
- **Ghosh, Visibility Algorithms in the Plane:** Treat as authoritative background for planar visibility algorithms, but full text was not accessible during this session. Keep as P0, access-limited.
- **Handbook of Discrete and Computational Geometry:** Use for robust computational geometry, visibility, and approximation framing; prefer implementation-specific sources before coding exact predicates.
- **de Berg et al., Computational Geometry:** Use for segment intersection, range searching, arrangements, and visibility graph concepts. Supports future angular sweep or point-location acceleration.

### Approximation and discretization

- **Bonnet & Miltzow:** Reinforces that point-guard art gallery variants are hard and approximation-sensitive; useful for understanding why discretized candidate/witness models need conservative validation.
- **Deshpande et al.:** The subdivision-to-finite-guard-set and set-cover framing is directly analogous to candidate antenna generation plus boundary witnesses.
- **Ghosh approximation paper:** Connects art-gallery approximation, visibility polygons, set cover, and greedy algorithms. It supports using guard/witness reductions but does not solve GIS Cup's grouped threshold objective.
- **AGP status survey:** Highlights hardness, irrational guard placements, witness-set issues, and approximation results. Practical lesson: do not overclaim theoretical optimality from a finite candidate set.

### Sensor, access-point, and camera placement

- **Gadiraju et al.:** Potentially relevant for AP placement in arbitrary polygonal environments, but IEEE access was blocked; keep as an access-limited lead.
- **Mikula & Kulich:** Strong practical relevance. Their hybrid accelerated-refinement framing supports multi-start candidate filtering, greedy baselines, and local refinement after correctness is stable.
- **Tossa et al.:** Connectivity-constrained WSN coverage is background only; connectivity is not part of official GIS Cup scoring.
- **Pålsson thesis:** Useful software-engineering analogy for camera placement with obstacles and coverage thresholds. Practical but not authoritative for official scoring.
- **Fleishman and Vázquez view-selection papers:** Useful for redundancy and viewpoint-quality heuristics, especially high-`tau` complementary coverage, but they are not geometry-scoring sources.

### Greedy and submodular optimization

- **Mirzasoleiman et al.:** Supports stochastic/lazier greedy as a future scalability path for large candidate pools. Apply only after the marginal objective is shaped around weighted progress and service thresholds.
- **Krause et al.:** Supports diminishing-returns thinking, greedy baselines, and comparing greedy to local search. Not all GIS Cup objectives are submodular, especially thresholded grouped service.
- **Shamaiah et al.:** Reinforces cardinality-constrained greedy selection concepts; the estimation model is not GIS Cup, so use as theoretical analogy.
- **Nemhauser/Wolsey/Fisher candidate:** Add as a future foundational source for monotone submodular greedy guarantees.

### Wireless LOS and urban blockage

- **Urban mmWave and UAV LOS papers:** Keep as P2 geographic/blockage intuition only. Reflections, path loss, antenna heights, relay positions, and 3D effects are out of scope unless official rules change.

## Resynthesis-Driven Code/Documentation Corrections

The resynthesis identified and addressed these scaffold-level issues:

- malformed solution headers could cause validation to loop indefinitely;
- solver/output could permit fewer than exactly `k` antenna points;
- sampled validation did not check claimed service coverage;
- hole boundary sampling did not match Shapely perimeter denominators;
- unimplemented optimizer names were accepted without warning;
- agent coverage lacked performance, dataset-QC, experiment, and submission-packaging roles.

## Geography / GIS Map

- The sample brief indicates projected meter coordinates in EPSG:32611 / UTM Zone 11N.
- Code must inspect CRS and preserve coordinates rather than assuming longitude/latitude.
- Distance, perimeter, spacing, and sample weights are meaningful only in projected units.
- Building density, urban block structure, and local occlusion patterns can inform candidate pruning, but must remain heuristics.

## Open Research Tasks

1. Read the new robust-predicate candidate source before implementing custom predicate logic.
2. Read the new visibility-polygon candidate source before replacing STRtree + segment checks.
3. Convert P1 optimization sources into a concrete shaped-objective design for `optimize.py`.
4. Evaluate whether visibility-polygon or angular-sweep methods can accelerate candidate-to-sample visibility.
5. Identify robust exact-predicate strategies compatible with Shapely/GEOS and Python performance constraints.
