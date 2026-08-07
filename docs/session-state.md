# Current Session State

This document captures the current operational state so future sessions can avoid rereading long history.

## Repository

- Local root: `/home/markolinux/projects/sigspatial_26`
- Remote: `https://github.com/mzlatic1/mz_giscup_26.git`
- Main branch has the scaffold, compact docs, and agents pushed.
- Harness: Claude Code. The Codex layer (`AGENTS.md`, `.agents/`, `.codex/`) was fully migrated on
  2026-08-06 and no longer exists; recover it from git history before commit `b4a7353` if ever needed.

## Environment

Project Conda env exists:

```bash
conda activate mz-giscup-26
```

Known installed/tested stack:

- Python 3.11
- Shapely
- GeoPandas
- pyogrio
- NumPy
- SciPy
- pytest
- bitarray
- orjson
- editable `mz-giscup-26`

## Latest validation

Run 2026-08-06 in Conda env `mz-giscup-26`, after the Claude Code migration:

```bash
python -m compileall src tests scripts   # OK
python -m pytest -q                      # 18 passed in 0.79s
```

The migration changed no source code, so this result is unchanged from the prior session and
confirms no regression.

Additional context QA passed: required compact docs exist and are non-empty; every repo-relative
path referenced by `CLAUDE.md`, `.claude/agents/*.md`, `.claude/commands/*.md`, and the compact
docs resolves; `.claude/settings.json` parses; every agent's `name:` matches its filename.

Synthetic CLI smoke tests passed:

- `giscup inspect`
- `giscup solve-one` + `validate-output`
- `giscup solve-all` + `validate-output`

## Recent applied fixes

Session of 2026-08-06 — Codex to Claude Code migration:

- `AGENTS.md` → `CLAUDE.md`, rewritten as a compact auto-loaded rule file.
- `.agents/*.yaml` + `.codex/agents/*.md` → self-contained `.claude/agents/*.md`. Each agent's
  markdown body is now its whole system prompt; no startup reads required.
- `.codex/{project-context,geometry-and-scoring-rules,development-workflow,research-papers,research-synthesis}.md`
  → `docs/reference/`. `.codex/repo-map.md` and `.codex/session-handoff.md` deleted as duplicates
  of `docs/codebase-map.md` and this file.
- `docs/codex-startup-brief.md` → `docs/startup-brief.md`; Codex wording stripped from all live
  docs (the archival `original_implementation_brief.md` keeps its original text deliberately).
- Added `/startup`, `/wrapup`, `/solve` slash commands.
- Added `.claude/settings.json`: allow-list for routine read-only commands, `Write`/`Edit` deny on
  `data/**` (a backstop only — it does not cover shell writes), and a `SessionStart` hook that
  injects this file into every new session.
- Hardened `.claude/settings.json` after a security review flagged three issues in the first
  version: `Bash(python -m pytest:*)` was arbitrary code execution via wildcard args;
  `giscup solve-one/solve-all:*` and `python -m giscup.cli:*` could write anywhere via `--output`,
  bypassing the `data/**` deny; and the deny listed only absolute paths, so relative spellings
  slipped through. Allow-list is now exact-match for anything that executes or writes, and the
  deny covers absolute plus relative forms.
- Added `.claude/skills/giscup-output-format/` — auto-triggering submission-format rules.
- `geospft-critique` now has no write tools, making its independence structural.

Earlier sessions:

- Created compact `/docs` startup set.
- Added `docs/context-maintenance.md` so sessions read compact docs at startup and update `/docs` at closeout.
- Updated project rules, agents, root `README.md`, and compact docs to enforce `/docs` maintenance.
- Created/updated project agents.
- Added research registry/source credibility metadata.
- Fixed validator empty-line and malformed-header behavior.
- Added sampled claim validation.
- Enforced exact `k` in solver/output paths.
- Made unimplemented optimizers explicit errors.
- Made sampling include interior rings to match Shapely perimeter.
- Added tests for solver, validation, output formatting, and hole sampling.

## Next recommended actions

1. **Add the official sample dataset under `data/`** — released 2026-03-31 and not yet present
   locally. Nearly all remaining work is blocked on it; every validation so far is against a
   synthetic GeoJSON.
2. Run `giscup inspect` on the sample and compare stats against
   `docs/original_implementation_brief.md`; use the `geodata-qc` agent.
3. Phase 4 — performance: visibility cache, bitset integration, candidate pruning. Current direct
   recomputation will not scale to `k=1000` on full-size data.
4. Phase 5 — replace the raw newly-visible-sample greedy objective with a threshold-aware one.
   The scored objective is *serviced building count*, not visible perimeter; the current objective
   optimizes the wrong thing.
5. Implement real `lazy-greedy` / `stochastic-greedy`, or remove the names from configs.
6. Fill in the `scripts/compare_configs.py` and `scripts/profile_visibility.py` placeholders.

## Hard deadline

Test dataset released **2026-08-15**; submission due **2026-08-16**. That is a ~24-hour window,
so the solve pipeline must be fully automated and performance-tested *before* Aug 15.
