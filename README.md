# mz_giscup_26 — ACM SIGSPATIAL 2026 GIS Cup Solver

`mz_giscup_26` is a correctness-first, performance-aware Python repository for the **ACM SIGSPATIAL 2026 GIS Cup** antenna-placement challenge. The project is organized to support rapid experimentation once the official competition dataset is released, while preserving a strong foundation for robust computational geometry, line-of-sight visibility, boundary coverage estimation, optimization, diagnostics, and final submission packaging.

> Project scratch context: `/mnt/c/Users/marko/OneDrive/Documents/SIGSPATIAL_2026`, also known in this project as the **OneDrive Parent Folder**.

## Fast Codex Startup

For future Codex sessions, prefer the compact startup docs in `docs/` before reading this full README:

1. `docs/codex-startup-brief.md`
2. `docs/competition-reference.md`
3. `docs/codebase-map.md`
4. `docs/session-state.md`
5. `docs/context-maintenance.md` when ending a session or editing docs

Use `docs/original_implementation_brief.md` as the preserved full source brief when deeper detail is needed. At the end of each Codex session, update the compact `/docs` layer according to `docs/context-maintenance.md` so future sessions do not need to reconstruct state from chat history.

## Repository Status

This initial commit establishes the professional project scaffold, documentation, CLI entry points, data models, geometry/visibility primitives, sampling and candidate-generation modules, baseline optimization interfaces, validation helpers, tests, and final-output formatting conventions. It intentionally favors maintainable, testable foundations over premature competition tuning.

## Source-of-Truth Hierarchy

When project notes disagree, resolve conflicts in this order:

1. Official competition page: <https://sigspatial2026.sigspatial.org/giscup.html>
2. Official/test dataset inspection
3. The imported implementation brief from the OneDrive Parent Folder
4. Engineering judgment, clearly marked as an assumption or heuristic

## Problem Summary

Given building footprints `B`, a service threshold `tau`, and a number of antennas `k`, compute exactly `k` antenna points on building boundaries so that the number of serviced buildings is maximized. A building is serviced when at least a `tau` fraction of its perimeter is visible from the antenna set. Visibility is direct line-of-sight: a segment is blocked only when it intersects the interior of a building footprint; tangency and boundary-only contact do not block visibility.

## Professional Repository Layout

```text
mz_giscup_26/
  AGENTS.md                    # Project-local Codex/session rules
  README.md                    # Detailed competition and implementation documentation
  LICENSE                      # Current rights statement
  pyproject.toml               # Python package metadata and tool config
  environment.yml              # Conda environment for geospatial work
  requirements.txt             # Pip-compatible dependency list
  .gitignore                   # Generated artifacts/data exclusions
  .gitattributes               # Text normalization and GIS large-file hints
  configs/
    defaults.yaml              # Default solver, sampling, and validation parameters
    experiments.example.yaml   # Example multi-start/tuning experiment grid
  data/
    README.md                  # Dataset placement and provenance instructions
    .gitkeep
  docs/
    README.md                         # Compact-doc index and startup read order
    codex-startup-brief.md            # Fast session startup context
    competition-reference.md          # Official rule/date/scoring summary
    codebase-map.md                   # Module/command/test/limitation summary
    session-state.md                  # Latest validation and next-step handoff
    context-maintenance.md            # Required session-start/session-end docs contract
    agent-roles-brief.md              # Agent routing summary
    research-synthesis-brief.md       # Compact research digest
    original_implementation_brief.md  # Preserved full initial brief
  outputs/
    .gitkeep
    cache/.gitkeep             # Visibility/cache outputs; ignored by Git
  scripts/
    run_sample.py
    profile_visibility.py
    compare_configs.py
  src/giscup/
    __init__.py
    bitsets.py                 # Integer bitset abstraction
    candidates.py              # Boundary candidate generation and dedupe
    cli.py                     # inspect / solve-one / solve-all / validate-output
    coverage.py                # Approximate sampled coverage accounting
    diagnostics.py             # Dataset and run diagnostics
    geometry.py                # CRS-safe geometry helpers and validation
    io.py                      # GeoJSON/geospatial loading
    models.py                  # Typed dataclasses
    optimize.py                # Greedy/lazy-greedy interfaces
    output.py                  # Official solution formatting/parsing
    sampling.py                # Weighted boundary sample generation
    solver.py                  # End-to-end solve orchestration
    validate.py                # Output and solution validation
    visibility.py              # LOS predicates and blocker index
  tests/
    test_geometry.py
    test_output_format.py
    test_sampling.py
    test_solver.py
    test_validate.py
    test_visibility.py
```

## Installation

Recommended local setup with Conda:

```bash
conda env create -f environment.yml
conda activate mz-giscup-26
python -m pip install -e .
```

Pip-only setup:

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e .[dev]
```

## Data Placement

Place the official/sample GeoJSON at:

```text
data/GIS-cup-sample-dataset.geojson
```

Large datasets and generated outputs are intentionally excluded from Git. Keep raw official data immutable and place derived artifacts under `outputs/`.

## CLI Usage

Inspect a dataset:

```bash
python -m giscup.cli inspect --input data/GIS-cup-sample-dataset.geojson
```

Solve one parameter combination:

```bash
python -m giscup.cli solve-one \
  --input data/GIS-cup-sample-dataset.geojson \
  --tau 0.5 \
  --k 500 \
  --output outputs/solution_tau_0.5_k_500.txt \
  --diagnostics outputs/diag_tau_0.5_k_500.json \
  --candidate-mode hybrid \
  --sampling-profile balanced \
  --optimizer greedy
