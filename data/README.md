# Data Directory

Place official GIS Cup datasets here for local runs:

```text
data/GIS-cup-sample-dataset.geojson        # March 31, 2026 sample -- 12,860 buildings
data/GIS-cup-competition-dataset.geojson   # August 15, 2026 test data -- 50,000 buildings
data/competition-parameters.txt            # the published (tau, k) grid, shipped with the test data
```

Both datasets are EPSG:32611 (UTM 11N). The test data shipped inside the official evaluator
repository rather than as a link on the competition page.

`competition-parameters.txt` is the authority on which nine subproblems to solve. Nothing in the
codebase hardcodes them, and nothing reads this file for you -- read it, then pass the values
through `--taus`/`--ks` on every command that takes them.

The `.geojson` files are intentionally untracked: they are large, and they are official inputs that
should be obtained from the organisers rather than from this repository.

Nothing here is ever written by the solver. Official files are read-only inputs, and derived or
temporary artifacts belong under `outputs/` or an explicitly named scratch path.
`.claude/settings.json` denies `Write`/`Edit` on `data/**` as a backstop, but that guard covers only
those two tools -- a shell redirect, a `cp`, or an `--output data/...` flag would still land here.
The rule, not the guard, is what protects the inputs.
