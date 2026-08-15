# Release-minute commands — 2026-08-15 16:00 UTC / 09:00 PDT

Copy-paste sequence for the first hour after the dataset publishes. **This is not the runbook** —
`docs/submission-day-runbook.md` carries the reasoning, the stop conditions, and what to do when
something looks wrong. This page exists so that nothing has to be *composed* at the release minute,
because composing a command under time pressure is how a flag gets dropped.

Every value below is a closed decision. **Do not re-open one here.**

Placeholders to fill once, at the top, and then never retype:

```bash
conda activate mz-giscup-26
cd /home/markolinux/projects/sigspatial_26

export DS=data/<the-new-file>.geojson     # set after download
export IDPROP=id                          # confirm in step 2 before trusting this
export TAUS="0.25 0.5 0.75"               # confirm in step 1 -- competition-parameters.txt wins
export KS="50 500 1000"                   # confirm in step 1
```

## 0 — environment (5 min)

```bash
python -m pytest -q                       # expect: 365 passed
nproc; free -g; df -h .                   # expect: 16 cores, ~21 GB available, 841 GB free
```

## 1 — parameters file (5 min)

```bash
cat data/competition-parameters.txt
```

If it names a grid other than `0.25/0.5/0.75` x `50/500/1000`, **it wins** — reset `TAUS`/`KS` above
and carry them through every later command. Nothing hardcodes the nine any more, but nothing reads
the file for you either.

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

## 4 — solve (the long one, ~5 h at March size)

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

```bash
cd <evaluator-clone>
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
