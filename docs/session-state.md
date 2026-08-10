# Current Session State

Operational state so the next session starts without rereading history.
Task list lives in `docs/task-board.md`. Say **"start session"** and `/startup` handles the rest.

---

# HANDOFF — 2026-08-09 ~18:00, written for a `/clear`

**Read this block first.** Everything below it is older narrative, still accurate but superseded
where they disagree.

## Live work at handoff

**A solve is running** and its result is the only thing outstanding:

```
giscup solve-all --taus 0.5 0.75 --ks 1000 --near-tau-quantile 50 25 \
    --visibility-radius 400 --cache-dir outputs/cache --matrix-workers 12 \
    --verify-band 0.10 --verify-max-buildings 2000 --verify-workers 12 \
    --output outputs/leverA_k1000_missing.txt
```

It fills the last two lever A blocks, `(0.5, 1000)` and `(0.75, 1000)`. Started ~17:35, estimated
~2 h. **Check `outputs/leverA_k1000_missing.txt` before assuming it is still running** — the file
is durable, the background-shell ID is not. Also check `ps -eo pid,etime,cmd | grep giscup`.

Note the quantile mapping: `--near-tau-quantile` maps **positionally onto `--taus`**, so a
two-tau run takes two values. Getting this wrong silently changes the objective.

## Where the competition work actually stands

**Lever A wins decisively and is audited clean.** Seven of nine blocks measured post-verification
against baseline `outputs/nine_verifypar_400.txt`:

| block | baseline | lever A | delta |
|---|---|---|---|
| (0.25, 50) | 1,660 | 1,659 | −0.1% |
| (0.25, 500) | 8,854 | 9,349 | +5.6% |
| (0.25, 1000) | 11,630 | 12,279 | +5.6% |
| (0.5, 50) | 144 | 269 | +86.8% |
| (0.5, 500) | 3,903 | 4,247 | +8.8% |
| (0.75, 50) | 27 | **148** | **+448.1%** |
| (0.75, 500) | 1,295 | **2,222** | **+71.6%** |
| **total** | **27,513** | **30,173** | **+9.7%** |

Shipping baseline instead would forfeit **1.89 of 9 subproblems** on these seven — ~21% of the
achievable total, because relative scoring weights every subproblem equally and lever A's gains
are largest where counts are smallest. **Audited: 0 overclaims of 27,803 claims** across the five
blocks in `outputs/nine_leverA_400_5of9.txt`, plus 0 off-boundary antennas and 0 unknown IDs.

Lever A artifacts on disk: `outputs/nine_leverA_400_5of9.txt` (5 blocks),
`outputs/leverA_tau075_small.txt` (2 blocks), `outputs/leverA_k1000_missing.txt` (2 blocks, in
flight). Combine them with `python scripts/assemble_blocks.py --input <files> --output <out>`.

## The three decisions waiting on Marko

| # | Decision | Recommendation |
|---|---|---|
| **15** | Lever A as submission default | Evidence strongly favours **yes**. Costs ~5 h on the day against baseline's 2.85 h. |
| **3b** | 400 m vs a 2x-pruned 600 m build (~3.6 h) | **400 m stands.** 600 m gives +4.1% but only ~1.6x headroom. |
| **9** | Adopt the free 2x candidate prune | Yes, but **only after 3b** — it changes the matrix cache key and would discard both built matrices. |

## What was done 2026-08-09 afternoon

- **#18 confirmed at full scale.** Parallel verification is exactly equivalent to the audited
  serial baseline — same antennas, same 39,120 claim IDs. **9.42 h → 2.85 h, 3.30x.**
- **#17 answered**, **#19 done** (the `(0.75, ·)` blocks above).
- The gate constant is now pinned to an **objective** as well as a radius pair: baseline 0.826,
  near-tau **1.26**. `--objective near-tau` on `scripts/rehearse.py`. Unknown objectives raise.
- **The audit is parallel**: 28 m 51 s → **5 m 41 s at 12 workers, 5.08x, 96% efficiency**,
  identical output. Fitted constant **0.090 s per building per 1000 antennas** at a 400 m screen;
  nine blocks project to ~46 min serial / ~9 min parallel.
- **`scripts/assemble_blocks.py`** recovers a nine-block file from partials. Round-trips a real
  nine-block file byte for byte.
