# Release-minute commands — 2026-08-15 16:00 UTC / 09:00 PDT

Copy-paste sequence for the first hour after the dataset publishes. **This is not the runbook** —
`docs/submission-day-runbook.md` carries the reasoning, the stop conditions, and what to do when
something looks wrong. This page exists so that nothing has to be *composed* at the release minute,
because composing a command under time pressure is how a flag gets dropped.

Every value below is a closed decision. **Do not re-open one here.**

## ⚠️ THE RELEASE MINUTE HAS HAPPENED — these are the REAL values, 2026-08-15 09:17 PDT

The placeholders below are no longer placeholders. **The published grid is NOT the assumed one**,
so any recovery run must use these exact values or it solves the wrong problem:

```bash
conda activate mz-giscup-26
cd /home/markolinux/projects/sigspatial_26

export DS=data/GIS-cup-competition-dataset.geojson
export IDPROP=id                          # CONFIRMED: inspect stderr was empty, no fallback
export TAUS="0.32 0.49 0.68"              # PUBLISHED -- was assumed 0.25 0.5 0.75
export KS="9 49 484"                      # PUBLISHED -- was assumed 50 500 1000
```

The dataset shipped **inside the evaluator repo**, not as a page link:
`github.com/alowe/gis-cup-2026-evaluator`, commit `9af12a5`, adding
`datasets/GIS-cup-competition-dataset.geojson` and `datasets/competition-parameters.txt`. Both are
copied to `data/` (md5 `cf36adb386b8caf1415cf359d578245b`). **Never overwrite them.**

Measured facts about this extract, all confirmed 2026-08-15 (see `docs/session-state.md`):
50,000 buildings (3.89x the sample), 613,666 candidates, 512,589 samples, **39.3 GB matrix at
400 m**, `holes_count` 0, EPSG:32611, IDs `1..50000` unique ints, and the official loader parses it.

## 0 — environment (5 min)

```bash
python -m pytest -q                       # expect: 368 passed
nproc; free -g; df -h .                   # expect: 16 cores, ~21 GB available, 841 GB free
```

## 1 — parameters file (5 min) — DONE, and it did disagree

```bash
cat data/competition-parameters.txt
```

If it names a grid other than `0.25/0.5/0.75` x `50/500/1000`, **it wins** — reset `TAUS`/`KS` above
and carry them through every later command. Nothing hardcodes the nine any more, but nothing reads
the file for you either.

**It named `0.32/0.49/0.68` x `9/49/484`.** This is exactly the failure the 2026-08-15 overnight
hardening was written for: without `--taus`/`--ks` on the audit and the assembler, a *correct*
submission would have been failed at the last gate and crash recovery would have been dead.

The taus land cleanly in lever A's measured quantile schedule (`<=0.375 -> 100`, `<=0.625 -> 50`,
else `25`), so **no `--near-tau-quantile` override is needed or wanted**. Note the schedule was
fitted at k=500 and the real ks are 9/49/484 — that is an unquantified extrapolation, but re-fitting
it on the day is the "do not tune on the day" trap. Left alone deliberately.

## 2 — inspect, capturing stderr (5 min)

```bash
giscup inspect --input "$DS" 2>&1 | tee outputs/inspect.log
```

**Stop conditions.** Any of these means stop and escalate, not proceed:

- a `UserWarning` about the ID property appears → the ID field is wrong. Re-run with the real
  field name. **This is the only signal; it is not in the JSON.**
- `holes_count > 0` → the official loader cannot read this dataset at all.
- CRS is not a projected metre CRS, or coordinate magnitudes are unlike UTM 11N.
- `feature_count` materially above 12,860 → size it first, then see runbook §8.

## 3 — size it (10 min)

```bash
python scripts/rehearse.py --input "$DS" \
    --budget-hours 20 --cores 16 --measured-radius 400 --verify-workers 12
```

`--cores` defaults to **1** and `--measured-radius` to **None** — omitting either gives a
meaningless answer. Read both printed figures; the **bound** sets the verdict. March sample reads
8.14 h / 2.5x (bound) and 4.64 h / 4.3x (likely).

**Deliberately SKIPPED on 2026-08-15**, and the reasoning matters if you are re-deciding. With
`--measured-radius 400` the gate builds the very matrix the solve needs — ~4.6 h at this size — and
then the solve still has to run. Paying that serially inside a 24 h window, to re-confirm a gate that
has read PASS since 2026-08-07, is the wrong trade. It was replaced by a **direct measurement of the
binding constraint** (below), which took ten minutes.

