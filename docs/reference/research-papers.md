# Research Paper Registry

This is the fast-parse research registry for the `geospatial-scientist` and `web-searcher` agents. It is shorter than the README and should be updated as the project learns more.

Status values:

- `seed`: copied from the original implementation brief / README, not yet independently inspected.
- `read`: inspected from an accessible primary/source page or PDF and summarized into project context.
- `access-limited`: source page found, but full text was blocked, paywalled, or otherwise not available in this environment.
- `to-read`: credible candidate source recommended for future synthesis.
- `synthesized`: durable project-specific synthesis recorded in `docs/reference/research-synthesis.md`.
- `superseded`: kept for history but no longer a primary source.
- `removed`: no longer recommended; explain why in notes.

Priority values:

- `P0`: foundational for correctness or scoring.
- `P1`: important for competitive implementation.
- `P2`: useful background or optional enhancement.

Source types:

- `survey / textbook`
- `primary research`
- `preprint`
- `thesis`
- `official / publisher page`
- `implementation reference`
- `access-limited lead`

## P0 — Geometry, Visibility, and Art-Gallery Foundations

| ID | Status | Priority | Source type | Access / credibility | Reference | URL | Project relevance |
|---|---:|---:|---|---|---|---|---|
| geom-orourke-art-gallery | read | P0 | survey / textbook | Author-hosted book PDF; foundational but older | Joseph O'Rourke, *Art Gallery Theorems and Algorithms* | https://www.science.smith.edu/~jorourke/books/ArtGalleryTheorems/Art_Gallery_Full_Book.pdf | Guarding theory, visibility geometry, decomposition ideas, degeneracy awareness. Use for concepts, not final implementation recipes. |
| geom-ghosh-visibility | access-limited | P0 | survey / textbook | Cambridge book page/source metadata; full text not accessible here | Subir Kumar Ghosh, *Visibility Algorithms in the Plane* | https://www.cambridge.org/core/books/visibility-algorithms-in-the-plane/ | Visibility algorithms, visibility graphs, obstacle geometry. Use as authoritative reference when accessible. |
| geom-discrete-handbook | read | P0 | survey / textbook | Official/author reference page; handbook is authoritative | O'Rourke / Goodman / Tóth, *Handbook of Discrete and Computational Geometry*, visibility material | https://www.science.smith.edu/~jorourke/books/discrete.html | Formal computational-geometry background and robust-geometric-computation pointers. |
| geom-deberg-compgeom | read | P0 | survey / textbook | University-hosted textbook PDF | de Berg et al., *Computational Geometry: Algorithms and Applications* | https://www.cs.cmu.edu/afs/cs/academic/class/15456-f15/Handouts/BKOS.pdf | Segment intersection, range searching, arrangements, visibility graphs, and data-structure concepts. |

## P1 — Art-Gallery Approximation and Set Cover

| ID | Status | Priority | Source type | Access / credibility | Reference | URL | Project relevance |
|---|---:|---:|---|---|---|---|---|
| approx-bonnet-miltzow-agp | read | P1 | preprint / primary research | arXiv with DOI metadata; computational geometry | Bonnet and Miltzow, *An Approximation Algorithm for the Art Gallery Problem* | https://arxiv.org/abs/1607.05527 | Supports hard-problem framing and discretized guard/witness approximation caveats. |
| approx-deshpande-art-gallery | read | P1 | primary research | Author/institution-hosted PDF | Deshpande et al., *Approximation Algorithm for Art Gallery Problems* | https://erikdemaine.org/papers/ArtGallery_WADS2007/paper.pdf | Finite guard-location generation, set cover, and VC-dimension approximation framing. |
| approx-ghosh-agp | read | P1 | primary research | ScienceDirect page with DOI/abstract; full text may be limited | Ghosh, *Approximation algorithms for art gallery problems in polygons* | https://www.sciencedirect.com/science/article/pii/S0166218X09004855 | Vertex/edge guard approximation, visibility polygons, minimum set cover, and greedy algorithms. |
| approx-agt-status | read | P1 | survey | Accessible survey PDF; useful but verify publication metadata before citation | *The Art Gallery Problem: Status and Perspectives* | https://aaysharma.github.io/data/AGT.pdf | Modern survey of hardness, approximation, parameterized variants, and witness-set issues. |

## Sensor, Access-Point, Camera, and View Placement