- Three defects fixed: `splitlines()` dropped a legal empty final claims line (would have failed a
  valid submission in the audit); `--exact-radius` defaulted to unbounded, the ~8-hour path,
  reachable by omitting a flag; the runbook's audit command had that omission.

## Corrections I had to make today — the pattern is worth knowing

Four of my own estimates were wrong, all optimistic, and the shape repeats: **extrapolating a
constant past the configuration it was measured in.**

- "8x candidate prune is viable" — the arm came in at −14.9%. Honest lever is 2x.
- "Audit takes 32 min / ~48 min for nine" — 32 min was *elapsed when I looked*, not completion.
- "Serial audit ~5 min" — actual 28 m 51 s. I extrapolated on claim count; cost scales with
  **claims × k**, and my source figure was measured at k=50.
- "In-sample bias inflates lever A" — measured, it did not, in any block.

Before quoting a number, state what configuration it was measured in. `verify_constant_for`
now enforces exactly this for the gate.

## Environment / state

- `conda activate mz-giscup-26`; 16 cores, 24 GB.
- **333 tests passing**, `compileall` clean.
- The 400 m matrix is cached (`outputs/cache/visibility-7a385189*`, 8,194,226 pairs) as is the
  600 m one (`...89846a10*`). Neither can be reused on submission day — the key includes the
  dataset.
- Check `git log origin/main..HEAD` for unpushed work.

---

**`docs/submission-day-runbook.md` is new (2026-08-09).** It is the operational sequence for
2026-08-15/16 — inspect first (the `--id-property` trap), size, solve, audit, package, plus what
to give up if the extract is bigger. Read it on the day; it is not a startup read.

## 2026-08-09 midday — three measurements and two corrections

**#3b ANSWERED: 600 m services +4.1% more buildings than 400 m, concentrated at low k**
(+146.4% at tau=0.75/k=50, +24.1% at 0.5/50, +13.5% at 0.25/50; only +1.0–6.5% at k=1000).
Matched pair — identical candidates, samples, script and objective. **But it cost 434.5 min to
build against a ~5.4 h projection**, and a 600 m solve verifies at 1200 m where the cost constant
does not apply. ~1.6x headroom. **Recommendation: 400 m stands. Marko's call**, and the live
counter-proposal is a 2x-pruned 600 m build (~3.6 h) that might land back near 2.5x.

**#9 SIZED: a 2x candidate prune is free** (one serviced building of 14,708) and worth **1.69 h**.
4x costs 6.6% at tau=0.75, 7.2x costs 14.9%. The free 2x is exactly the vertex half. I claimed
mid-session that an 8x prune was viable — **withdrawn**, the last arm disproved it.

**Correction carried into the board:** its 400 m row (3,888,638 pairs, 24.7 visible/candidate) was
the **pre-#14** matrix and understates visibility ~2x. Valid figures: 8,194,226 and 52.0, key
`7a385189`. The derived "real matrix is 2.5x sparser than synthetic" claim was wrong too — it is
1.2x.

**New guard:** `gate_model.verify_constant_for()` now **refuses** to cost a radius pair it was not
measured at. 0.826 s belongs to (400 m solve, 800 m verify), not to the solver — reusing it at
600/1200 would repeat #16 exactly. `--verify-workers` now defaults to `min(cores, 12)` everywhere,
and the gate's default is pinned *to the solver's* by test.

Last session: **2026-08-09 (overnight)**. Local head `f4e7b81`. **`4c947d6` and `f4e7b81` are
committed LOCALLY AND UNPUSHED** — Marko authorised local commits only while asleep.

## READ FIRST — the feasibility gate is optimistic by 2.35x

**The v2 nine-block run took 9 h 25 m (`real 564m58s`), against the gate's 4.01 h estimate.**
That is not a rounding error, and it is measured on the official sample at the settled 400 m radius
with the exact flags the gate models.

| | gate says | actually measured |
|---|---|---|
| nine-block run | 4.01 h | **9.42 h** |
| headroom vs 20 h budget | 5.0x | **2.1x** |

