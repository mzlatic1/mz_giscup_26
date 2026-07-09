# Project Rules — mz_giscup_26

- This repository is for participating in the ACM SIGSPATIAL 2026 GIS Cup antenna-placement challenge.
- The folder `/mnt/c/Users/marko/OneDrive/Documents/SIGSPATIAL_2026` is the project scratch folder and should also be referred to as the **OneDrive Parent Folder**.
- Treat files in the OneDrive Parent Folder as competition context, notes, datasets, scratch outputs, transfer material, or final packaging workspace unless the user gives more specific instructions.
- Preserve CRS explicitly and do not assume EPSG:4326. The sample brief indicates EPSG:32611 / UTM Zone 11N, but code must inspect source data.
- Avoid silently overwriting source data. Write derived outputs under `outputs/` or explicitly named scratch locations.
- Keep official rules separate from heuristics. When the official GIS Cup page conflicts with repository notes, the official page wins.
- Fast-start project context lives under `docs/`. At the beginning of every Codex session, read `docs/codex-startup-brief.md`, `docs/competition-reference.md`, `docs/codebase-map.md`, and `docs/session-state.md` before drilling down. Use `README.md` and `docs/original_implementation_brief.md` as archival/full-detail sources, not default startup reads.
- Maintain `/docs` as the compact session-memory layer. At the end of every Codex session, update `docs/session-state.md` and any other affected compact docs according to `docs/context-maintenance.md`; QA/QC is not complete until the final documentation-maintenance pass yields no changes.
- Additional Codex-specific project context lives under `.codex/`. Read `.codex/project-context.md`, `.codex/geometry-and-scoring-rules.md`, and `.codex/development-workflow.md` when making substantive solver or competition-strategy changes that need more detail than the compact docs.
- Project agent `geospatial-scientist` is defined in `.agents/geospatial-scientist.yaml`; use it for research synthesis across computational geometry, GIS/geography, visibility, wireless LOS, and optimization papers.
- Project agent `geosoft-engineer` is defined in `.agents/geosoft-engineer.yaml`; use it for robust, testable, competition-aligned geospatial software implementation.
- Project agent `geospft-critique` is defined in `.agents/geospft-critique.yaml`; use it to independently critique code and deliverables against user instructions, official competition objectives, geospatial correctness, and robustness.
- Project agent `web-searcher` is defined in `.agents/web-searcher.yaml`; use it for credibility-aware internet/source discovery across any user-indicated research topic, not only geospatial or GIS Cup topics.
- Project agent `performance-engineer` is defined in `.agents/performance-engineer.yaml`; use it for visibility profiling, caching, bitset tradeoffs, multiprocessing, and scalability work.
- Project agent `submission-packager` is defined in `.agents/submission-packager.yaml`; use it for final GIS Cup solution text, source bundle, run instructions, reproducibility notes, and zip packaging.
- Project agent `geodata-qc` is defined in `.agents/geodata-qc.yaml`; use it for dataset CRS/topology/ID/statistics/anomaly inspection.
- Project agent `optimization-experimenter` is defined in `.agents/optimization-experimenter.yaml`; use it for configuration sweeps, multi-start analysis, diagnostics ranking, and tau/k-specific tuning.
- All project agents must conduct iterative QA/QC at the end of their work until the final QA/QC pass yields no changes.
