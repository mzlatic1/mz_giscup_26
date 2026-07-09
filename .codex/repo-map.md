# Repository Map

```text
.
├── AGENTS.md
├── .agents/
│   ├── geodata-qc.yaml
│   ├── geosoft-engineer.yaml
│   ├── geospatial-scientist.yaml
│   ├── geospft-critique.yaml
│   ├── optimization-experimenter.yaml
│   ├── performance-engineer.yaml
│   ├── submission-packager.yaml
│   └── web-searcher.yaml
├── .codex/
│   ├── README.md
│   ├── development-workflow.md
│   ├── geometry-and-scoring-rules.md
│   ├── project-context.md
│   ├── repo-map.md
│   ├── session-handoff.md
│   ├── agents/
│   │   ├── geodata-qc.md
│   │   ├── geosoft-engineer.md
│   │   ├── geospatial-scientist.md
│   │   ├── geospft-critique.md
│   │   ├── optimization-experimenter.md
│   │   ├── performance-engineer.md
│   │   ├── submission-packager.md
│   │   └── web-searcher.md
│   ├── research-papers.md
│   └── research-synthesis.md
├── README.md
├── docs/
│   ├── README.md
│   ├── agent-roles-brief.md
│   ├── codebase-map.md
│   ├── codex-startup-brief.md
│   ├── competition-reference.md
│   ├── context-maintenance.md
│   ├── original_implementation_brief.md
│   ├── research-synthesis-brief.md
│   └── session-state.md
├── configs/
│   ├── defaults.yaml
│   └── experiments.example.yaml
├── data/
│   └── README.md
├── outputs/
│   └── cache/
├── scripts/
│   ├── compare_configs.py
│   ├── profile_visibility.py
│   └── run_sample.py
├── src/giscup/
│   ├── bitsets.py
│   ├── candidates.py
│   ├── cli.py
│   ├── coverage.py
│   ├── diagnostics.py
│   ├── geometry.py
│   ├── io.py
│   ├── models.py
│   ├── optimize.py
│   ├── output.py
│   ├── sampling.py
│   ├── solver.py
│   ├── validate.py
│   └── visibility.py
└── tests/
    ├── test_geometry.py
    ├── test_output_format.py
    ├── test_sampling.py
    ├── test_solver.py
    ├── test_validate.py
    └── test_visibility.py
```

## Module Ownership

- `models.py`: dataclasses for buildings, candidates, samples, solutions, dataset metadata.
- `io.py`: dataset loading and CRS/metadata capture.
- `geometry.py`: boundary extraction, legality checks, lengths, bounds.
- `visibility.py`: line-of-sight predicates and STRtree blocker queries.
- `sampling.py`: weighted perimeter samples.
- `candidates.py`: boundary candidate generation and deduplication.
- `coverage.py`: sampled coverage aggregation and serviced-building checks.
- `optimize.py`: baseline greedy and future lazy/stochastic greedy hooks.
- `solver.py`: end-to-end orchestration.
- `output.py`: official three-line solution formatting and parsing.
- `validate.py`: output validation.
- `diagnostics.py`: inspect/run summaries.
- `cli.py`: command-line interface.

## Project Agents

- `geospatial-scientist`: reads the project research registry, studies the referenced literature, and synthesizes mathematical/geographic/algorithmic implications for the solver.
- `geosoft-engineer`: writes robust, testable, competition-aligned geospatial software deliverables for the solver.
- `geospft-critique`: independently critiques `geosoft-engineer` outputs for user-instruction compliance, competition alignment, geospatial correctness, and robustness.
- `web-searcher`: searches the internet for credible sources relevant to user input and critiques each source for authority, relevance, recency, and applicability.
- `performance-engineer`: owns profiling, visibility caches, bitset tradeoffs, multiprocessing, and scalability planning.
- `submission-packager`: owns final output/zip/source/run-instruction/reproducibility audits.
- `geodata-qc`: owns official dataset inspection, CRS/topology/ID/statistics checks, and anomaly reporting.
- `optimization-experimenter`: owns experiment design, parameter sweeps, diagnostics comparison, and tau/k tuning.

## Compact Docs Layer

- `docs/codex-startup-brief.md`: first compact operational memory for new Codex sessions.
- `docs/competition-reference.md`: compact official-rule/scoring/date reference.
- `docs/codebase-map.md`: package, command, validation, and limitation summary.
- `docs/session-state.md`: latest environment, validation, uncommitted-state, and next-step handoff.
- `docs/context-maintenance.md`: mandatory beginning/end-of-session maintenance contract.