```

Solve all nine sample-style combinations:

```bash
python -m giscup.cli solve-all \
  --input data/GIS-cup-sample-dataset.geojson \
  --taus 0.25 0.5 0.75 \
  --ks 50 500 1000 \
  --output outputs/solution.txt \
  --diagnostics outputs/diagnostics.json
```

Validate solution formatting and claims:

```bash
python -m giscup.cli validate-output \
  --input data/GIS-cup-sample-dataset.geojson \
  --solution outputs/solution.txt \
  --sampling-profile accurate
```

## Implementation Notes

- Coordinates are stored as Python floats / NumPy `float64` and formatted with `17` significant digits for final output.
- The default perimeter mode uses Shapely polygon length (`all-boundaries`) to handle the sample anomaly with one hole; exterior-only mode is exposed for future evaluator alignment.
- The baseline code discretizes continuous boundary coverage into weighted boundary samples. Dense validation and conservative claim margins are recommended before final submissions.
- Visibility predicates are strategy-based (`relate`, `negative_buffer`, `hybrid`) because boundary degeneracies are important for official correctness.
- The initial solver is intentionally simple and deterministic. The currently implemented optimizer is `greedy`; future phases should add cached visibility matrices, bitset acceleration, stochastic/lazy greedy improvements, local search, and multi-start experiments.

## Development Roadmap

1. **Correctness foundation** — IO, models, geometry, output format, validation.
2. **Visibility and sampling** — weighted samples, STRtree blocker index, LOS tests.
3. **Baseline solver** — candidate generation, greedy solve-one, validate-output.
4. **Performance** — bitsets, visibility cache, parallel precompute, candidate pruning.
5. **Competitive improvements** — stochastic greedy, local swaps, adaptive refinement, multi-starts.
6. **Final packaging** — solve-all, official zip helper, diagnostics summaries, reproducibility notes.

## Validation and QA

Run fast checks:

```bash
python -m compileall src tests scripts
python -m pytest
```

The tests cover output formatting, basic geometry behavior, weighted sampling, and official visibility edge cases such as clear LOS, interior blocking, tangency, vertex touch, and boundary contact.

## Imported Competition Brief

The following content was imported from the OneDrive Parent Folder onboarding brief so this repository remains self-contained for future development sessions.

---

# ACM SIGSPATIAL 2026 GIS Cup — Codex CLI Implementation Brief

**Purpose:** Use this Markdown file as the primary build prompt/specification for Codex CLI.  
**Goal:** Generate a correctness-first, performance-aware Python repository for the ACM SIGSPATIAL 2026 GIS Cup antenna-placement challenge.

---

## 0. Source-of-Truth Hierarchy

Use this order when resolving conflicts:

1. **Official competition page**: <https://sigspatial2026.sigspatial.org/giscup.html>
2. **Uploaded sample dataset inspection**: `GIS-cup-sample-dataset.geojson`
3. **Research-informed implementation guidance** listed in this document
4. **Engineering judgment**, but only when explicitly marked as an assumption or heuristic

Do **not** treat heuristics in this document as official rules. Official rules come from the GIS Cup page.

---

## 1. Official Competition Facts

### 1.1 Event

- Event: **2026 GIS Cup**
- Conference: **34th ACM SIGSPATIAL International Conference on Advances in Geographic Information Systems**
- Location: **Riverside, CA, USA**
- Conference dates: **Tuesday Nov 3 – Friday Nov 6, 2026**

### 1.2 Motivation

The competition models a 2D urban antenna-placement problem motivated by high-frequency wireless networks such as 5G and 6G. Higher-frequency signals are more easily blocked by obstacles such as buildings and trees, so antenna placement must account for line of sight.

### 1.3 Official Task

Given a collection of building footprints, place a fixed number of antennas on the **sides/perimeters/boundaries of buildings** to maximize the number of buildings that can be serviced.

A building does **not** need full perimeter visibility. It is serviced if a sufficient fraction of its perimeter is covered.

### 1.4 Input Parameters

For a problem instance, the program receives:

- `B`: a set of building footprints
- `tau`: a threshold value where `0 < tau <= 1`
- `k`: the number of antennas to place

### 1.5 Output

Compute a set `P` of exactly `k` antenna points such that:

- every point lies on the boundary of a building in `B`
- the service score is maximized

### 1.6 Final Competition Structure

The final competition will provide:

- one building-footprint dataset `B`
- three threshold values `tau`
- three antenna-count values `k`

This creates **9 independent subproblems**: all `3 × 3` combinations.

### 1.7 Official Sample Parameters

The sample page lists:

- `tau`: `0.25`, `0.5`, `0.75`
- `k`: `50`, `500`, `1000`

These are sample values. The solver must accept arbitrary `tau` and `k`.

### 1.8 Important Dates

- Sample dataset available: **March 31, 2026**
- Test dataset published / competition begins: **August 15, 2026**
- Submission deadline: **August 16, 2026**
- Final results published and invited-paper notifications: **September 15, 2026**
- Invited-paper deadline: **11:59 PM AoE, September 30, 2026**

### 1.9 Official Contacts

- Aaron Lowe: `alowe` at `esri.com`
- Ashwin Shashidharan: `ashashidharan` at `esri.com`

---

## 2. Official Mathematical Definitions

### 2.1 Point Visibility

Given points `p` and `q` in the plane and a set of building footprints `B`, point `p` is visible from `q` with respect to `B` if the straight line segment connecting `p` and `q` **does not intersect the interior of any building**.

Critical edge cases:

- tangency to a building does **not** block visibility
- touching a building boundary at a vertex does **not** block visibility
- boundary-only contact does **not** block visibility
- intersection with a building interior **does** block visibility

### 2.2 Segment Visibility

Given:

- a set of antenna points `P`
- a set of building footprints `B`
- a line segment `l`

Segment `l` is visible from `P` if **every point along `l`** is visible from at least one antenna point in `P`.

This is a continuous visibility definition, not merely point-sample visibility.

### 2.3 Building Coverage

For a building `b`, its boundary can be subdivided into visible and non-visible line segments.

Coverage is:

```text
C(P, B, b) = visible_boundary_length(b) / total_perimeter_length(b)
```

### 2.4 Service Score

A building is serviced if:

```text
C(P, B, b) >= tau
```

The service score is the number of buildings meeting or exceeding `tau`.

### 2.5 Optimization Problem

Given `B`, `tau`, and `k`, compute `k` antenna points on building boundaries that maximize the service score.

The official page explicitly states that computing the absolute maximum is hard, so approximate best solutions under reasonable time and resource constraints are expected.

---

## 3. Official Submission Requirements

### 3.1 Zip File Contents

The final submission should contain:

1. A text file with solutions for each of the 9 subproblems.
2. A folder containing source code and compiling/running instructions.

### 3.2 Three-Line Format per Subproblem

For each `(tau, k)` pair, output exactly three lines:

```text
(tau, k)
(x1, y1), (x2, y2), ..., (xk, yk)
id1, id2, id3, ...
```

Line meanings:

1. parameter pair
2. comma-separated list of exactly `k` antenna coordinates
3. comma-separated list of building IDs claimed as serviced

### 3.3 Precision Requirement

Antenna coordinates must remain at **64-bit precision**. Evaluation uses standard **IEEE 754 doubles**.

Implementation requirement:

- store coordinates as Python floats / NumPy float64
- output coordinates with `17` significant digits
- do not round to six decimals
- avoid unnecessary snapping, reprojection, or coordinate normalization in final output

Recommended coordinate formatting:

```python
format(x, ".17g")
```

### 3.4 Evaluation Formula

For each of the 9 parameter combinations:

```text
points = team's service score / highest service score among all submitted answers
```

Total score is the sum of points across all 9 subproblems.

Implication:

- optimize every `(tau, k)` combination separately
- avoid overfitting to only one threshold or antenna count
- track per-subproblem score diagnostics

### 3.5 AI / Code Use

The official FAQ allows AI tools and any software/code for implementation and testing. If invited to write a short paper, describe AI/software/code use there.

---

## 4. Uploaded Sample Dataset Inspection

Dataset path:

```text
/mnt/data/GIS-cup-sample-dataset.geojson
```

Expected repository-local path:

```text
data/GIS-cup-sample-dataset.geojson
```

### 4.1 GeoJSON Metadata

- GeoJSON type: `FeatureCollection`
- Collection name: `building_footprints_projected`
- CRS: `EPSG:32611` / UTM Zone 11N
- Feature count: `12,860`
- Geometry type: `Polygon` only
- Property keys: `id`
- Building IDs:
  - integer IDs from `1` to `12,860`
  - unique
  - contiguous

### 4.2 Coordinate Extent

Coordinates are projected planar meters.

```text
min x: 480722.8908011479
min y: 3765686.4007992023
max x: 485669.16843957646
max y: 3769950.3378679175
width:  ~4,946.2776384285535 m
height: ~4,263.937068715226 m
bbox area: ~21,090,616.574652717 m²
```

### 4.3 Geometry Validity

- Valid polygons: `12,860 / 12,860`
- Exterior rings closed: yes
- Exterior ring orientation: clockwise for all inspected polygons
- Official page says no holes, but the uploaded sample contains one polygon with a hole.

### 4.4 Important Dataset Anomaly

Building ID `9448` has one interior ring.

```text
building id: 9448
holes: 1
area: ~4016.6492834498986 m²
perimeter: ~374.02982085311805 m
bounds:
  min x: 484124.08494831744
  min y: 3767983.379717134
  max x: 484236.0420778062
  max y: 3768063.88471401
