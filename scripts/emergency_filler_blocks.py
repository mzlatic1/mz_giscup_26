#!/usr/bin/env python
"""Pad a partial solution up to nine blocks so it can be packaged and submitted.

WHY THIS EXISTS
---------------
`solve-all` writes `outputs/final.txt.partial` after every block, so a run killed at
block 7 leaves six good blocks on disk. `scripts/assemble_blocks.py` can merge those
with re-solved blocks -- but on submission night there may be no time left to re-solve
anything, and `giscup.packaging.inspect_solution` **refuses any file that is not
exactly nine blocks** (`EXPECTED_BLOCKS = 9`).

That combination is a cliff. At the drop-dead hour, six good blocks and no time is
indistinguishable from nothing at all: the packager rejects the file, and the operator
has to write this script under maximum time pressure. Scoring is per-subproblem
(`team score / best score`, summed over nine), so six real blocks plus three throwaways
scores six blocks' worth. Submitting nothing scores zero.

WHAT A FILLER BLOCK IS
----------------------
Exactly `k` antennas taken **verbatim from building boundary vertices**, and an empty
claims line. It scores 0 for that subproblem and is guaranteed structurally legal:

* Source vertices are already on a boundary, exactly. Nothing is interpolated, so the
  ULP-off-the-line hazard that produced defect #14 cannot arise here -- an interpolated
  midpoint lands inside the polygon about half the time, a source vertex never does.
* Claims are empty, so the block cannot overclaim. An overclaim is the one error that
  costs more than the points it chases.
* Coordinates are emitted with `format(x, ".17g")`, the same writer the solver uses.

**Blocks that already exist are copied byte for byte** and are never reparsed or
reformatted, exactly as `assemble_blocks.py` does -- `.17g` output must survive
unchanged or antennas move off the boundaries they are required to lie on.

THIS IS A LAST RESORT. It converts an unsubmittable file into a submittable one; it
does not make the missing subproblems any better than zero. Re-solving a missing block
beats filling it every time there is time to re-solve.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from giscup.assemble import _format_key, parse_blocks, subproblem_grid  # noqa: E402
from giscup.io import load_buildings  # noqa: E402


def _format_point(x: float, y: float) -> str:
    return f"({format(x, '.17g')}, {format(y, '.17g')})"


def legal_vertices(dataset: Path, id_property: str, needed: int) -> list[tuple[float, float]]:
    """Collect `needed` distinct boundary vertices, spread across distinct buildings.

    Spreading is not cosmetic. Taking `k` vertices off one footprint would put every
    antenna of the block on a single building, which is legal but pathological, and it
    makes a filler block visually indistinguishable from a solver bug in the output
    file. One vertex per building, cycling, keeps it obviously synthetic.
    """
    buildings, _ = load_buildings(dataset, id_property=id_property)
    if not buildings:
        raise SystemExit("dataset contains no buildings")

    picked: list[tuple[float, float]] = []
    seen: set[tuple[float, float]] = set()
    ring = 0
    while len(picked) < needed:
        progressed = False
        for b in buildings:
            coords = b.exterior_coords
            if ring >= len(coords):
                continue
            progressed = True
            pt = (float(coords[ring][0]), float(coords[ring][1]))
            if pt not in seen:
                seen.add(pt)
                picked.append(pt)
                if len(picked) == needed:
                    return picked
        if not progressed:
            raise SystemExit(
                f"dataset has only {len(picked)} distinct boundary vertices, need {needed}"
            )
        ring += 1
    return picked


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--input", required=True, help="the buildings geojson")
    ap.add_argument("--partial", required=True, help="partial solution, e.g. outputs/final.txt.partial")
    ap.add_argument("--output", required=True)
    ap.add_argument("--id-property", default="id")
    ap.add_argument("--taus", type=float, nargs="+", required=True)
    ap.add_argument("--ks", type=int, nargs="+", required=True)
    ap.add_argument("--force", action="store_true", help="overwrite --output if it exists")
    args = ap.parse_args()

    out = Path(args.output)
    if out.exists() and not args.force:
        raise SystemExit(f"refusing to overwrite {out} without --force")

    grid = subproblem_grid(args.taus, args.ks)
    have = {(b.tau, b.k): b for b in parse_blocks(Path(args.partial).read_text(encoding="utf-8"))}

    missing = [(tau, k) for (tau, k) in grid if (tau, k) not in have]
    unexpected = [key for key in have if key not in grid]
    if unexpected:
        raise SystemExit(
            f"partial contains blocks outside the given grid: {unexpected}. "
            "Check --taus/--ks against data/competition-parameters.txt."
        )
    if not missing:
        print(f"nothing to fill: all {len(grid)} blocks present in {args.partial}")
        return 0

    print(f"present: {len(have)} of {len(grid)}   filling: {missing}", flush=True)
    vertices = legal_vertices(Path(args.input), args.id_property, max(k for _, k in missing))

    lines: list[str] = []
    for tau, k in grid:
        block = have.get((tau, k))
        if block is not None:
            # Coordinates byte for byte -- `points` and `claims` are never reinterpreted.
            # Only the header is re-emitted, and it carries no precision to lose.
            lines.extend([_format_key(tau, k), block.points, block.claims])
        else:
            pts = ", ".join(_format_point(x, y) for x, y in vertices[:k])
            lines.extend([_format_key(tau, k), pts, ""])

    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"wrote {out} -- {len(grid)} blocks, {len(missing)} of them FILLER (score 0)")
    print("Now run scripts/audit_submission.py on it, then package_submission.py.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