**RE-FITTED 2026-08-09 (#16 done).** Decomposing v2's measured 33,898 s:

| phase | seconds | share |
|---|---|---|
| setup ×9 | 30 | **0.1%** |
| greedy | 6,174 | 18.2% |
| **verification** | **27,694** | **81.7%** |

Verification is not a correction term on the greedy model — **it is the runtime.** The constant was
`0.051` s per building per 1000 antennas; the measured value is **`0.826`**, **16.2× larger**. That
single constant is the whole 2.35× error. It now lives in `giscup.gate_model`, pinned by
`tests/test_gate_calibration.py` against the observed run.

**#18 done — verification is now parallel (`--verify-workers`).** It was single-core on a 16-core
host despite every building being independent. Measured on a real block under contention (so these
are floors): **1.77x at 2 workers, 3.10x at 4, 4.20x at 8, 4.70x at 12**, and **bit-identical to
serial at every level** — coverage decides which claims survive, so "close enough" is not enough.

| gate, 20 h budget | serial | 12 verify workers |
|---|---|---|
| upper bound | 19.34 h / **1.0x** | **6.87 h / 2.9x** |
| likely | 11.18 h / 1.8x | **5.14 h / 3.9x** |

Verification fell from 82% of the projected total to 49%. **The matrix build (99.5 min) is now the
largest single line** — and unlike the sample run it cannot be served from cache on the day.

The gate reports **two** numbers, because either alone misleads:

| | verify | total | headroom |
|---|---|---|---|
| upper bound (every building claimed) | 15.85 h | **19.34 h** | **1.0×** |
| likely (v2 claim fractions) | 7.70 h | 11.18 h | 1.8× |

The bound sets the verdict; the likely figure is what to plan around. Subtracting the 1.66 h matrix
build that v2 didn't pay (cached), the likely model predicts **9.52 h against 9.42 h actual — within
1%**.

**A correction to my own earlier claim.** I wrote that `solve-all`'s repeated setup cost "~8.5 min
per repeat, roughly 40% of a run". That was wrong — it misread the sweep's
`baseline greedy done [8.5 min]`, a *greedy* timing at k=500, as a setup timing. Setup measures
**3.32 s**; eight redundant repeats cost **27 s, 0.08%** of the run. The scene fix is still worth
keeping for its `SceneSpec` guard, and the partial-write half of that commit is unaffected — but
the speedup justification was fabricated from a misreading.

**This matters more for lever A than for baseline.** Lever A services *more* buildings, so it
verifies *more* claims, so it is strictly slower. The lever A nine-block run was at 2/9 blocks
after 142 min and projects to **~10–11 h**. On the day that is ~11 h of a ~24 h window, on a
dataset that may be larger than the March sample.

**Measured 2026-08-09, and the penalty is worse than "more claims" implies.** Lever A checks cost
**~1.8× more per building** than baseline's, not just more of them — at (0.25, 1000) lever A spent
261.6 min serial on 12,469 checks (1.26 s each) against baseline's 29.8 min parallel on 11,920
(0.150 s each). Correcting for the 4.70× worker speedup leaves a genuine 1.8× per-check gap. The
mechanism is the lever itself: near-tau selection parks buildings *at* the threshold, which is
exactly the band `--verify-band` catches and where exact coverage must be computed rather than
short-circuited. **Budget lever A at ~5 h on the day against baseline's 2.85 h**, and note that
the same property is what makes an overclaim audit non-optional for the lever A artifact.

**Rule 1 of the competition posture applies: feasibility outranks quality.** Re-run `/rehearsal`
with the verification cost re-fitted to 0.87 s/claim before treating any headroom figure as real.

## 2026-08-09 overnight — lever A is real, and its knob depends on tau

**The sweep control validated exactly.** `quantile=100` degenerates to the already-measured
threshold objective (lever B) and reproduced it at all three taus — `-1.1% / +0.3% / +6.4%`,
matching the prior measurement to the decimal. An independently written code path reproducing
three prior numbers is what makes the rest of the table trustworthy.

Measured against baseline greedy on the official sample, **k=500**:

| tau | q=25 | q=50 | q=100 | best |
|---|---|---|---|---|
| 0.75 | **+77.7%** | +60.1% | −1.1% | q=25 |
| 0.5 | +3.5% | **+8.6%** | +0.3% | q=50 |
| 0.25 | −8.3% | +0.2% | **+6.4%** | q=100 |

**The optimum moves monotonically: as tau rises, tighten the mask.** At tau=0.75 few buildings are
reachable, so concentrating fire pays enormously (1,312 → 2,331). At tau=0.25 nearly every
unserviced building is winnable and discriminating actively *hurts*.

This reframes lever B, which looked like a failure. It is not a bad lever — it is the **tau→0
corner of a one-parameter family**, and it had only ever been measured at the corner where it
happens to be right.

Capture against the pre-registered hard bound: **13.1%** (+1,019 of +7,756), against an estimate of
~14% made *before* the measurement existed. The sizing framework retrodicted the result.

**These are upper estimates, not score predictions.** `scripts/sweep_near_tau.py` counts serviced
buildings from the same sample grid the optimizer optimized on — the #12 defect, reproduced in the
analysis script. The bias is **asymmetric**: baseline's serviced buildings mostly sit clear of tau,
while lever A concentrates on buildings *at* the threshold, where in-sample error decides the
outcome. Compare post-verification claim counts in `outputs/nine_real_400_v2.txt` (baseline) against
`outputs/nine_leverA_400.txt` (lever A) — that is the honest measurement, and the first thing to do.

**The schedule also depends on k** (k=50 sweep): at tau=0.75 q=25 gives **+460.7%**, and at tau=0.5
q=25 (+37.7%) now beats q=50 (+22.1%) — the reverse of k=500. Smaller k → tighter quantile, same
mechanism as tau. **The CLI expresses per-tau schedules only, not per-(tau, k).** That is the open
design question, recorded as task #15.

## The one thing that matters

**2026-08-08 was a bug-fixing day, not a tuning day.** Six defects were found and fixed, four of
them the same class (relative or sub-resolution tolerances at projected magnitudes). **Every
solution-quality figure recorded before 2026-08-08 ~10:30 is void.** Feasibility timings are
unaffected; correctness figures are not. See task board #13–#17.

The largest, #14, made **32% of all boundary samples permanently unseeable** and alone delivered
**101x at tau=0.75** (13 → 1,312 serviced). No amount of objective tuning came close.

**Current status: the pipeline is proven end-to-end on correct data.** A full nine-block run on the
official dataset completed in 164 min, 27 content lines, 40,118 claims. The audit passed every
structural check — nine blocks, exactly-k counted, boundary legality, IDs — but found overclaims,
which #17 fixed. A re-run with the fix was in flight when this was written.

## What 2026-08-08 evening added

Four defects found, all by checking code against something *outside itself* -- the spec,
a foreign environment, or a changed dependency. Each produced output that looked perfect.

1. **Blank separator lines** (`output.py`). Nine blocks emitted 35 lines, not 27. The spec
   says three lines per subproblem AND allows an empty third line; a block claiming
   nothing plus a separator gives two consecutive blanks no parser can attribute. Could
   have invalidated every block. Files written before this carry separators --
   `--normalize-legacy` strips them, and refuses when a block claims nothing.
2. **`--id-property` never reached the solver.** `io.py` falls back to the row index when
   the field is missing. If August's extract names its ID field anything but `id`, every
   claim would reference a nonexistent building while passing every structural check.
   Now plumbed through both solve commands, warns and names the real fields, and records
   `DatasetInfo.id_fallback_used` in diagnostics. **Run `giscup inspect` first on the day.**
3. **`numpy>=1.26` declared, `np.bitwise_count` needs 2.0.** Four hot-path call sites.
   Surfaced only because a clean venv resolved 2.5.1 where the dev env has 2.4.6. Fixed
   in all three dependency files; four unused deps (tqdm, joblib, bitarray, orjson) dropped.
4. **The feasibility gate modelled deleted code.** It costed verification at the old
   band cap of 2,000/block while #17 re-checks every claim -- short by ~4x.

## Decisions settled

- **Cull radius: 400 m.** 800 m was attempted and abandoned — killed at 12/48 chunks tracking to
  ~15 h, leaving only 1.1x headroom on the day. Not robust: on unseen data a denser extract
  evaporates the window and all nine subproblems score zero. 600 m (~5.4 h, 2.5x headroom) remains
  the upgrade candidate if measured results justify it. Full cost model in task board #3b.
- **Threshold-aware objective (#6): superseded by lever A.** Lever B (`greedy_select_threshold`)
  is the `quantile=100` special case of the near-tau family. Kept, tested, still not wired.
- **Lever A (#6): built, measured, wired behind `--near-tau-quantile`, DEFAULT OFF.** The
  default does not change without Marko's call (task #15) — it is measured at k=500 and k=50
  on the **March sample only**, and the competition allows one submission with no feedback.
  `solve-all` takes one value per tau, aligned positionally with `--taus`; a count that does not
  line up is refused rather than guessed at.
- **Feasibility gate: PASS at 4.01 h / 5.0x headroom** (re-run 2026-08-08 on official data,
  15 cores). Supersedes the earlier 3.74 h / 5.3x figure, which predated #17. The gate's
  verification model was itself stale -- it costed the old band-capped pass at 7.9 min while
  #17 re-checks every claim. Now split into claim re-check (bounded by building count,
  50.8 min) and band recovery (7.9 min). Bounding claims by 12,860 is pessimistic at high
  tau and near-tight at low tau, which is the right direction for a gate.
- **Claims are verified exhaustively (#17)**, recovery stays banded. An overclaim is a correctness
  failure; a missed recovery is only lost score.
- **Audit at 400 m, not 800 m — REVISED 2026-08-09, the guidance was practically wrong.**
  The logic ("a tighter radius under-reports coverage, so it flags more, never fewer") is sound,
  but measured against v2 it produced **25 false failures and zero true ones** in block 1 alone.
  An alarm that only ever fires falsely cannot distinguish a real defect from noise.

  Every one of the 25 flagged claims at tau=0.25/k=50 holds when re-measured at 800 m — the radius
  the solver's own verification uses (`visibility_radius x verify_radius_factor`, 400 x 2). Worst
  case, building 8787: **0.1853 at 400 m, 0.5000 at 800 m.**

  **Audit at the verification radius or wider.** Auditing tighter than the solver verified is not
  conservatism, it is a guaranteed false-positive generator. Note the 25 were selected for having
  the lowest 400 m readings, so this does not show the cull costs that much generally — but it does
  show it can understate badly for buildings *near tau*, which are the ones that decide the score.

## Resume here

```bash
conda activate mz-giscup-26

# ALL BACKGROUND JOBS ARE DONE as of 2026-08-09 14:00. The machine is free.
#
#   b5vcoaz15  600 m matrix build + sizing   DONE. 434.5 min, +4.1% serviced,
#              ~1.6x headroom. Recommendation: 400 m stands (Marko's call, #3b).
#   bk22xn0vm  nine-block re-run at 12 verify workers  DONE. 171.1 min.
#              -> outputs/nine_verifypar_400.txt. EXACTLY equivalent to the
#              audited serial baseline: same antennas, same 39,120 claim IDs.
#              9.42 h -> 2.85 h, 3.30x. (Its auto-diff said DIFFERS; that was
#              the harness comparing bytes across a formatting change.)
#   bpzzrkr5r  lever A nine-block re-solve   KILLED 13:55 at block 6/9, on
#              Marko's instruction, after 10.4 h with ~7.8 h still to go --
#              it was launched before the --verify-workers default landed and
#              was verifying on one core. Five completed blocks preserved as
#              outputs/nine_leverA_400_5of9.txt; they answer #17 (+6.2%).

# 1. DONE (#16, #18). The gate is re-fitted and verification is parallel.
#    ALWAYS pass --verify-workers; serial puts the bound at 1.0x headroom.
python scripts/rehearse.py --input data/GIS-cup-sample-dataset.geojson \
    --cores 16 --measured-radius 400 --verify-workers 12
#    -> upper bound 6.87 h / 2.9x, likely 5.14 h / 3.9x
#
#    AND USE IT ON THE DAY -- solve-all takes --verify-workers too:
#    giscup solve-all ... --verify-workers 12

# 2. BASELINE IS DONE AND FULLY AUDITED -- AUDIT PASSED, 0 overclaims of 39,120
#    claims across all nine blocks (outputs/audit_v2.log). Task #8 is closed for
#    the baseline artifact.
#    outputs/nine_real_400_v2.txt      (8 blank separator lines -- predates the fix)
#    outputs/nine_real_400_v2_clean.txt (normalised: 27 lines, 0 blanks, 39,120 claims)

# 3. The A/B that decides lever A. Baseline claims are known: 39,120.
#    Compare against lever A's total once its run finishes.
python - <<'EOF'
import sys; sys.path.insert(0,'src')
from pathlib import Path
from giscup.packaging import inspect_solution
for name in ("outputs/nine_real_400_v2_clean.txt", "outputs/nine_leverA_400.txt"):
    if Path(name).exists():
        bl = inspect_solution(Path(name).read_text())
        print(f"{name}: {sum(b.n_claims for b in bl):,} claims")
EOF

# 4. Package (the clean file needs no --normalize-legacy)
python scripts/package_submission.py --solution outputs/nine_real_400_v2_clean.txt
```

**Packaging is rehearsed and verified** -- bundle extracted to a clean directory, fresh
venv, installed per the shipped instructions, CLI works, real dataset loads, shipped
source passes its own tests, SHA-256 matches across source/bundle/manifest.

Matrices in `outputs/cache` are keyed on `interior_tolerance`, so pre-#14 ones can never be reused.
The official 400 m matrix (key `7a385189…`, 8,194,226 pairs) is current and valid.

Local head: `be0a2bf Verify every claim exactly instead of by band (#17)`. Everything pushed.

## Known gaps, ranked

1. **The lever A schedule is fitted per-tau but the optimum is per-(tau, k).** Measured at k=500
   and k=50; k=1000 was in flight overnight. The nine-block artifact
   `outputs/nine_leverA_400.txt` was produced with the k=500-fitted schedule `100 50 25`, which
   is positive in every measured cell but optimal in only some. **Task #15 — Marko's call.**
2. **Everything is fitted on the March sample; August is a different extract.** This now matters
   more than it did: lever A's quantile is a *tuned* parameter, and the tuning may not transfer.
   The baseline objective has no such knob. An argument for keeping the default off.
3. **Every figure comes from the March sample; August is a different extract.** Config tuned here
   may not transfer — an argument for keeping the generous headroom.
4. **`solve-all` silence — FIXED 2026-08-08.** `src/giscup/progress.py` reports per-subproblem
   with an ETA weighted by *antennas placed*, not subproblems finished. The measured fit over the
   nine-block run is 2.16 s per antenna with a -24 s intercept, so cost is proportional to `k`;
   count weighting is off by 14x after the first (k=50) block. Progress is on by default,
   `--quiet` disables. The ETA is pessimistic early (131 min predicted vs 163 actual after one
   block) and converges to <1% by block 7 — the safe direction.
5. **My timing estimates ran optimistic five times today** (800 m build 2.6x, audit 16x, nine-block
   26%). Treat any projection of mine that is not calibrated against a measured run with suspicion.

## Repository

- Local root: `/home/markolinux/projects/sigspatial_26`
- Remote: `https://github.com/mzlatic1/mz_giscup_26.git`, branch `main`
- Pushed through `d7b9f6d`. **6 later commits are LOCAL AND UNPUSHED** — Marko's standing rule is
  that pushes need explicit approval each time, and he was asleep.
- Local head: `3166d19 Add the mechanical submission audit (#8)`
- Unpushed: `047159e` (gate PASS), `89945ab` (#13 exact coverage), `3bc49f3` (#10 deletions),
  `26aeedb` (#5 dataset + #3b calibration), `3166d19` (#8 audit), plus this docs commit.

## Environment

```bash
conda activate mz-giscup-26      # Python 3.11; required for all work
```

### Managing the multi-hour background jobs

This project runs several CPU-bound jobs for hours at a time, and they contend for **memory
bandwidth**, not just cores — four jobs on 16 cores cut the greedy pick rate from 59/min to 34/min.

- **Use `nice -n 15` when launching the low-priority job**, and let the scheduler arbitrate. Do not
  try to `renice`/`SIGSTOP` after the fact.
- **`pgrep -f <pattern>` matches your own shell**, because the pattern appears in that shell's own
  command line. On 2026-08-09 this suspended my own subshell and killed an authorised 600 m build
  outright (exit 147 = 128+19). Match on something narrower, or filter out the current shell's PID.
- A killed matrix build is **safe by design**: the metadata JSON is the completion marker, so a
  `.bits` file without its `.json` is rebuilt rather than trusted. One 2.6 GB orphan
  (`visibility-89846a10….bits`, no JSON) is in `outputs/cache` — harmless, overwritten on rebuild.

Host: **16 cores, 24 GB RAM** (the gate's 8-core assumption is conservative — 16 are available).
NumPy 2.4.6 (`np.bitwise_count` available), Shapely 2.1.2, SciPy 1.17.1.
**`ruff` and `mypy` are NOT installed** — `pip install -e .[dev]` if lint is needed.

## Data situation — read before trusting any number

**The official sample dataset is now present**: `data/GIS-cup-sample-dataset.geojson` (6.3 MB,
git-ignored), downloaded 2026-08-08 from
`https://sigspatial2026.sigspatial.org/img/GIS-cup-sample-dataset.geojson` (public, no
registration). Every documented statistic matches exactly: 12,860 buildings, 78,727 exterior
vertices, 858,973.22 m total perimeter, 1 hole-bearing polygon, EPSG:32611.

Test data still does not exist until 2026-08-15.

The synthetic stand-in (`outputs/synthetic_full.geojson`, regenerable via
`scripts/make_synthetic_dataset.py`) is still around and is what every pre-2026-08-08 figure was
measured on. **It understated reality in two ways that mattered:** it omitted the large-building
tail (real max perimeter 1,066 m, max area 17,957 m²) and it understated visibility reach, which
is why the 400 m cull costs ~9% on real data rather than the ~2% it implied. Prefer the official
dataset for everything from now on.

**Matrix cache keys are per-dataset.** The synthetic matrix cannot be reused for real-data solves.

`.gitignore` was tightened this session: `/outputs/*` matched only one level, so the 2.77 GB
matrix showed up as untracked. Now `/outputs/**` plus `*.bits`.

## What was built 2026-08-07

### #1 — `relate` default + erosion hoist (done)

`relate_pattern(poly, "T********")` is exactly the official predicate. Default flipped from
`hybrid` at all six entry points plus the CLI and `configs/defaults.yaml`. `buffer(-eps)` is
memoized per-eps on `BlockerIndex`; strategy dispatch was also hoisted out of the per-blocker loop
(it ran ~1,180 redundant string comparisons per unbounded pair).

**Correction to the board:** the claimed "~2.5x faster" was measured before the hoist. Re-measured
at full scale it is **1.16–1.40x** — hoisting sped `hybrid` up too. Still a win; the figure was
wrong.

### #7 — validation scales (done)

- `geometry.BoundaryIndex`: STRtree over boundaries. **1,877x** faster than the linear scan,
  identical results on 300 full-scale probes. 8.6 min → 0.3 s for k=1000 × 9 blocks.
- `validate.visible_sample_ids_from_points`: point-major with an early-out plus an optional
  `--validation-radius`. Nine blocks in ~95 min measured *under full CPU contention* (real number
  will be well under), against a naive 2.39e8 checks per block.
- Validation deliberately does **not** reuse the solver's matrix: a solution file's points need
  not be in the candidate set, and sharing the matrix would make validation blind to matrix bugs.
  Independence is the point.

### #11 — hole-perimeter question (done)

Official page re-checked verbatim: **"the polygons will not self-intersect and will not have
holes."** Moot on official data — with no interior rings, `polygon.length` equals exterior
perimeter. Defensive behaviour kept because the sample contradicts the page; the assumption and
its bounded cost are recorded in `docs/competition-reference.md`.

### #2 — visibility matrix (code complete, build unproven)

`src/giscup/matrix.py`. Dense candidate-major bit matrix, `uint64` words, memmap-backed.
Marko chose dense bitsets over sparse CSR after seeing the density measurement.

- cKDTree enumerates only pairs inside the radius; parallel workers write disjoint candidate
  ranges through the memmap, so 2.76 GB never crosses a pickle boundary. `fork` inherits
  buildings/candidates/samples copy-on-write; STRtree and KDTree are rebuilt per worker.
- Cache key: blake2b over building WKB + candidate coords + sample coords + radius + strategy +
  eps. The metadata JSON is the completion marker, so a crashed partial build is rebuilt, never
  trusted.
- `optimize.greedy_select_matrix` is tested to select **exactly** what the predicate-based greedy
  selects. `solver.solve_one` gained `--visibility-radius` / `--cache-dir` / `--matrix-workers`.
  The radius is opt-in and never implied.

## Bug found and fixed: `negative_buffer` reported everything visible

At EPSG:32611 magnitudes (~5e5, 3.7e6) `buffer(-1e-9)` is below float64 relative precision
(~2.7e-16 vs eps 2.2e-16) and collapses whole footprints to **empty**. Empty geometry blocks
nothing, so `negative_buffer` reported every pair visible — 56/400 disagreements with `relate` at
≤200 m on real-magnitude data.

`hybrid` survived only because it ORs with `relate`. The compounding danger: `validate-output`
accepts the same `--visibility-strategy`, so solving *and* validating on `negative_buffer` would
have produced a garbage solution that validated clean — the exact ROGII "blind local validation"
failure mode. It now raises with a message naming the cause. `hybrid` passes `strict=False`
because it stays correct.

**Recommendation carried to #10: delete both alternative strategies.** `relate` is the official
predicate; `hybrid` is identical to it but slower; `negative_buffer` is a footgun.

## Measured constants — 2026-08-07, full-scale synthetic

12,860 buildings, 138,077 samples (`balanced`), 160,198 candidates, domain 4,975 × 4,263 m.

Throughput with `relate` (400 pairs per row, 1 core; run-to-run variance ±10–25%):

| segment length | blockers/query | checks/s |
|---|---|---|
| unbounded | 1,180 | 537–580 |
| ≤ 400 m | 21 | 12,172–16,213 |
| ≤ 200 m | 7 | 23,169–25,775 |

Matrix density (150 probe candidates):

| radius | neighbours/candidate | visible/candidate | nonzeros | density |
|---|---|---|---|---|
| 200 m | 798 | 48.3 | 7.74M | 0.035% |
| 400 m | 3,048 | 60.5 | 9.70M | 0.044% |

**200 m → 400 m costs 6.2x the build time for +25% visible pairs.** A quarter of all visibility
lives in that band, so culling at 200 m forfeits real buildings. Radius **400 m** chosen.

**Build time reality check:** the 150-candidate probe projected 58 min on 8 cores; the actual
build tracked to **~117 min**. Contiguous chunks hit denser regions than random probes do, and
8 workers contend for memory bandwidth. Probe-based projections of this build run ~2x optimistic.

## Validation status — 2026-08-07

```bash
python -m pytest -q                        # 119 passed, 4 failed  (was 18 passed)
python -m compileall -q src tests scripts  # OK
```

The 4 failures are **expected and deliberate**: the `select_buildings_to_reverify` tests in
`tests/test_verify.py` fail on `NotImplementedError` because the selection policy is an open
decision for Marko (task #3). Everything else is green. Once that function lands the suite should
read 123 passed.

## Known limitations carried forward

- Greedy objective is still raw newly-visible-sample count, not serviced-building count (#6).
- Candidate "pruning" modes only add candidates; they prune nothing (#9). **Do not enable pruning
  without rebuilding the matrix** — it changes the candidate digest and invalidates the cache.
- `configs/defaults.yaml` is still not wired into the CLI.
- `scripts/compare_configs.py` and `scripts/profile_visibility.py` are placeholders.
- `negative_buffer` / `hybrid` visibility strategies should be deleted (#10).
- The cull radius is a heuristic with no feedback; the un-culled verification pass (#3) is
  scaffolded but its selection policy is unimplemented.
- Only `greedy` exists as an optimizer. `lazy-greedy` / `stochastic-greedy` / `hybrid` raise.

## Session log

**2026-08-07 — critical path: #1, #7, #11 done; #2 built; #3 scaffolded.** See sections above.
Two board corrections recorded (relate speedup 2.5x → 1.16–1.40x; build-time projection 2x
optimistic). One silent-overclaim bug found and guarded. `.gitignore` tightened to keep the
2.77 GB matrix out of git.

**2026-08-06 — Codex to Claude Code migration, security hardening, feasibility gate.**
`AGENTS.md` → `CLAUDE.md`; `.agents/` + `.codex/` → `.claude/agents/` and `docs/reference/`.
Added `/startup`, `/wrapup`, `/solve`, `/rehearsal`, the `giscup-output-format` skill,
`scripts/make_synthetic_dataset.py`, and `scripts/rehearse.py`. `.claude/settings.json` hardened
after a security review found 3 issues; the `data/**` deny is a backstop, not a guarantee — it
does not cover shell writes. Encoded the ROGII lessons as rules and gates.