```

Implementation requirement:

- the official problem says no holes, but the solver must defensively support holes because the sample file contains one
- antenna candidates may lie on the exterior boundary; optionally support hole boundaries for validity checks, but do not rely on hole-boundary antenna placement unless confirmed by official evaluator expectations

Recommended conservative rule:

- generate antenna candidates from exterior boundaries only
- include holes in obstacle/interior geometry for visibility blocking
- include holes in geometry validity checks
- compute building perimeter using Shapely polygon length unless official clarification later says exterior-only perimeter

### 4.5 Area Statistics

```text
total building area: ~3,416,147.870858091 m²
building area / bbox area: ~16.20%
min area: ~7.252682450690249 m²
median area: ~201.76432641873942 m²
mean area: ~265.64135854261986 m²
max area: ~17,956.716603489156 m²
```

### 4.6 Perimeter Statistics

```text
total perimeter: ~858,973.2186701939 m
min perimeter: ~10.832002199606423 m
median perimeter: ~62.13215520764492 m
mean perimeter: ~66.79418496657807 m
max perimeter: ~1,066.07100868539 m
```

### 4.7 Vertex and Segment Statistics

```text
total exterior vertices: 78,727
unique exterior vertices: 78,727
min vertices/building: 4
median vertices/building: 6
mean vertices/building: ~6.121850699844479
max vertices/building: 38

