#!/usr/bin/env python
"""Assemble the final GIS Cup submission zip.

Official requirement: a zip containing the results file and "your source code, along
with instructions for compiling and running the program".

    python scripts/package_submission.py \
        --solution outputs/nine_real_400_v2.txt \
        --dest outputs/submission

Refuses to package a solution that is not nine blocks of exactly three lines with
exactly `k` points each -- this is the last gate before submission, so it fails loudly
rather than shipping something malformed. The results file is copied byte for byte;
coordinates are never re-serialised.

Solutions written before 2026-08-08 separate blocks with blank lines. Pass
`--normalize-legacy` to strip those; it removes only wholly-empty lines and refuses if
any block legitimately claims nothing, since a blank line is then ambiguous.
"""

from __future__ import annotations

import argparse
import sys
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from giscup.packaging import (  # noqa: E402
    PackagingError,
    build_bundle,
    inspect_solution,
    normalize_legacy_separators,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--solution", required=True, help="Nine-block results file")
    parser.add_argument("--dest", default="outputs/submission")
    parser.add_argument("--repo", default=str(Path(__file__).resolve().parents[1]))
    parser.add_argument("--name", default=None, help="Bundle name (default: dated)")
    parser.add_argument(
        "--normalize-legacy",
        action="store_true",
        help="Strip pre-2026-08-08 blank separator lines before packaging.",
    )
    args = parser.parse_args(argv)

    solution = Path(args.solution)
    dest = Path(args.dest)
    dest.mkdir(parents=True, exist_ok=True)

    if args.normalize_legacy:
        raw = solution.read_text(encoding="utf-8")
        normalized = normalize_legacy_separators(raw)
        if normalized.replace("\n", "") != raw.replace("\n", ""):
            raise PackagingError("normalisation altered file content; refusing")
        solution = dest / "solution_canonical.txt"
        solution.write_text(normalized, encoding="utf-8")
        print(f"normalised legacy separators -> {solution}")

    blocks = inspect_solution(solution.read_text(encoding="utf-8"))
    print(f"solution     : {solution}")
    for i, b in enumerate(blocks, 1):
        print(f"  block {i}    : tau={b.tau:<6g} k={b.k:<6d} {b.n_claims:,} claims")
    print(f"  totals     : {sum(b.k for b in blocks):,} antennas, "
          f"{sum(b.n_claims for b in blocks):,} claims")

    zip_path = build_bundle(
        repo=Path(args.repo), solution=solution, dest=dest, name=args.name
    )
    with zipfile.ZipFile(zip_path) as zf:
        assert zf.testzip() is None
        count = len(zf.namelist())
    print(f"\nbundle       : {zip_path}")
    print(f"size         : {zip_path.stat().st_size / 1024:.1f} KiB, {count} files")
    print("\nUpload to EasyChair: https://easychair.org/conferences/?conf=giscup2026")
    print("(published 2026-08-15; an account is required. This line said the link was")
    print("unpublished until then.) Break-glass: alowe@esri.com, ashashidharan@esri.com")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except PackagingError as exc:
        print(f"REFUSED: {exc}", file=sys.stderr)
        raise SystemExit(2) from exc
