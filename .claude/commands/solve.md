---
description: Run one (tau, k) subproblem end-to-end with diagnostics and validation
argument-hint: <tau> <k> [input-geojson]
allowed-tools: Bash(conda:*), Bash(giscup:*), Bash(python -m giscup.cli:*), Bash(ls:*), Read, Glob
---

# Solve subproblem tau=$1, k=$2

Input dataset: `$3` — if empty, default to `data/GIS-cup-sample-dataset.geojson`.

Available data:

!`ls -la data/ 2>/dev/null`

## Steps

1. **Check the input exists.** If it does not, stop and say so — do not silently substitute a
   synthetic dataset or a different file.

2. **Solve** in the `mz-giscup-26` Conda env:

```bash
giscup solve-one \
  --input <input> \
  --tau $1 \
  --k $2 \
  --output outputs/solution_tau_$1_k_$2.txt \
  --diagnostics outputs/diag_tau_$1_k_$2.json \
  --candidate-mode basic \
  --sampling-profile balanced \
  --optimizer greedy
```

3. **Validate** with a denser profile than the one used to solve — validating at the solve profile
   proves nothing about overclaiming:

```bash
giscup validate-output \
  --input <input> \
  --solution outputs/solution_tau_$1_k_$2.txt \
  --sampling-profile accurate
```

4. **Report:**
   - serviced-building count and coverage distribution from the diagnostics JSON
   - confirmation that the output block contains **exactly $2** coordinates
   - any validation failure, verbatim
   - runtime, and whether it would plausibly scale to the full dataset at this `k`
   - how many claimed buildings sit within a hair of `tau` — those are the overclaim risk

Never edit `outputs/solution_*.txt` by hand to make validation pass. If validation fails, the
solver or the claim margin is wrong, and that is the finding to report.