total exterior segments: 78,727
min segment length: ~0.019141824915281696 m
median segment length: ~9.2006720497326 m
mean segment length: ~10.910439577916604 m
max segment length: ~271.07912159470976 m
```

### 4.8 Performance Implications

The sample is medium-sized:

- 12,860 buildings
- 78,727 exterior boundary segments
- ~859 km total perimeter
- sparse low-vertex footprint geometry
- projected coordinates in meters

Do not implement all-pairs candidate/sample/blocker checks naively without spatial indexing. The solver must use candidate pruning, STRtree/R-tree indexing, and bitset-based marginal updates.

---

## 5. Research-Informed Design Guidance

This section converts research findings into implementation instructions. These are **not** official rules.

### 5.1 Core Computational Geometry

Relevant references:

- Joseph O'Rourke, **Art Gallery Theorems and Algorithms**  
  <https://www.science.smith.edu/~jorourke/books/ArtGalleryTheorems/Art_Gallery_Full_Book.pdf>

- Subir Kumar Ghosh, **Visibility Algorithms in the Plane**  
  <https://www.cambridge.org/core/books/visibility-algorithms-in-the-plane/>

- O'Rourke / Goodman / Tóth, **Handbook of Discrete and Computational Geometry**, visibility material  
  <https://www.science.smith.edu/~jorourke/books/discrete.html>

- de Berg et al., **Computational Geometry: Algorithms and Applications**  
  <https://www.cs.cmu.edu/afs/cs/academic/class/15456-f15/Handouts/BKOS.pdf>

Implementation translation:

- treat GIS Cup as an exterior/perimeter guarding variant with obstacles
- implement robust line-segment vs. polygon-interior predicates
- explicitly test degeneracies: tangency, vertex touch, collinearity, antenna on boundary
- use visibility-graph and visibility-polygon ideas for acceleration after the baseline works

### 5.2 Art Gallery Approximation and Set Cover

Relevant references:

- Bonnet and Miltzow, **An Approximation Algorithm for the Art Gallery Problem**  
  <https://arxiv.org/abs/1607.05527>

- Deshpande et al., **Approximation Algorithm for Art Gallery Problems**  
  <https://erikdemaine.org/papers/ArtGallery_WADS2007/paper.pdf>

- Ghosh, **Approximation algorithms for art gallery problems in polygons**  
  <https://www.sciencedirect.com/science/article/pii/S0166218X09004855>

- The Art Gallery Problem: Status and Perspectives  
  <https://aaysharma.github.io/data/AGT.pdf>

Implementation translation:

- discretize the continuous problem into candidate antenna points and weighted boundary coverage elements
- formulate each `(tau, k)` as a maximum coverage-style problem with cardinality constraint
- use greedy/lazy greedy as a strong baseline
- consider set-cover / ILP only for small diagnostic subsets because the full sample dataset is too large for naive exact optimization

### 5.3 Sensor / Access-Point Placement

Relevant references:

- Gadiraju et al., **Novel Sensor/Access-Point Coverage-Area Maximization for Arbitrary Indoor Polygonal Geometries**  
  <https://ieeexplore.ieee.org/document/9552949/>

- Mikula and Kulich, **Omnidirectional Sensor Placement: A Large-Scale Computational Study and Novel Hybrid Accelerated-Refinement Heuristics**  
  <https://arxiv.org/abs/2410.08784>

- Tossa et al., **Area Coverage Maximization under Connectivity Constraint in Wireless Sensor Networks**  
  <https://pmc.ncbi.nlm.nih.gov/articles/PMC8914776/>

Implementation translation:

- use hybrid accelerated-refinement ideas after greedy:
  - generate multiple initial solutions
  - filter poor/redundant candidates
  - refine by local swaps
  - re-score with denser coverage samples
- prioritize runtime/quality tradeoffs because final evaluation gives only 24 hours after dataset release
- implement diagnostics so multiple heuristic configurations can be compared quickly

### 5.4 Camera Placement and View Selection

Relevant references:

- Pålsson, **The Camera Placement Problem — An Art Gallery Problem Variation**  
  <https://fileadmin.cs.lth.se/cs/education/Examensarbete/Rapporter/2008/CameraPlacement.pdf>

- Fleishman, Cohen-Or, and Lischinski, **Automatic Camera Placement for Image-Based Modeling**  
  <https://www.sci.utah.edu/~shachar/Publications/FleishmanPG99.pdf>

- Vázquez et al., **Automatic View Selection Using Viewpoint Entropy**  
  <https://vccimaging.org/Publications/Vazquez2003AVS/Vazquez2003AVS.pdf>

Implementation translation:

- use weighted coverage quality, not only binary visible/not visible sample counts
- penalize redundant coverage when it does not push buildings across `tau`
- for high `tau`, explicitly reward complementary views of the same building

### 5.5 Submodular and Greedy Optimization

Relevant references:

- Mirzasoleiman et al., **Lazier Than Lazy Greedy**  
  <https://web.cs.ucla.edu/~baharan/papers/mirzasoleiman15lazier.pdf>

- Krause et al., **Near-Optimal Sensor Placements in Gaussian Processes**  
  <https://jmlr.org/papers/volume9/krause08a/krause08a.pdf>

- Shamaiah et al., **Greedy Sensor Selection: Leveraging Submodularity**  
  <https://sidbanerjee.orie.cornell.edu/docs/CDC_sensorsel.pdf>

Implementation translation:

- implement lazy greedy first
- add stochastic greedy for large candidate pools
- maintain marginal gains efficiently
- because thresholded building service is not strictly the same as plain maximum coverage, use a shaped objective that includes partial progress toward `tau`

### 5.6 Wireless LOS / Urban Blockage

Relevant references:

- **Base Station and Passive Reflectors Placement for Urban mmWave Networks**  
  <https://arxiv.org/abs/2011.01920>

- **Geography-aware Optimal UAV 3D Placement for LOS Relaying**  
  <https://arxiv.org/abs/2209.15161>

Implementation translation:

- use urban-blockage spatial indexing and candidate pruning ideas
- ignore reflections, propagation strength, heights, and radio physics unless explicitly added by official rules
- GIS Cup only evaluates direct geometric line of sight and perimeter coverage

---

## 6. Repository Structure to Build

Create this repository:

```text
giscup2026/
  README.md
  pyproject.toml
  src/
    giscup/
      __init__.py
      io.py
      models.py
      geometry.py
      visibility.py
      sampling.py
      coverage.py
      candidates.py
      bitsets.py
      optimize.py
      solver.py
      output.py
      validate.py
      diagnostics.py
      cli.py
  scripts/
    run_sample.py
    profile_visibility.py
    compare_configs.py
  data/
    GIS-cup-sample-dataset.geojson
  outputs/
    .gitkeep
  tests/
    test_io.py
    test_geometry.py
    test_visibility.py
    test_sampling.py
    test_coverage.py
    test_candidates.py
    test_output_format.py
    test_validate.py