### The one thing worth measuring at this size

At 613,666 candidates x 512,589 samples the matrix is **39.3 GB on a 24 GB machine**. That looks
like a hard stop and is not one:

| scan of the March matrix | rate |
|---|---|
| pages cached | 4.07 GB/s |
| pages dropped (`posix_fadvise(DONTNEED)`) | **4.09 GB/s** |
| raw disk, `dd iflag=direct` | 4.2 GB/s |

`marginal_gains` walks the memmap **sequentially in 4096-row chunks**, which kernel readahead
predicts perfectly, and the disk (4.2 GB/s) outruns the popcount pipeline (4.07 GB/s). The run is
bandwidth-bound, not cache-resident-bound, so residency is irrelevant and **no lever is needed**.
Had the access pattern been random, the same 39.3 GB would have been fatal — the distinction, not
the ratio of matrix to RAM, is what decides it.

## 4 — solve (the long one; **measured 2026-08-15: matrix ~7.8 h, whole run ~13–15 h**)

Launch immediately on clean checks. Marko's standing instruction: report, do not ask.

```bash
time giscup solve-all \
    --input "$DS" \
    --id-property "$IDPROP" \
    --taus $TAUS --ks $KS \
    --visibility-radius 400 \
    --cache-dir outputs/cache --matrix-workers 8 \
    --verify-band 0.10 --verify-max-buildings 2000 \
    --verify-workers 12 \
    --output outputs/final.txt \
    --diagnostics outputs/final.json \
    2>&1 | tee outputs/solve.log
```

**`--matrix-workers 8` is load-bearing — the flag defaults to `1`.** Objective defaults to
`near-tau` (lever A); do not pass `--objective` unless deliberately shipping baseline for a block.

Partial output lands in `outputs/final.txt.partial` after every block and is deleted on success.

### Reading progress while it runs — the log will NOT tell you

`progress=False` on this code path, so nothing is printed between `setup` and block 1 — during the
matrix build (**~7.8 h at competition size**) `solve.log` is silent. **Silence is not a stall.** The
`.bits` file is preallocated and zero-filled before any worker starts, so `ls -l` and `du` are dead
signals too: both read full size at 0% done.

Use the frontier probe instead. Workers write disjoint contiguous row chunks, so an unprocessed row
is still exactly zero:

```bash
python scripts/matrix_progress.py \
    --bits outputs/cache/visibility-<key>.bits --chunks 32   # chunks = matrix-workers * 4
```

It prints a per-chunk map and an overall percentage, is read-only, and drops the pages it reads so
it cannot evict the build's cache. Expect `workers` chunks partial at once; that is the healthy
shape. The **`.json` sidecar is the completion marker** — never file size.

Whole-run cost is arithmetic once the matrix exists: `marginal_gains` makes **one full pass per
greedy iteration** with no pruning, the matrix is built once and reused by all nine blocks, and
iterations total `3 x (9 + 49 + 484) = 1,626`. At the measured 4.09 GB/s pages-dropped scan rate,
one pass over 39.27 GB is ~9.6 s, so greedy is **~4.4 h** regardless of build time.

## 5 — audit (~10 min at 12 workers)

```bash
python scripts/audit_submission.py --input "$DS" \
    --solution outputs/final.txt \
    --taus $TAUS --ks $KS \
    --exact-radius 400 --confirm-radius 800 --workers 12
```

Must report: every block present, exactly `k` coordinates counted per block, 0 off-boundary,
0 unknown IDs, **0 overclaims**. Never confirm tighter than the solve verified.

## 6 — official evaluator (~1 h; start it the moment the solve finishes)

Setup and full detail: `scripts/official_evaluator/README.md`.

**The clone is already built, installed, and green — do NOT re-clone or re-`pnpm install` today.**

```text
/home/markolinux/projects/gis-cup-2026-evaluator     # evaluator commit 9af12a5, node_modules present,
                                                    # both driver files already copied in
```

Verified 2026-08-15 10:37 PDT: `pnpm test` -> **73 passed in ~2 s**. It was moved here from a session
scratchpad under `/tmp`, which would not have survived a WSL restart. Two traps if you ever do rebuild
it: the installed pnpm is **10.15.1** while `package.json` pins `packageManager: pnpm@11.16.0` (fine
only because `node_modules` already exists), and a fresh `git clone` gets whatever is current rather
than `9af12a5`, the commit that shipped the competition dataset.

