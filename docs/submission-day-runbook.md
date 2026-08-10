# Submission-day runbook

**Test data 2026-08-15. Deadline 2026-08-16. One submission, no score feedback, ever.**
Scoring is relative (`team score / best submitted score`, summed over nine subproblems), so a
subproblem that does not finish scores ~0.

This page is the operational sequence. It exists because on the day the risk is not algorithmic —
it is clerical. Every step below is here because something went wrong at it during rehearsal.

Read `CLAUDE.md` first for the non-negotiable output constraints. This page assumes them.

---

## 0. Before anything (5 min)

```bash
conda activate mz-giscup-26
cd /home/markolinux/projects/sigspatial_26
python -m pytest -q                    # must be green before you touch the real data
nproc; free -g; df -h .                # 16 cores, 24 GB, and the matrix needs ~2.6 GB free
```

Put the downloaded dataset under `data/`. **Never overwrite it.** `.claude/settings.json` denies
`Write`/`Edit` on `data/**`, but that guard does not cover shell redirects, `cp`, or an
`--output data/...` flag.

## 1. Inspect the extract FIRST — do not skip this (5 min)

```bash
giscup inspect --input data/<the-new-file>.geojson
```

Check, and write the answers down:

| Question | Why it matters | Rehearsal finding |
|---|---|---|
| What is the **ID property** called? | `io.py` silently falls back to the row index when the field is missing. Every claim would then reference a nonexistent building **while passing every structural check**. | Found 2026-08-08. Pass `--id-property <name>` if it is not `id`. |
| What is the **CRS**? | Tolerances are absolute in CRS units. The sample is EPSG:32611. | Do not assume; the code inspects, but you should too. |
| How many **buildings**, and total perimeter? | Drives every runtime projection below. The sample has 12,860. | If materially larger than 12,860, see §6. |
| Any **holes**? | The official page says no; the March sample had one. | Holes are preserved and included as obstacles. |
| Coordinate **magnitudes**? | At ~3.7e6 one ULP is ~5e-10 m. Everything about tolerance depends on this. | If magnitudes differ wildly from UTM 11N, stop and think. |

If `DatasetInfo.id_fallback_used` is true in diagnostics, **stop and fix the flag** before solving.

## 2. Size the run before committing to it (10 min)

```bash
python scripts/rehearse.py --input data/<the-new-file>.geojson \
    --budget-hours 20 --cores 16 --measured-radius 400 --verify-workers 12 \
    --objective baseline          # or: --objective near-tau, if shipping lever A
```

Read **both** numbers it prints — upper bound and likely. The bound sets the verdict; the likely
figure is what to plan around. On the March sample at 400 m these read 6.87 h / 2.9× and
5.14 h / 3.9×.

**Pass `--objective near-tau` if the solve will use `--near-tau-quantile`.** Verification is not
the same price for both objectives: lever A parks buildings *at* the threshold by design, which is
exactly where exact interval coverage cannot short-circuit, and it measured **1.26** s per building
per 1000 antennas against baseline's **0.826**. Costing a lever A day as baseline hides **+1.77 h**
on the bound and **+0.86 h** on the likely figure. The two flags must agree — if `solve-all` gets
`--near-tau-quantile`, the gate gets `--objective near-tau`.

The gate **refuses** to cost a radius pair or an objective it was not measured at. That is
deliberate, and it is the same defect twice: the verification constant belongs to (400 m solve,
800 m verify) *and* to baseline greedy, not to the solver in general. Change
`--visibility-radius`, `--verify-radius-factor`, or the objective, and the gate stops rather than
lies. An unrecognised objective is refused rather than defaulted, because baseline is the cheapest
constant in the module and would be the worst possible fallback.

## 3. Solve (the long step — budget ~5–7 h at March-sample size)

```bash
time giscup solve-all \
    --input data/<the-new-file>.geojson \
    --id-property <from step 1> \
    --taus 0.25 0.5 0.75 --ks 50 500 1000 \
    --visibility-radius 400 \
    --cache-dir outputs/cache --matrix-workers 12 \
    --verify-band 0.10 --verify-max-buildings 2000 \
    --verify-workers 12 \
    --output outputs/final.txt \
    --diagnostics outputs/final.json
```

Notes that cost hours if forgotten:

- **`--verify-workers`** now defaults to `min(cores, 12)`, but pass it explicitly so the log
  records what ran. Serial verification costs ~12 h of the window.
- **The matrix build cannot come from cache.** It is keyed on the dataset, so the new extract
  rebuilds from scratch — ~100 min at 400 m on the March sample. This is the largest single line.
- **Partial output is written after every block** to `outputs/final.txt.partial`. If the run dies
  at block 7, you still have six blocks. The `.partial` file is removed on success.

  **To use them**, re-solve only what is missing and merge — do not re-run all nine:

  ```bash
  giscup solve-all --input data/<file>.geojson --taus 0.75 --ks 500 1000 \
      ... --output outputs/blocks_89.txt          # only the missing subproblems

  python scripts/assemble_blocks.py \
      --input outputs/final.txt.partial outputs/blocks_89.txt \
      --output outputs/final.txt
  ```

  The assembler emits tau-outer/k-inner, copies coordinates verbatim, and **refuses** on a
  duplicated subproblem, a missing one, or a block whose coordinate count does not match its own
  `k`. It checks structure, not correctness — audit the assembled file afterwards.

  Watch the quantile mapping if you are shipping lever A: `--near-tau-quantile` maps positionally
  onto `--taus`, so a `--taus 0.75`-only re-run takes a single value (`25`), not all three.