```

---

## 7. Dependencies

Use Python 3.11+.

Recommended dependencies:

```text
shapely
geopandas
pyogrio
numpy
scipy
tqdm
joblib
bitarray
orjson
pytest
```

Optional performance dependencies:

```text
numba
pyroaring
rtree
```

Use Shapely 2.x STRtree if available.

---

## 8. Data Model

Implement typed dataclasses or Pydantic-free lightweight models.

### 8.1 Building

Fields:

```python
id: int | str
polygon: shapely.geometry.Polygon
exterior_coords: np.ndarray  # shape (n, 2), closed ring optional internally
exterior_edges: list[tuple[np.ndarray, np.ndarray]]
interiors: list[np.ndarray]
perimeter: float
area: float
bounds: tuple[float, float, float, float]
```

### 8.2 Candidate

Fields:

```python
id: int
x: float
y: float
source_building_id: int | str
source_edge_index: int | None
kind: str  # vertex, midpoint, edge_sample, cluster, refined
```

### 8.3 BoundarySample

Fields:

```python
id: int
x: float
y: float
building_id: int | str
edge_index: int
weight: float  # represented boundary length
```

### 8.4 Solution

Fields:

```python
tau: float
k: int
antenna_points: list[tuple[float, float]]
claimed_building_ids: list[int | str]
diagnostics: dict
```

---

## 9. Geometry and Visibility Requirements

### 9.1 Boundary Legality

A coordinate is legal if it lies on a building boundary.

Implementation:

- use exact generated boundary coordinates whenever possible
- for validation, use `polygon.boundary.distance(Point(x, y)) <= eps`
- default `eps` should be small relative to coordinate scale, e.g. `1e-8` to `1e-7`
- do not snap final coordinates unless explicitly running a repair step

### 9.2 Visibility Predicate

Implement:

```python
def is_visible(a: PointLike, b: PointLike, polygons_index) -> bool:
    ...
