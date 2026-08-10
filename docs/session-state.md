# Current Session State

Operational state so the next session starts without rereading history. Say **"start session"** and
`/startup` handles the rest.

**Scope of this file:** what is true *now* — environment, validation, artifacts, next actions.
Detailed findings and their reasoning live in `docs/task-board.md`; the narrative of how each was
reached lives in commit messages, which are long and specific by design. Compressed from 693 lines
on 2026-08-09; nothing unique was dropped, but for the story behind a decision use `git log`.

---

# HANDOFF — 2026-08-09, end of session

## Status in one line

**A complete, audited submission artifact exists and is packaged.** Six days to the 2026-08-15 test
data, seven to the 2026-08-16 deadline. Nothing is blocked on machine time. One decision sits with
Marko.

## The submission artifact

**`outputs/nine_bestof_400.txt`** — 9 blocks, 4,650 antennas, **42,728 claims, audit PASSED, 0
overclaims.** Packaged as `outputs/submission/mz_giscup_26_submission_20260810.zip` (478.5 KiB,
94 files).

It is **per-block best-of**: lever A in eight blocks, **baseline in `(0.5, 1000)`**, because lever A
measurably loses that block at every quantile tested. Legitimate because the nine subproblems score
independently.

| artifact | claims | subproblems (of 9, vs the better of our own two) |
|---|---|---|
| baseline `nine_verifypar_400.txt` | 39,120 | 6.90 |
| lever A `nine_leverA_400_full.txt` | 42,556 | 8.98 |
| **best-of `nine_bestof_400.txt`** | **42,728** | **9.00** |

All three audited clean: `outputs/audit_v2.log`, `audit_leverA_full.log`, `audit_bestof.log`.
*(Our-options-only comparison, not a score prediction — competition rule 5 still holds.)*

**Structurally re-verified 2026-08-10, independently of the audit logs.** `nine_bestof_400.txt` is
27 lines, no separators, nine blocks in tau-outer/k-inner order, with **exactly k points counted**
in every block (50/500/1000 x3). Per-block claims are 1,659 / 9,349 / 12,279 / 269 / 4,247 / 8,063 /
148 / 2,222 / 4,492, **summing to exactly 42,728**. The `(0.5, 1000)` block reads **8,063**, which is
the *baseline* count and not lever A's 7,891 — so the per-block best-of really is in the file, not
just in the documentation. Bundle passes `unzip -t`.

**The packaged bundle's `source/` is now behind the repo** (it predates the 2026-08-10
`DEFAULT_OBJECTIVE` fix and the 350 -> 356 tests). Harmless — it is a March-sample bundle that must
be regenerated on the day regardless — but do not ship this zip.

## Decisions

| # | Decision | Status |
|---|---|---|
| **15** | Lever A is the shipped default | **DONE.** `--objective {near-tau,baseline}`, default `near-tau`. |
| **3b** | 400 m cull stands | **DONE.** Reinforced by #20 below. |
| **9** | 2x candidate prune | **CLOSED 2026-08-10 — default stays OFF, contingency only.** |
| **20** | Radii below 400 m | **CLOSED — measured and rejected.** |

**Every decision is now closed.** #9 was adopted as a *free* lever on a sizing measured in-sample,
with baseline greedy, pooled at k=500. Measured against the objective we actually ship it costs
**~0.07 subproblems** (−2.03% at `(0.75, 50)`). Marko re-decided it on 2026-08-10 with those
corrected numbers: **`--candidate-stride` ships at 1.** Buying ~1.7 h of headroom we do not need,
at a certain cost concentrated in the small-count blocks, is the wrong trade while the day
projection sits near 5 h of a ~20 h window. It stays **ranked first among the day-of levers**,
implemented, tested, and one flag away.

## The two time-buying levers, measured and ranked

This is what the submission-day runbook's "what to give up if the extract is bigger" section was
missing — it listed options with no ranking.

| lever | matrix build | greedy | total saved | score cost |
|---|---|---|---|---|
| **#9 `--candidate-stride 2`** | ~50 min | **~0.86 h** | **~1.7 h** | **~0.07 subproblems** |
| **#20 300 m cull** | ~50 min | **nothing** | ~0.8 h | **~0.79 subproblems** |

