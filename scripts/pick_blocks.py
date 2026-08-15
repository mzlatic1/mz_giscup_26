#!/usr/bin/env python
"""Choose, per subproblem, between two solved solutions -- and merge the winners.

WHY THIS EXISTS
---------------
`scripts/assemble_blocks.py` deliberately **refuses** when a `(tau, k)` appears in
more than one input: "two solutions for one subproblem means picking a winner
arbitrarily, so nothing is assembled". That is exactly right for crash recovery,
where overlap means ambiguity.

The approved `k=9` best-of creates overlap **on purpose**. `outputs/final.txt` holds
all nine blocks and `outputs/k9_baseline.txt` holds three `k=9` blocks, colliding on
precisely the subproblems being compared -- so `assemble_blocks.py` cannot perform
that merge. This tool performs it, with the choice stated explicitly rather than
inferred.

TWO MODES, AND THE DEFAULT IS THE SAFE ONE
------------------------------------------
* **Report** (no `--take-alt`): print claimed-ID counts per subproblem for both
  files and write nothing. This is the comparison step.
* **Merge** (`--take-alt TAU,K ...`): emit the full grid, taking the named
  subproblems from `--alt` and every other from `--base`.

Nothing is inferred from the counts. A higher claim count is not automatically the
better block -- claims are only worth what an audit says they are worth, and an
overclaim costs more than the points it chases. The operator names the winners; this
tool refuses to guess.

**Coordinates are copied byte for byte.** No number here is ever reparsed or
reformatted: `format(x, ".17g")` output must survive unchanged or antennas move off
the boundaries they are required to lie on. Only the `(tau, k)` header is re-emitted,
and it carries no precision to lose.

**Audit the result.** Like every assembler in this repository, this one checks
structure, not correctness. Run `scripts/audit_submission.py` on the output before
packaging it.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from giscup.assemble import (  # noqa: E402
    _count_points,
    _format_key,
    parse_blocks,
    subproblem_grid,
)


def _count_claims(claims: str) -> int:
    """Number of claimed building IDs on a block's third line.

    The line is legitimately empty for a block that services nothing (and for every
    filler block), which must read as 0 rather than 1.
    """
    stripped = claims.strip()
    if not stripped:
        return 0
    return len([part for part in stripped.split(",") if part.strip()])


def _load(path: Path) -> dict[tuple[float, int], object]:
    return {(b.tau, b.k): b for b in parse_blocks(path.read_text(encoding="utf-8"))}


def _parse_selection(raw: list[str]) -> list[tuple[float, int]]:
    out: list[tuple[float, int]] = []
    for item in raw:
        try:
            tau_s, k_s = item.split(",")
            out.append((float(tau_s), int(k_s)))
        except ValueError:
            raise SystemExit(
                f"--take-alt expects TAU,K (e.g. 0.32,9); got {item!r}"
            ) from None
    return out


def main() -> int:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    ap.add_argument("--base", required=True, help="the solution holding the full grid")
    ap.add_argument("--alt", required=True, help="the challenger, may hold a subset")
    ap.add_argument("--taus", nargs="+", type=float, required=True)
    ap.add_argument("--ks", nargs="+", type=int, required=True)
    ap.add_argument(
        "--take-alt", nargs="*", default=None, metavar="TAU,K",
        help="Subproblems to take from --alt. Omit entirely to report and write nothing.",
    )
    ap.add_argument("--output", help="required when --take-alt is given")
    ap.add_argument("--force", action="store_true", help="overwrite --output if it exists")
    args = ap.parse_args()

    grid = subproblem_grid(args.taus, args.ks)
    base = _load(Path(args.base))
    alt = _load(Path(args.alt))

    for name, blocks in (("--base", base), ("--alt", alt)):
        extra = [key for key in blocks if key not in grid]
        if extra:
            listed = ", ".join(_format_key(*key) for key in extra)
            raise SystemExit(
                f"{name} contains subproblems outside the given grid: {listed}. "
                "Check --taus/--ks against data/competition-parameters.txt."
            )

    missing = [key for key in grid if key not in base]
    if missing:
        listed = ", ".join(_format_key(*key) for key in missing)
        raise SystemExit(f"--base is not a complete grid; missing {listed}")

    # --- report ---------------------------------------------------------------
    print(f"{'subproblem':>16}  {'base claims':>12}  {'alt claims':>12}   delta")
    for key in grid:
        b = _count_claims(base[key].claims)
        if key in alt:
            a = _count_claims(alt[key].claims)
            delta = a - b
            mark = "  <-- alt higher" if delta > 0 else ("  <-- base higher" if delta < 0 else "  tie")
            print(f"{_format_key(*key):>16}  {b:>12,}  {a:>12,}  {delta:+,}{mark}")
        else:
            print(f"{_format_key(*key):>16}  {b:>12,}  {'-':>12}       -")

    if args.take_alt is None:
        print()
        print("Report only -- nothing written. Claim counts are not a verdict: run the audit,")
        print("then re-run with --take-alt TAU,K ... --output FILE to merge the winners.")
        return 0

    # --- merge ----------------------------------------------------------------
    if not args.output:
        raise SystemExit("--output is required when --take-alt is given")
    out = Path(args.output)
    if out.exists() and not args.force:
        raise SystemExit(f"refusing to overwrite {out} without --force")

    take = _parse_selection(args.take_alt)
    unknown = [key for key in take if key not in grid]
    if unknown:
        listed = ", ".join(_format_key(*key) for key in unknown)
        raise SystemExit(f"--take-alt names subproblems outside the grid: {listed}")
    absent = [key for key in take if key not in alt]
    if absent:
        listed = ", ".join(_format_key(*key) for key in absent)
        raise SystemExit(f"--alt does not contain {listed}; nothing written")

    chosen = set(take)
    lines: list[str] = []
    for key in grid:
        block = alt[key] if key in chosen else base[key]
        found = _count_points(block.points)
        if found != block.k:
            source = "--alt" if key in chosen else "--base"
            raise SystemExit(
                f"subproblem {_format_key(*key)} from {source} has {found} coordinates "
                f"but declares k={block.k}. A block must contain exactly k points; a "
                f"truncated partial write looks exactly like this. Nothing written."
            )
        lines.extend([_format_key(*key), block.points, block.claims])

    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    listed = ", ".join(_format_key(*key) for key in take)
    print()
    print(f"wrote {out} -- {len(grid)} blocks, {len(take)} taken from --alt ({listed})")
    print("Now run scripts/audit_submission.py on it, then package_submission.py.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
