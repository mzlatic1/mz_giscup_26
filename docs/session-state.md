# Current Session State

Operational state so the next session starts without rereading history.
Task list lives in `docs/task-board.md`. Say **"start session"** and `/startup` handles the rest.

Last session: **2026-08-06**. Working tree clean, all work committed and pushed.

## The one thing that matters

**The solver cannot finish a single subproblem.** The feasibility gate reads **FAIL by ~5e8x**.
Until `/rehearsal` reads PASS, feasibility work outranks everything else — a better objective on a
solver that cannot finish scores zero.

Next action: **task #1** in the task board (switch default visibility strategy to `relate`), which
unblocks **#2**, the radius-culled cached visibility matrix. #2 is the blocker for the project.

**9 days to test-data release (2026-08-15); submission 2026-08-16.** One shot, no score feedback
ever. Treat Aug 15 as a rehearsal deadline, not a start date.

## Repository

- Local root: `/home/markolinux/projects/sigspatial_26`
- Remote: `https://github.com/mzlatic1/mz_giscup_26.git`, branch `main`
- Harness: Claude Code. The Codex layer (`AGENTS.md`, `.agents/`, `.codex/`) was migrated
  2026-08-06 and no longer exists; recover from git history before `b4a7353` if ever needed.
- Head: `ee51eef`. Preceding: `6403ab6`, `be6d66b`, `b4a7353`, `050f95a`.

## Environment

```bash
conda activate mz-giscup-26      # Python 3.11; required for all work
```

Installed and exercised: Shapely, GeoPandas, pyogrio, NumPy, SciPy, pytest, bitarray, orjson,
editable `mz-giscup-26`. **`ruff` and `mypy` are NOT installed** despite being configured in
`pyproject.toml` — `pip install -e .[dev]` if lint is needed.

## Data situation — read before trusting any number

`data/` contains **no dataset**. The official sample (released 2026-03-31) was never added locally
and the test data does not exist until 2026-08-15.

All scaling work therefore runs against a synthetic stand-in:

```bash
python scripts/make_synthetic_dataset.py --output outputs/synthetic_full.geojson
```

`outputs/synthetic_full.geojson` exists on disk (5.1 MB, git-ignored, regenerable — deterministic
under `--seed 20260806`). It matches the documented sample statistics within a few percent, but has
**no real street topology** and **omits the large-building tail**. Real grids have long
unobstructed sight corridors it cannot produce, so the measured visible-distance range is very
likely an underestimate. Never use it for solution-quality claims.

## Latest validation — run 2026-08-06 in `mz-giscup-26`

```bash
python -m compileall -q src tests scripts   # OK
python -m pytest -q                         # 18 passed in 0.29s
giscup inspect --input outputs/synthetic_full.geojson   # OK, CRS EPSG:32611 preserved
python scripts/rehearse.py --input outputs/synthetic_full.geojson --cores 8   # FAIL (expected)
```

Context QA passed: every repo-relative path referenced by `CLAUDE.md`, `.claude/agents/*.md`,
`.claude/commands/*.md` and the compact docs resolves; `.claude/settings.json` parses; each agent's
`name:` matches its filename.

No source code was changed this session — the 18-test result is unchanged from the prior session
and confirms no regression.

## Feasibility gate — measured 2026-08-06

Full-scale synthetic (12,860 buildings, 138,077 samples, 160,198 candidates), 20 h / 8-core budget:

| variant | checks (all 9) | time | |
|---|---|---|---|
| current: hybrid, no cache, no cull | 1.03e14 | 666,236 days | FAIL |
| relate, cached, no cull | 2.21e10 | 53 days | FAIL |
| relate, cached, radius cull 200 m | 1.31e08 | **10.3 min** | PASS |
| relate, cached, radius cull 400 m | 5.24e08 | **1.0 h** | PASS |

Throughput is dominated by **blockers per STRtree query**, which scales with segment length:
unbounded ~1,401 blockers at ~605 checks/s; ≤200 m ~7 blockers at ~26,539 checks/s — a 44x swing
from segment length alone. Visibility matrix is ~99.985% empty; median visible distance ~91–130 m
(small-sample; treat as indicative).

**The viable route:** `relate` + per-candidate caching + a radius cull, matrix computed once and
reused across all nine subproblems. Choose the radius **generously** — the budget has slack and
under-culling loses score silently.

## Two corrections made this session

Numbers derived from a small test grid earlier in the session were wrong, both optimistic, both
conclusion-flipping. Recorded because the rule they produced now lives in `CLAUDE.md`:

| | claimed | measured at full scale | error |
|---|---|---|---|
| visibility throughput | 6,045 checks/s | 549–605 checks/s | 11x |
| visibility sparsity | 2.85% visible | 0.015–0.05% visible | 190x |

Cause: a long segment's bbox in a 5 km domain intersects ~1,400 buildings — invisible on a
900-building test. **Measure at full scale; never extrapolate from a toy case.**

## Session log

**2026-08-06 — Codex to Claude Code migration, security hardening, feasibility gate.**

- `AGENTS.md` → `CLAUDE.md`; `.agents/*.yaml` + `.codex/agents/*.md` → self-contained
  `.claude/agents/*.md`; `.codex/*.md` → `docs/reference/`; `docs/codex-startup-brief.md` →
  `docs/startup-brief.md`. `.codex/repo-map.md` and `.codex/session-handoff.md` deleted as
  duplicates. Codex wording stripped from live docs; the archival brief keeps its original text.
- Added `/startup`, `/wrapup`, `/solve`, `/rehearsal`, and the `giscup-output-format` skill.
- `.claude/settings.json`: allow-list, `Write`/`Edit` deny on `data/**`, `SessionStart` hook.
  Hardened after a security review found 3 issues — wildcard `pytest` was arbitrary code
  execution, `giscup solve-*` could write anywhere via `--output` and defeat the deny, and the
  deny matched only absolute paths. The deny is a **backstop, not a guarantee**: it does not cover
  shell writes.
- `geospft-critique` has no write tools, making its independence structural.
- Added `scripts/make_synthetic_dataset.py` and `scripts/rehearse.py`.
- Encoded the ROGII lessons as rules and gates (`CLAUDE.md` posture section, agent rules, session
  memory). ROGII finished top 20% / no medal with the gap ~3x the range of every lever being
  tuned; the four failure modes were dead knobs, the winning route found too late, blind local
  validation, and lessons written down but never re-applied.

## Known limitations carried forward

- Only `greedy` exists. `lazy-greedy` / `stochastic-greedy` / `hybrid` correctly raise — never
  describe them as working.
- Greedy objective is raw newly-visible-sample count, not serviced-building count (task #6).
- Validation path has the same complexity bug as the solver (task #7).
- Candidate "pruning" modes only add candidates; they prune nothing (task #9).
- `configs/defaults.yaml` is not wired into the CLI.
- `scripts/compare_configs.py` and `scripts/profile_visibility.py` are placeholders.
- Hole-perimeter asymmetry between sampling and candidate generation (task #11).