**#9 strictly dominates #20** — about twice the time saved at about a eleventh of the cost. 300 m
does not speed up greedy at all: the argmax is a popcount over every candidate row, and
words-per-row depends on *sample* count, not on how many bits are set, so a sparser matrix costs the
same to scan.

**If runtime must be bought on the day: prune first, cut radius only if that is not enough.**

## Official page — re-checked 2026-08-10, nothing has changed

`https://sigspatial2026.sigspatial.org/giscup.html`. **The submission link is still not published**:
*"The webpage will be updated closer to the competition time to include a link to submit."* Re-check
on 2026-08-15. Fallback contact if it never appears: Aaron Lowe (`alowe@esri.com`) or Ashwin
Shashidharan (`ashashidharan@esri.com`).

Everything else on the page re-confirmed against our docs, verbatim, with **no drift**: all five
dates; three lines per subproblem for nine subproblems; three taus x three ks; IEEE-754 doubles;
*"the polygons will not self-intersect and will not have holes"*; test dataset published 2026-08-15.

**Submission artifact shape confirmed** — *"a zip file including the following: 1. A text file with
the solutions for each of the sub-problems... 2. A folder that has your source code, along with
instructions for compiling and running the program."* That is exactly what
`scripts/package_submission.py` produces.

**The ID field name is still ABSENT from the page.** The `--id-property` trap is therefore live and
unresolvable before the extract lands: `giscup inspect` on the day is the only way to settle it.

## Next actions

1. **On the day, read `docs/submission-day-runbook.md` first.** It carries the `--id-property` trap
   (run `giscup inspect` before solving), the sizing sequence, and the ranked fallback levers.
2. **Re-check the official page for the submission link on 2026-08-15.**
3. Optional: re-run `/rehearsal` if solver code changes.

---

# Environment

```bash
conda activate mz-giscup-26          # Python 3.11; required for all work
```

**Host: 16 cores, 24 GB RAM.** NumPy 2.4.6 (`np.bitwise_count` needs >=2.0), Shapely 2.1.2,
SciPy 1.17.1. **`ruff` and `mypy` are NOT installed** — `pip install -e .[dev]` if lint is needed.

## Validation status — actually run 2026-08-09, end of session

```bash
python -m pytest -q                         # 350 passed
python -m compileall -q src tests scripts   # OK
```

Working tree **clean**; everything committed and pushed to `origin/main`.

## Managing the multi-hour background jobs

These jobs are **memory-bandwidth bound, not core bound.** Four concurrent jobs cut the greedy pick
rate from 59/min to 34/min. Measured 2026-08-09: **12 workers buys essentially nothing over 8** for
the matrix build — an inferred 400 m/12-worker build (~102 min) lands on the measured 8-worker time
(99.6 min).

- **Use `nice -n 15` on the low-priority job** and let the scheduler arbitrate. Do not `renice` or
  `SIGSTOP` after the fact.
- **`pgrep -f <pattern>` matches your own shell**, because the pattern appears in that shell's own
  command line. On 2026-08-09 this killed an authorised 600 m build outright (exit 147 = 128+19).
  Match on something narrower, or filter out the current shell's PID. `ps -p <pid>` and
  `pgrep -P <pid>` are safe.
- **A killed matrix build is safe by design**: the metadata JSON is the completion marker, so a
  `.bits` file without its `.json` is rebuilt rather than trusted.
- **Piping a long job through `tail` hides all progress** — `tail` only flushes at exit. Watch the
  `.partial` file instead; `solve-all` writes one after every block.
- **A background shell ID does not survive a `/clear`; `outputs/` does.** Check files and `ps`
  before assuming a job died.

## Matrix cache — `outputs/cache`, 8.6 GB, 845 GB free

| radius | stride | candidates | visible pairs | build | key |
|---|---|---|---|---|---|
| 400 m | 1 | 157,454 | 8,194,226 | 99.6 min @ 8 w | `7a385189` **<- the one in use** |
| 600 m | 1 | 157,454 | 8,891,506 | 434.5 min @ 6 w | `89846a10` |
| 400 m | 2 | 78,727 | 4,878,593 | 50.9 min @ 12 w | `7c422675` |
| 300 m | 1 | 157,454 | 7,529,996 | 48.6 min @ 12 w | `73e00daa` |

