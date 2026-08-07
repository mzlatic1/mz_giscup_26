# Project Agent Roles Brief

Agents are defined in `.claude/agents/*.md`, one self-contained file each — the markdown body is
the agent's full system prompt, so no extra reading is required at spawn time. Claude Code
auto-discovers them; invoke by name or let them be delegated automatically.

All project agents must end work with iterative QA/QC until the final pass yields no changes.

## Research and source discovery

- `web-searcher`: internet/source discovery for any user-indicated topic; critiques credibility, authority, relevance, recency, and applicability.
- `geospatial-scientist`: synthesizes computational geometry, GIS/geography, visibility, wireless LOS, and optimization research for this project.

## Engineering and critique

- `geosoft-engineer`: writes robust, testable, competition-aligned geospatial code.
- `geospft-critique`: independently reviews code/deliverables against user instructions, official competition objectives, geospatial correctness, and robustness.

## Specialized project agents

- `performance-engineer`: visibility profiling, caching, bitsets, multiprocessing, scalability.
- `geodata-qc`: CRS, topology, ID, bounds, geometry validity, sample/final anomaly inspection.
- `optimization-experimenter`: config sweeps, multi-start runs, diagnostics ranking, tau/k tuning.
- `submission-packager`: final nine-block output, source bundle, run instructions, reproducibility notes, zip packaging.

## Selection examples

- Need a paper search: `web-searcher`.
- Need to understand art-gallery math: `geospatial-scientist`.
- Need to implement lazy greedy: `geosoft-engineer`, then `geospft-critique`.
- Need to speed up visibility: `performance-engineer`.
- Need to inspect official data: `geodata-qc`.
- Need to compare configs: `optimization-experimenter`.
- Need final submission audit: `submission-packager`.