- Progress prints per subproblem with an ETA weighted by antennas placed. It is pessimistic early
  and converges to <1% by block 7.

## 4. Audit before you believe it (~9 min at 12 workers; ~46 min serial)

```bash
python scripts/audit_submission.py --input data/<the-new-file>.geojson \
    --solution outputs/final.txt \
    --exact-radius 400 --confirm-radius 800 --workers 12
```

**`--exact-radius 400` is not optional — omitting it costs hours.** It defaults to `None`, and
the script passes that through as the *screen* radius, where `None` means **unbounded**: every
claim measured against the whole dataset instead of against blockers within 400 m. That is the
~8-hour path, on the last gate before submitting. Found 2026-08-09 by running it that way twice
and watching a five-block audit pass 3 h 25 m without finishing. The library default in
`giscup.audit` is 400 m; the *script* overrides it to `None`, so the flag must be passed
explicitly. **The two radii do different jobs** — 400 m screens cheaply, 800 m confirms only what
the screen flagged.

`--workers` defaults to `min(cores, 12)`; pass it explicitly so the log records what ran. This
step was single-core until 2026-08-09.

**Measured 2026-08-09** on five lever A blocks (27,803 claims, 1,550 antennas), both runs using
the two-stage radii above:

| | serial | 12 workers |
|---|---|---|
| wall clock | 28 m 51 s | **5 m 41 s** |
| speedup / efficiency | — | **5.08x, 96%** |
| verdict | identical to the parallel run, line for line | |

**Audit cost scales with claims x k**, exactly like the solver's verification, because every
claimed building is re-measured against every antenna. Fitting that against the run above gives
**0.090 s per building per 1000 antennas** at a 400 m screen — about 9x cheaper than the solver's
0.826 at 800 m, which is what the radius difference predicts. Projecting onto the March
baseline's nine blocks (30,354 building-k units): **~46 min serial, ~9 min at 12 workers.**

Do not size this step from claim counts alone. An earlier estimate did exactly that, using a
figure measured on `(0.25, 50)` at k=50, and came out 6x optimistic — `(0.25, 1000)` costs 20x
more per claim than that block does.

Must report: 9 blocks, exactly `k` coordinates **counted** per block, 0 off-boundary at
eps=1e-7, 0 unknown IDs, **0 overclaims**. The March baseline passed with 0 overclaims of
39,120 claims; the five audited lever A blocks passed with 0 overclaims of 27,803.

**Confirm at the verification radius or wider — never tighter.** Auditing a 400 m solve and
*confirming* at 400 m produced 25 false failures and zero real ones; the worst read 0.1853 at
400 m and 0.5000 at 800 m. A tighter confirm is not conservatism, it is a guaranteed
false-positive generator. This applies to `--confirm-radius`; the *screen* is deliberately tight,
because a tight screen over-flags and the confirm stage then clears the false alarms.

## 5. Package and submit

```bash
python scripts/package_submission.py --solution outputs/final.txt
```

If the solution file was produced by an older build carrying blank separator lines, add
`--normalize-legacy`. Files produced by current code need no such thing — they emit 27 content
lines with no separators.

Packaging is rehearsed end to end: bundle extracted to a clean directory, fresh venv, installed
per the shipped instructions, CLI works, real dataset loads, shipped source passes its own tests,
SHA-256 matches across source, bundle and manifest.

## 6. If the extract is much bigger than 12,860 buildings

Cost is roughly linear in buildings for verification and in candidates for the matrix build and
greedy. In order of what to give up:

1. **Prune the candidate pool 2×** (keep the vertex half). Measured free — one serviced building
   of 14,708 — and takes ~1.7 h off the day. **This changes the matrix cache key**, which is
   irrelevant on the day because nothing is cached anyway. Not yet implemented as a flag; see #9.
2. **Raise `--verify-workers`** if the host has more than 16 cores. Do not expect more than the
   4.70× measured at 12; efficiency was already down to 39% there.
3. **Do not raise the radius.** 600 m was measured at 4.36× the build time of 400 m for +8.5%
   visible pairs, and 800 m was abandoned at 1.1× headroom.
4. **Do not lower `--verify-radius-factor` below 2.0** to save time. That is the pass that makes
   overclaims structurally impossible, and an overclaim is a correctness failure.

## 7. What NOT to do on the day

- Do not round coordinates. `format(x, ".17g")`, always.
- Do not reproject, snap, or normalize the output.
- Do not emit a block with fewer or more than `k` points.
- Do not omit the third line of a block. It may be empty; it must exist.
- Do not tune the objective. Everything was fitted on the March sample; the August extract is a
  different extract, and a tuned parameter that does not transfer is worse than no parameter.
- Do not trust local validation as a score estimate. It is a rejection framework. It can tell you
  something is broken; it cannot tell you what you will score.