```

Rule:

- construct segment `ab`
- query spatial index for polygons whose bbox intersects segment bbox
- for each candidate blocker polygon:
  - if segment intersects the polygon interior, return `False`
  - if segment only touches boundary, tangent edge, or vertex, do not block
- return `True`

Robust Shapely approach:

```python
line = LineString([a, b])
blocked = line.crosses(poly) or line.within(poly) or line.relate_pattern(poly, "T********")
```

However, Shapely predicates around boundaries can be subtle. Add explicit tests and adjust until official edge cases are satisfied.

Recommended safer predicate:

```python
interior = poly.buffer(-eps)
blocked = not interior.is_empty and line.intersects(interior)
```

But negative buffering can fail for tiny polygons and is approximate. Keep both approaches available behind a strategy flag:

- `relate`
- `negative_buffer`
- `hybrid`

Default should be `hybrid`.

### 9.3 Self-Blocking

Do not automatically exclude the source building or target building from blocker checks.

Reason:

- an antenna on one side of a building may not see the opposite side if the segment crosses that building's interior
- the segment starts/ends on a boundary, but the rest of the segment may enter interior

### 9.4 Holes

Because sample building `9448` has one hole:

- include polygon interiors in geometric operations
- if using `poly.interiors`, preserve them
- for perimeter coverage, use Shapely `poly.length` by default, but expose `--perimeter-mode exterior|all-boundaries`
- default `perimeter-mode` should be `all-boundaries` for Shapely consistency, but document that official wording implies exterior building perimeter

---

## 10. Sampling Strategy

The official coverage definition is continuous, but the first competitive implementation should use weighted boundary sampling.

### 10.1 Boundary Samples

Generate samples along each exterior segment.

For each edge of length `L`:

```python
n = max(1, ceil(L / spacing))
```

Each sample represents approximately:

```python
weight = L / n
```

Sample at interval midpoints, not endpoints, to avoid duplicate vertex ambiguity:

```python
t = (i + 0.5) / n
point = p0 + t * (p1 - p0)
```

### 10.2 Default Sampling Configs

Implement named sampling profiles:

```text
fast:
  spacing: 20 m
  min_samples_per_building: 4

balanced:
  spacing: 10 m
  min_samples_per_building: 8

accurate:
  spacing: 5 m
  min_samples_per_building: 16

final:
  spacing: 2.5 m
  min_samples_per_building: 24
```

For the uploaded sample with ~858,973 m total perimeter:

- 10 m spacing implies roughly 85,900 weighted samples before min-sample adjustment
- 5 m spacing implies roughly 171,800 samples
- 2.5 m spacing implies roughly 343,600 samples

Use `balanced` for optimization and `accurate`/`final` for validation.

### 10.3 Adaptive Refinement

After an initial solve:

- identify buildings with coverage within `tau ± 0.05`
- resample those buildings more densely
- recompute coverage and claimed serviced IDs
- optionally run local search focused on near-threshold buildings

---

## 11. Candidate Generation

The sample has 78,727 exterior segments, so candidate generation must be controlled.

### 11.1 Required Candidate Types

Generate:

1. exterior vertices
2. edge midpoints
3. adaptive edge samples for long edges

Candidate count estimates:

- vertices only: ~78,727 candidates
- vertices + midpoints: ~157,454 candidates
- adding long-edge samples may increase substantially

### 11.2 Candidate Deduplication

Deduplicate by exact coordinate string or quantized coordinate key for internal use.

Recommended internal key:

```python
key = (round(x, 12), round(y, 12))
```

But preserve original float coordinates for output.

### 11.3 Candidate Pruning

Add pruning modes:

```text
none
basic
density
visibility_probe
hybrid
```

Basic pruning:

- keep all vertices
- keep all midpoints
- limit long-edge samples to a max per edge
- remove duplicate candidates

Density pruning:

- estimate local building density with grid or KDTree
- prioritize candidates in dense urban areas

Visibility-probe pruning:

- use a coarse boundary sample subset
- score each candidate by approximate visible weighted perimeter
- keep top N candidates globally and/or per spatial tile

Hybrid pruning:

- combine density and visibility probe
- always preserve some candidates per tile for spatial diversity

### 11.4 Candidate Budgets

Expose CLI options:

```text
--max-candidates
--candidate-mode
--candidate-spacing
--candidate-top-per-tile
```

Suggested defaults:

```text
k=50:   max_candidates = 50,000 to 150,000
k=500:  max_candidates = 30,000 to 100,000
k=1000: max_candidates = 20,000 to 80,000
```

These are starting points, not hard limits.

---

## 12. Visibility Matrix and Bitsets

### 12.1 Precomputation

For each candidate, compute visible boundary samples.

Naive complexity is too high:

```text
candidate_count × sample_count × blocker_checks
```

Required accelerations:

- STRtree/R-tree blocker query
- coarse sample filtering by bbox or tiles
- multiprocessing with joblib
- bitsets for visible sample IDs

### 12.2 Bitset Representation

Implement a wrapper in `bitsets.py` that can use:

1. Python `int` bitsets for small/medium runs
2. `bitarray`
3. optional `pyroaring`

Required operations:

```python
union
intersection
difference
count
iter_set_bits
```

### 12.3 Visibility Cache

Cache visibility results by:

```text
dataset hash
candidate config hash
sampling config hash
visibility strategy
```

Store cache under:

```text
outputs/cache/
```

Use `orjson`/pickle/npz as appropriate.

---

## 13. Coverage Evaluation

### 13.1 Approximate Coverage

Maintain:

```python
visible_weight_by_building[building_id]
coverage_by_building = visible_weight / perimeter
serviced = coverage >= tau
```

### 13.2 Incremental Updates

When adding candidate `c`:

- compute newly visible samples:
  ```python
  new_samples = visibility[c] - current_visible
  ```
- aggregate `new_samples` weights by building
- update coverage only for affected buildings

### 13.3 Claimed IDs

Only claim buildings that pass the internal evaluator.

Recommended conservative mode:

```text
claim_margin = 0.005
claim building only if coverage >= tau + claim_margin
```

For final attempts, experiment with smaller margins after validating against dense sampling.

---

## 14. Optimization

### 14.1 Baseline Objective

The true objective is thresholded serviced-building count. However, optimizing only immediate threshold crossings can stall. Use a shaped objective.

For current coverage `cov[b]` and threshold `tau`:

```python
progress[b] = min(cov[b] / tau, 1.0)
```

Marginal gain for candidate `c`:

```text
gain(c) =
  W_service * newly_serviced_count
  + W_progress * sum(progress_after - progress_before for affected unserviced buildings)
  + W_near * near_threshold_bonus
  - W_redundancy * redundant_visible_weight