| ID | Status | Priority | Source type | Access / credibility | Reference | URL | Project relevance |
|---|---:|---:|---|---|---|---|---|
| place-gadiraju-access-point | access-limited | P1 | access-limited lead | IEEE page found but blocked by JavaScript/verification in this environment | Gadiraju et al., *Novel Sensor/Access-Point Coverage-Area Maximization for Arbitrary Indoor Polygonal Geometries* | https://ieeexplore.ieee.org/document/9552949/ | Practical AP placement in polygonal environments. Keep as a lead; do not rely on details until full text is accessible. |
| place-mikula-kulich-omnidirectional | read | P1 | preprint / primary research | arXiv, 2025 revision, associated repository noted | Mikula and Kulich, *Omnidirectional Sensor Placement: A Large-Scale Computational Study and Novel Hybrid Accelerated-Refinement Heuristics* | https://arxiv.org/abs/2410.08784 | Large-scale accelerated-refinement and hybrid local-search ideas directly relevant after baseline correctness. |
| place-tossa-wsn | access-limited | P2 | access-limited lead | PMC page blocked by browser check in this environment | Tossa et al., *Area Coverage Maximization under Connectivity Constraint in Wireless Sensor Networks* | https://pmc.ncbi.nlm.nih.gov/articles/PMC8914776/ | Broader sensor coverage ideas; connectivity constraints appear out of scope unless official rules change. |
| camera-palsson | read | P2 | thesis | University-hosted master thesis | Pålsson, *The Camera Placement Problem — An Art Gallery Problem Variation* | https://fileadmin.cs.lth.se/cs/education/Examensarbete/Rapporter/2008/CameraPlacement.pdf | Camera-placement analogy, constraints, greedy practical engineering, and coverage-threshold language. |
| camera-fleishman-view | read | P2 | primary research | University-hosted PDF | Fleishman, Cohen-Or, and Lischinski, *Automatic Camera Placement for Image-Based Modeling* | https://www.sci.utah.edu/~shachar/Publications/FleishmanPG99.pdf | View quality and redundancy concepts; use only as heuristic inspiration. |
| camera-vazquez-entropy | read | P2 | primary research | Author/institution-hosted PDF | Vázquez et al., *Automatic View Selection Using Viewpoint Entropy* | https://vccimaging.org/Publications/Vazquez2003AVS/Vazquez2003AVS.pdf | Entropy/view-selection concepts for nonredundant candidate choice; not official scoring. |

## P1 — Submodular and Greedy Optimization

| ID | Status | Priority | Source type | Access / credibility | Reference | URL | Project relevance |
|---|---:|---:|---|---|---|---|---|
| opt-mirzasoleiman-lazier | read | P1 | primary research | Author-hosted ICML paper PDF | Mirzasoleiman et al., *Lazier Than Lazy Greedy* | https://web.cs.ucla.edu/~baharan/papers/mirzasoleiman15lazier.pdf | Stochastic/lazy greedy acceleration for large candidate pools. Useful after objective is shaped correctly. |
| opt-krause-sensor-placement | read | P1 | primary research | JMLR paper PDF | Krause et al., *Near-Optimal Sensor Placements in Gaussian Processes* | https://jmlr.org/papers/volume9/krause08a/krause08a.pdf | Submodular sensor-placement principles, diminishing returns, greedy guarantees, and local-search comparison framing. |
| opt-shamaiah-greedy-sensor | read | P1 | primary research | Author-hosted conference PDF | Shamaiah et al., *Greedy Sensor Selection: Leveraging Submodularity* | https://sidbanerjee.orie.cornell.edu/docs/CDC_sensorsel.pdf | Greedy sensor-selection theory; supports cardinality-constrained greedy framing, but model differs from GIS Cup. |

## P2 — Wireless LOS and Urban Blockage

| ID | Status | Priority | Source type | Access / credibility | Reference | URL | Project relevance |
|---|---:|---:|---|---|---|---|---|
| wireless-mmwave-urban | read | P2 | preprint | arXiv source; radio/reflection details are out of scope | *Base Station and Passive Reflectors Placement for Urban mmWave Networks* | https://arxiv.org/abs/2011.01920 | Urban blockage and visibility-region intuition only; ignore reflections, path loss, and radio physics for scoring. |
| wireless-uav-los-relaying | read | P2 | preprint / primary research | arXiv with IEEE TWC journal reference and DOI | *Geography-aware Optimal UAV 3D Placement for LOS Relaying* | https://arxiv.org/abs/2209.15161 | Geography-aware LOS search ideas; 3D UAV details are out of scope for 2D boundary placement. |

## P1/P2 — New Candidate Additions From Resynthesis

| ID | Status | Priority | Source type | Access / credibility | Reference | URL | Project relevance |
|---|---:|---:|---|---|---|---|---|
| robust-shewchuk-predicates | to-read | P1 | primary research | Classic robust-predicate paper; add full source before implementation | Shewchuk, *Adaptive Precision Floating-Point Arithmetic and Fast Robust Geometric Predicates* | https://people.eecs.berkeley.edu/~jrs/papers/robust-predicates.pdf | Robust orientation/incircle predicate principles for boundary degeneracies and exactness risk. |
| visibility-bungiu-efficient | to-read | P1 | preprint / implementation reference | arXiv paper associated with CGAL visibility-polygon work | Bungiu et al., *Efficient Computation of Visibility Polygons* | https://arxiv.org/abs/1403.3905 | Candidate acceleration path if segment-by-segment visibility becomes too slow. |
| opt-nemhauser-submodular | to-read | P1 | primary research | Foundational result; locate stable DOI/publisher source before citation | Nemhauser, Wolsey, Fisher, *An analysis of approximations for maximizing submodular set functions I* | https://doi.org/10.1007/BF01588971 | Greedy approximation baseline for monotone submodular maximization under cardinality constraints. |

## Maintenance Notes

- The registry is complete relative to the original README seed list as of the July 2026 resynthesis.
- `access-limited` entries should not drive implementation details until full text or a reliable secondary summary is obtained.
- Keep wireless/radio papers as P2 background only; official GIS Cup scoring is geometric direct visibility, not propagation strength.
- Move long summaries into `docs/reference/research-synthesis.md`.
