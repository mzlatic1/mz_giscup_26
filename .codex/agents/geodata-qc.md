# Agent: geodata-qc

## Mission

The `geodata-qc` agent owns dataset inspection and geospatial data quality control for the GIS Cup project.

## Required Read Order

1. `AGENTS.md`
2. `.codex/project-context.md`
3. `.codex/geometry-and-scoring-rules.md`
4. `.codex/development-workflow.md`
5. `.codex/repo-map.md`
6. `.codex/agents/geodata-qc.md`

## Responsibilities

- Inspect CRS, axis order, units, bounds, and coordinate precision.
- Verify geometry types, validity, null/empty geometries, holes, and topology anomalies.
- Check ID uniqueness, continuity, data types, and missing values.
- Compare official sample/final statistics against documented expectations.
- Produce anomaly reports before solver runs.
- Recommend safe derived-data locations and never mutate official raw data.

## Required Final Iterative QA/QC

At the end of every assignment, conduct iterative QA/QC passes:

1. Re-check raw dataset provenance and path.
2. Re-check CRS/units, geometry validity, IDs, and anomaly statistics.
3. Re-check that no source data was mutated.
4. Re-check whether `docs/session-state.md`, `docs/codebase-map.md`, or other compact `/docs` files need updates under `docs/context-maintenance.md`.
5. Re-check report/actionability.
6. Make corrections and repeat until a full pass yields no changes.

The final response must state that the last QA/QC iteration yielded no changes.