```

Recommended starting weights:

```text
W_service = 1000
W_progress = 1
W_near = 5
W_redundancy = 0.05
```

Tune these weights per `tau`.

### 14.2 Lazy Greedy

Implement lazy greedy:

1. initialize priority queue with estimated gains
2. pop best candidate
3. recompute exact current gain
4. if still best, select it
5. otherwise push it back with updated priority

### 14.3 Stochastic Greedy

For large candidate pools, implement stochastic greedy inspired by submodular optimization:

- sample a random subset of candidates each iteration
- evaluate only that subset
- keep deterministic seeds for reproducibility

CLI options:

```text
--optimizer greedy|lazy-greedy|stochastic-greedy|hybrid
--random-seed
--stochastic-sample-size
```

### 14.4 Local Search

After greedy solution:

- attempt 1-swap:
  - remove one selected antenna
  - add one unselected candidate
  - accept if score improves
- focus swaps on:
  - candidates near near-threshold buildings
  - selected antennas with low unique contribution

Add time budget:

```text
--local-search-seconds
```

### 14.5 Multi-Start

Run multiple configurations:

- different candidate modes
- different sample densities
- different objective weights
- different random seeds

Keep the best by final validation score.

---

## 15. Tau- and K-Specific Strategy

### 15.1 Tau Strategy

For `tau = 0.25`:

- broad coverage is valuable
- prioritize candidates that see many buildings at least partially
- less need for repeated complementary views

For `tau = 0.5`:

- balance broad coverage and complementary views
- near-threshold management is important

For `tau = 0.75`:

- broad shallow coverage is often insufficient
- focus on clusters where multiple antennas can cover most perimeter
- local search and complementary-angle scoring become more important

### 15.2 K Strategy

For `k = 50`:

- candidate quality matters more than raw speed
- use larger candidate pool
- use accurate scoring
- run multi-start and local search

For `k = 500`:

- use lazy greedy with pruned candidates
- use balanced samples for optimization, accurate samples for validation

For `k = 1000`:

- prioritize scalability
- use aggressive candidate pruning
- use stochastic/lazy greedy
- cache visibility
- parallelize visibility precomputation

---

## 16. CLI Requirements

Implement a CLI in `src/giscup/cli.py`.

### 16.1 Inspect

```bash
python -m giscup.cli inspect \
  --input data/GIS-cup-sample-dataset.geojson
```

Output:

- feature count
- CRS
- ID property
- geometry types
- area/perimeter stats
- vertex/segment stats
- hole count
- bbox
- recommended sampling sizes

### 16.2 Solve One

```bash
python -m giscup.cli solve-one \
  --input data/GIS-cup-sample-dataset.geojson \
  --tau 0.5 \
  --k 500 \
  --output outputs/solution_tau_0.5_k_500.txt \
  --diagnostics outputs/diag_tau_0.5_k_500.json \
  --candidate-mode hybrid \
  --sampling-profile balanced \
  --optimizer lazy-greedy
```

### 16.3 Solve All

```bash
python -m giscup.cli solve-all \
  --input data/GIS-cup-sample-dataset.geojson \
  --taus 0.25 0.5 0.75 \
  --ks 50 500 1000 \
  --output outputs/solution.txt \
  --diagnostics outputs/diagnostics.json
```

### 16.4 Validate Output

```bash
python -m giscup.cli validate-output \
  --input data/GIS-cup-sample-dataset.geojson \
  --solution outputs/solution.txt \
  --sampling-profile accurate
```

### 16.5 Compare Configurations

```bash
python -m giscup.cli compare-configs \
  --input data/GIS-cup-sample-dataset.geojson \
  --tau 0.5 \
  --k 500 \
  --config configs/experiments.yaml \
  --output outputs/comparison.json