```bash
cd /home/markolinux/projects/gis-cup-2026-evaluator
SCORE_DATASET=/home/markolinux/projects/sigspatial_26/$DS \
SCORE_SOLUTION=/home/markolinux/projects/sigspatial_26/outputs/final.txt \
SCORE_SUMMARY=/home/markolinux/projects/sigspatial_26/outputs/official-score.json \
SCORE_BLOCKS=1,4,7 \
pnpm exec vitest run --config vitest.score.config.ts --reporter=verbose
```

Cheap `k=50` blocks first (~1 min). If they agree, drop `SCORE_BLOCKS` and run all nine in the
background.

## 7 — package and submit

```bash
python scripts/package_submission.py --solution outputs/final.txt
```

Then eyeball: 27 content lines, nine `(tau, k)` headers, no blank separators, third line present in
every block even when empty.

Upload to **EasyChair**: `https://easychair.org/conferences/?conf=giscup2026`.
Log in and confirm the form is reachable *before* the bundle is ready.

## If the solve dies partway

```bash
giscup solve-all --input "$DS" --taus <only-missing> --ks <only-missing> ... \
    --output outputs/blocks_missing.txt

python scripts/assemble_blocks.py \
    --input outputs/final.txt.partial outputs/blocks_missing.txt \
    --taus $TAUS --ks $KS \
    --output outputs/final.txt --force
```

Re-solve **only** what is missing. `--near-tau-quantile` maps positionally onto `--taus`, so a
single-tau re-run takes a single value. Audit the assembled file afterwards — the assembler checks
structure, not correctness.

## ⏰ If there is no time left to re-solve — DROP-DEAD 03:30 PDT 2026-08-16

Full schedule and reasoning: `docs/submission-day-runbook.md`, top section. The one number to carry:
**if a usable nine-block file does not exist by 03:30 PDT on 2026-08-16, stop the solve and fill.**
That leaves 60 min audit + 90 min evaluator + packaging + a 1 h buffer before the 09:00 PDT deadline.

`packaging.inspect_solution` **refuses anything that is not exactly nine blocks**, so a six-block
partial is unsubmittable as it stands. Scoring is per subproblem — six real blocks plus three
throwaways scores six blocks' worth; nothing scores zero.

```bash
python scripts/emergency_filler_blocks.py \
    --input "$DS" --partial outputs/final.txt.partial \
    --taus $TAUS --ks $KS --output outputs/final_filled.txt

python scripts/audit_submission.py --input "$DS" --solution outputs/final_filled.txt \
    --taus $TAUS --ks $KS --exact-radius 400 --confirm-radius 800 --workers 12

python scripts/package_submission.py --solution outputs/final_filled.txt
```

Proven on the real competition dataset 2026-08-15: 0→9 and 6→9 both in 8.2 s, pre-existing blocks
`cmp`-identical, audit **PASSED / 0 off-boundary / rc 0**.

## After the solve — the approved `k=9` best-of

Marko approved this on 2026-08-15, for `k=9` **only**. Re-run the three cheap blocks against the
already-cached matrix and keep the better result per block:

```bash
giscup solve-all --input "$DS" --id-property "$IDPROP" \
    --taus $TAUS --ks 9 --objective baseline \
    --visibility-radius 400 --cache-dir outputs/cache --matrix-workers 8 \
    --verify-workers 12 --output outputs/k9_baseline.txt
```

Then compare and merge with `scripts/pick_blocks.py`. **Not `assemble_blocks.py`** — it *refuses* a
duplicated `(tau, k)` on purpose, and both files hold all three `k=9` blocks, so it would reject this
merge outright:

```bash
# 1. Report. Writes nothing.
python scripts/pick_blocks.py --base outputs/final.txt --alt outputs/k9_baseline.txt \
    --taus $TAUS --ks $KS

# 2. Merge, naming the winners explicitly (only k=9 subproblems are eligible).
python scripts/pick_blocks.py --base outputs/final.txt --alt outputs/k9_baseline.txt \
    --taus $TAUS --ks $KS --take-alt 0.32,9 0.49,9 0.68,9 \
    --output outputs/final_bestof.txt
```

Claim counts are a comparison, not a verdict — **audit both files first**; an overclaim costs more
than the points it chases. Then audit `final_bestof.txt` again before packaging.

This is selection between two audited results, not tuning: `near-tau`'s
quantile schedule was fitted at `k=500` and `k=9` is a 55x extrapolation that has never been
measured. **`k=49` and `k=484` ship `near-tau` untouched.**
