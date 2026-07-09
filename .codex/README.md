# Codex Project Context

This directory contains project-local instructions for Codex sessions working on `mz_giscup_26`.

Compact read order for future sessions:

1. `../AGENTS.md`
2. `../docs/codex-startup-brief.md`
3. `../docs/competition-reference.md`
4. `../docs/codebase-map.md`
5. `../docs/session-state.md`
6. `../docs/context-maintenance.md` when editing docs or ending a session

Task-specific drill-down:

- Research/math/geography: `../docs/research-synthesis-brief.md`, then `.codex/research-papers.md` and `.codex/research-synthesis.md` if needed.
- Agent selection: `../docs/agent-roles-brief.md`.
- Full original context: `../docs/original_implementation_brief.md`.
- Codex implementation details: `.codex/project-context.md`, `.codex/geometry-and-scoring-rules.md`, `.codex/development-workflow.md`, `.codex/repo-map.md`.

These files are guidance for this repository only. They do not replace official ACM SIGSPATIAL GIS Cup rules.

## Required Context-Maintenance Rule

- At the beginning of every new session, read the compact `/docs` startup set above before loading large archival files.
- At the end of every session, update `../docs/session-state.md` plus any affected compact docs listed in `../docs/context-maintenance.md`.
- Keep `/docs` compact and operational; keep long-form archival material in `README.md`, `../docs/original_implementation_brief.md`, and `.codex/research-synthesis.md`.
- Final QA/QC for a session must include a documentation-maintenance pass where the last pass yields no changes.

## Project Agents

- `.agents/geospatial-scientist.yaml` defines the `geospatial-scientist` agent.
- `.codex/agents/geospatial-scientist.md` contains the detailed research-synthesis operating instructions.
- `.agents/geosoft-engineer.yaml` defines the `geosoft-engineer` implementation agent.
- `.codex/agents/geosoft-engineer.md` contains the geospatial software-engineering operating instructions.
- `.agents/geospft-critique.yaml` defines the `geospft-critique` independent QA/critique agent.
- `.codex/agents/geospft-critique.md` contains the competition-compliance critique instructions.
- `.agents/web-searcher.yaml` defines the `web-searcher` credibility-aware source-discovery agent.
- `.codex/agents/web-searcher.md` contains the web/research search and source-credibility critique instructions.
- `.agents/performance-engineer.yaml` defines the `performance-engineer` scalability agent.
- `.codex/agents/performance-engineer.md` contains visibility/cache/bitset/profiling guidance.
- `.agents/submission-packager.yaml` defines the `submission-packager` final deliverable agent.
- `.codex/agents/submission-packager.md` contains final zip/output/reproducibility guidance.
- `.agents/geodata-qc.yaml` defines the `geodata-qc` dataset inspection agent.
- `.codex/agents/geodata-qc.md` contains CRS/topology/ID/anomaly QA guidance.
- `.agents/optimization-experimenter.yaml` defines the `optimization-experimenter` experiment-design agent.
- `.codex/agents/optimization-experimenter.md` contains parameter sweep and diagnostics-comparison guidance.
