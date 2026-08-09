"""Build one nine-block submission out of separately-solved block files.

Recovery path for a run that died partway, and for deliberately solving blocks in
separate passes. `solve-all` writes `<output>.partial` after every block, so a run
that dies at block 7 leaves six good blocks -- this is what consumes them.

    python scripts/assemble_blocks.py \
        --input outputs/final.txt.partial outputs/blocks_789.txt \
        --output outputs/final.txt

Inputs may be given in any order and may each hold any number of blocks. The result
is emitted tau-outer, k-inner, as 27 content lines with no separators.

**Coordinates are copied verbatim.** Nothing here reparses or reformats a number:
`format(x, ".17g")` output has to survive byte for byte.

It refuses rather than guesses -- on a duplicated subproblem, a missing one, or a
block whose coordinate count does not match its own k. Structure is all it can check.
**Run `scripts/audit_submission.py` on the result before submitting**; this tool
cannot tell you the blocks are correct, only that they form a well-shaped file.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from giscup.assemble import REQUIRED_SUBPROBLEMS, assemble_blocks, parse_blocks  # noqa: E402


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    ap.add_argument("--input", nargs="+", required=True, help="Block files, in any order.")
    ap.add_argument("--output", required=True)
    ap.add_argument(
        "--force", action="store_true",
        help="Overwrite --output if it exists. Off by default: the likeliest target is "
             "the submission file itself.",
    )
    return ap


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    out = Path(args.output)
    if out.exists() and not args.force:
        print(f"refusing to overwrite {out} (pass --force if that is what you want)")
        return 1

    texts = []
    for path in args.input:
        text = Path(path).read_text(encoding="utf-8")
        blocks = parse_blocks(text)
        listed = ", ".join(f"({b.tau:g}, {b.k})" for b in blocks)
        print(f"{path}: {len(blocks)} block(s)  {listed}")
        texts.append(text)

    try:
        assembled = assemble_blocks(texts)
    except ValueError as exc:
        print(f"\nNOT ASSEMBLED: {exc}")
        return 1

    out.write_text(assembled, encoding="utf-8")
    lines = assembled.splitlines()
    print(f"\nwrote {out}: {len(lines)} lines, {len(REQUIRED_SUBPROBLEMS)} blocks")
    for i in range(0, len(lines), 3):
        n_pts = lines[i + 1].count("(")
        n_claims = len([c for c in lines[i + 2].split(",") if c.strip()])
        print(f"  {lines[i]:>14}  {n_pts:>5,} antennas  {n_claims:>6,} claims")
    print("\nNow audit it -- this tool checked structure, not correctness:")
    print(f"  python scripts/audit_submission.py --input <geojson> --solution {out} "
          f"--confirm-radius 800 --workers 12")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