**None can be reused on submission day** — the key includes the dataset digest. Keys also cover
candidate set, samples, radius, strategy, eps, and `interior_tolerance`, so a pre-#14 matrix can
never be silently reused.

## Data situation

**`data/GIS-cup-sample-dataset.geojson`** — the official March sample (6.3 MB, git-ignored,
obtained 2026-08-08). Every documented statistic matches exactly: 12,860 buildings, 78,727 exterior
vertices, 858,973.22 m perimeter, 1 hole-bearing polygon, EPSG:32611.

**Test data does not exist until 2026-08-15.** Every solution-quality figure in this repository is
fitted on the March sample; August is a different extract.

`outputs/synthetic_full.geojson` (regenerable via `scripts/make_synthetic_dataset.py`) is fine for
feasibility rehearsals but has no real street topology and omits the large-building tail.
**Never use it for solution-quality claims.**

## Estimation calibration — read before trusting a projection

Two distinct patterns, both live:

**1. Extrapolating a constant past the configuration it was measured in.** This produced every major
error in the project: the gate's verification constant (16.2x low), the 800 m build (2.6x), the
audit cost (16x), the "free" 2x prune, and the per-`(tau, k)` schedule. `gate_model` now *refuses*
to cost an unmeasured radius pair or objective rather than guessing. **Apply the same standard to
analysis scripts, which have no such guard.**

**2. A pooled figure hiding where the score actually lives.** Hit three times on 2026-08-09 alone.
Claim counts pooled across blocks say −5.4% for a 300 m cull; relative scoring says 0.79
subproblems, because the loss concentrates in small-count blocks worth exactly as much as large
ones. **Size every lever per block, never on the total.**

**In-sample sweeps rank well and predict margins badly.** `scripts/sweep_near_tau.py` counts off the
same grid the optimizer optimized on. It picked the right quantile ordering repeatedly, then missed
`(0.5, 1000)` by 3.2 and 5.5 points — enough to flip a decision both times.

**Timing projections have run optimistic six times and pessimistic once.** Treat any projection not
calibrated against a measured run with suspicion, in that direction.

## Known gaps, ranked

1. **Everything is fitted on the March sample.** Lever A's quantile schedule is a *tuned* parameter;
   the baseline objective has no such knob. This is the main argument for the escape hatch
   (`--objective baseline`) existing and staying tested.
2. **`(0.5, 1000)` ships baseline**, so the artifact mixes objectives. Deliberate and audited, but
   the submission is therefore not reproducible from a single command — see
   `scripts/assemble_blocks.py`.
3. **The cull radius is still a heuristic with no feedback.** 400 m discards ~9% of visibility;
   verification re-measures near-threshold buildings at 800 m, so the buildings that decide the
   score already get the wide view. Both directions are now measured: 600 m gains +4.1% for ~1.6x
   headroom, 300 m loses ~0.79 subproblems for ~0.8 h.
4. **`gate_model` uses the 4.70x contended verify speedup for its verdict**, deliberately, though
   7.3x was measured uncontended. The gate reports both; only the conservative one decides.
   **Reviewed 2026-08-10 and deliberately left alone — this is CLOSED, not outstanding.** The
   uncontended figure is already fully in the module: `MEASURED_VERIFY_SPEEDUP_UNCONTENDED = {12:
   7.30}`, reachable via `verify_speedup(w, contended=False)`, printed by `rehearse.py` as a third
   row, and pinned by four tests. The only step never taken is letting it set the **verdict**, and
   it should stay untaken: a feasibility gate that quietly gets more optimistic is exactly how #16
   happened. *(Docs previously called this "not acted on", which understated what exists.)*
5. **Greedy optimizes on the sampled matrix**, not the scored quantity. Deliberate — it is a search
   heuristic — but the objective and the claim decision measure different things.
6. Only `greedy` exists as an optimizer. `lazy-greedy` / `stochastic-greedy` / `hybrid` were deleted
   in #10 and are not roadmap markers.

## Repository

- Local root `/home/markolinux/projects/sigspatial_26`, remote
  `https://github.com/mzlatic1/mz_giscup_26.git`, branch `main`.
- **Standing rule: commits and pushes need Marko's explicit approval each time.**
- Do not commit datasets, generated outputs, visibility caches, or environments.