```

---

## 17. Diagnostics

For every solve, write JSON diagnostics:

```json
{
  "dataset": {
    "path": "...",
    "feature_count": 12860,
    "crs": "EPSG:32611"
  },
  "parameters": {
    "tau": 0.5,
    "k": 500
  },
  "candidate_config": {},
  "sampling_config": {},
  "optimizer_config": {},
  "counts": {
    "candidate_count": 0,
    "sample_count": 0,
    "selected_count": 0,
    "claimed_serviced_count": 0
  },
  "coverage": {
    "mean": 0.0,
    "median": 0.0,
    "near_threshold_count": 0
  },
  "runtime_seconds": {},
  "warnings": []
}
```

Diagnostics should be sufficient to reproduce a run.

---

## 18. Testing Requirements

Use `pytest`.

### 18.1 Geometry Tests

Create synthetic tests for:

1. valid polygon loading
2. exterior edge extraction
3. hole preservation
4. perimeter calculation
5. boundary legality

### 18.2 Visibility Tests

Create tests for official edge cases:

1. clear line of sight
2. line crossing polygon interior is blocked
3. tangent line is not blocked
4. vertex-touch line is not blocked
5. boundary-overlap line is not blocked unless it enters interior
6. same-building self-blocking
7. source and target points on boundaries

### 18.3 Coverage Tests

Create tests for:

1. one antenna covers expected boundary samples
2. coverage ratio calculation
3. threshold service decision
4. near-threshold claim margin
5. hole-containing polygon behavior

### 18.4 Output Tests

Create tests for:

1. exactly three lines per subproblem
2. exactly `k` coordinates
3. coordinate parser roundtrip
4. 17-significant-digit formatting
5. valid building IDs
6. all 9 subproblems present in `solve-all`

---

## 19. Acceptance Criteria

The repository is acceptable when all of the following are true:

1. `inspect` correctly reports sample dataset stats close to those in this document.
2. `solve-one` runs for at least one sample pair and writes a valid solution file.
3. `solve-all` writes all 9 subproblem blocks.
4. `validate-output` confirms:
   - exactly `k` antenna points per block
   - all antenna points lie on building boundaries within tolerance
   - all claimed IDs exist
   - claimed buildings satisfy the internal sampled coverage check
5. Visibility tests cover tangency, vertex touch, and interior blocking.
6. Coordinates are written with 17 significant digits.
7. Diagnostics JSON is produced for every run.
8. Code is deterministic when a random seed is provided.
9. README explains installation, CLI usage, assumptions, and limitations.

---

## 20. Development Roadmap

### Phase 1 — Correctness Foundation

Build:

- IO
- geometry models
- dataset inspection
- boundary extraction
- boundary legality validation
- output formatter/parser

### Phase 2 — Visibility and Sampling

Build:

- weighted boundary sampler
- STRtree blocker index
- visibility predicate
- visibility unit tests
- approximate coverage evaluator

### Phase 3 — Baseline Solver

Build:

- vertex/midpoint candidate generator
- greedy solver
- solve-one CLI
- validate-output CLI

### Phase 4 — Performance

Build:

- bitsets
- lazy greedy
- visibility caching
- parallel visibility precompute
- candidate pruning

### Phase 5 — Competitive Improvements

Build:

- stochastic greedy
- local search
- adaptive refinement
- multi-start experiments
- compare-configs CLI

### Phase 6 — Final Packaging

Build:

- solve-all
- official solution zip helper
- complete README
- reproducibility instructions
- diagnostics summaries

---

## 21. Known Risks and Mitigations

### Risk: Continuous coverage vs sampled approximation

Mitigation:

- use dense final validation
- conservative claim margin
- adaptive refinement near threshold

### Risk: Shapely boundary predicates disagree with official evaluator

Mitigation:

- test official edge cases
- keep visibility strategy switch
- avoid relying on one predicate without tests

### Risk: Candidate pool too large

Mitigation:

- candidate budgets
- tile-based diversity
- visibility-probe pruning
- stochastic greedy

### Risk: Final dataset differs from sample

Mitigation:

- no hardcoded coordinate ranges
- no hardcoded IDs
- arbitrary `tau` and `k`
- robust CRS/GeoJSON parsing
- handle holes defensively

### Risk: Overclaiming serviced buildings

Mitigation:

- final dense validation
- claim margin
- diagnostics for coverage near threshold

---

## 22. Codex CLI Build Instruction

Implement the repository described in this file.

Prioritize in this order:

1. correctness against official definitions
2. valid official-format output
3. robust geometry and visibility edge cases
4. scalable approximate coverage
5. lazy greedy optimization
6. diagnostics and reproducibility
7. local search and multi-start improvements

Do not remove tests to make the build pass. If a geometry predicate is ambiguous, add a strategy flag and document the behavior.

---

## 23. QA/QC Log for This Specification

### QA/QC Pass 1 — Accuracy

Findings:

- The official rules, sample parameters, scoring, submission format, and precision requirement were separated from implementation recommendations.
- The uploaded dataset anomaly for building `9448` was preserved and marked as a sample-specific issue, not an official rule.
- The sample `tau`/`k` values were clearly marked as examples, not guaranteed final values.

Changes made:

- Added source-of-truth hierarchy.
- Added official vs. heuristic separation.
- Added defensive hole-handling guidance.

### QA/QC Pass 2 — Consistency

Findings:

- Earlier drafts repeated candidate-generation and optimization advice in multiple places.
- Visibility and coverage instructions needed clearer module ownership.
- Research references needed to map directly to implementation choices.

Changes made:

- Consolidated candidate generation into one section.
- Consolidated optimization into one section.
- Added research-to-implementation translations.

### QA/QC Pass 3 — Completeness

Findings:

- The previous Codex brief did not include enough acceptance criteria or test requirements.
- It needed stronger CLI details and diagnostics expectations.
- It needed explicit risk mitigation for sampled coverage.

Changes made:

- Added acceptance criteria.
- Added pytest requirements.
- Added diagnostics schema.
- Added risk/mitigation section.

### QA/QC Pass 4 — Redundancy Check

Findings:

- No additional substantive changes required.
- Remaining repetitions are intentional cross-references where implementation correctness depends on official visibility and precision rules.

Result:

- Final specification is ready for Codex CLI.
