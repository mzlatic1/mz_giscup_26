# Research Synthesis Brief

This is the compact research digest. Full registry: `docs/reference/research-papers.md`. Durable synthesis: `docs/reference/research-synthesis.md`.

## Core framing

GIS Cup is a perimeter-guarding / maximum-coverage problem with polygonal obstacles:

- Guards = antenna candidate points on building boundaries.
- Witnesses = weighted boundary samples representing perimeter length.
- Obstacles = building interiors.
- Objective = thresholded serviced-building count, not raw visible perimeter.

## Geometry / visibility

Foundational sources:

- O'Rourke, *Art Gallery Theorems and Algorithms*
- Ghosh, *Visibility Algorithms in the Plane* (access-limited in this environment)
- Handbook of Discrete and Computational Geometry
- de Berg et al., *Computational Geometry: Algorithms and Applications*

Implementation takeaways:

- Treat official degeneracies as first-class tests: tangency, vertex touch, boundary overlap, self-blocking.
- STRtree + Shapely predicates are fine for scaffold correctness but must be profiled and stress-tested.
- If custom predicates are needed, first synthesize robust-predicate literature such as Shewchuk.
- If direct candidate-sample checks become too slow, investigate visibility polygons/angular sweep.

## Approximation / discretization

Sources:

- Bonnet & Miltzow
- Deshpande et al.
- Ghosh approximation paper
- AGP survey/status paper

Takeaways:

- The continuous problem is hard; finite candidate/witness discretization is practical but approximate.
- Do not claim theoretical optimality from candidate sets.
- Use dense validation and conservative claim margins near `tau`.
- Adaptive refinement should target near-threshold buildings.

## Sensor/camera/view-placement analogies

Sources:

- Mikula & Kulich: strong practical source for hybrid accelerated refinement.
- Gadiraju et al.: promising but access-limited IEEE lead.
- Pålsson thesis: useful engineering analogy for obstacles and thresholds.
- Fleishman / Vázquez: view quality and redundancy heuristics.

Takeaways:

- Useful for heuristics, multi-starts, local search, and redundancy reduction.
- Do not import camera/radio constraints into official scoring.

## Greedy/submodular optimization

Sources:

- Mirzasoleiman et al., *Lazier Than Lazy Greedy*
- Krause et al., *Near-Optimal Sensor Placements in Gaussian Processes*
- Shamaiah et al., *Greedy Sensor Selection*
- Candidate addition: Nemhauser/Wolsey/Fisher foundational submodular maximization

Takeaways:

- Greedy/lazy/stochastic greedy are appropriate baselines for large candidate pools.
- GIS Cup thresholded grouped service is not plain submodular coverage; shape the objective carefully.
- Reward newly serviced buildings, progress toward `tau`, and complementary near-threshold coverage.

## Wireless LOS / urban blockage

Sources:

- Urban mmWave placement paper
- Geography-aware UAV LOS paper

Takeaways:

- Use only as urban blockage intuition.
- Ignore reflections, path loss, heights, radio physics, relay placement, and 3D unless official rules change.

## Research gaps to address before major algorithm changes

1. Robust predicates for exact boundary/interior semantics.
2. Visibility polygon/angular sweep acceleration.
3. Threshold-aware objective shaping.
4. Bitset/compressed bitmap performance tradeoffs.
5. Candidate pruning with spatial diversity and density awareness.
