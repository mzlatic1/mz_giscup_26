#!/usr/bin/env python
"""Mechanical audit of a nine-block solution file (task board #8).

Checks every item in `.claude/skills/giscup-output-format/SKILL.md`. Each check is
computed from the file itself -- nothing is trusted from a header or from the solver's
own diagnostics, because the failure mode this guards against is precisely the solver
believing something the file does not say.

    python scripts/audit_submission.py --input <geojson> --solution <txt>

Exit code 0 only if every check passes. Anything else means do not submit.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from giscup.assemble import DEFAULT_KS, DEFAULT_TAUS, subproblem_grid  # noqa: E402
from giscup.audit import confirm_overclaims  # noqa: E402
from giscup.gate_model import default_verify_workers  # noqa: E402
from giscup.geometry import BoundaryIndex  # noqa: E402
from giscup.io import load_buildings  # noqa: E402
from giscup.output import parse_points  # noqa: E402
from giscup.visibility import BlockerIndex  # noqa: E402

# Defaults only. The dataset's competition-parameters.txt outranks them -- see --taus.
EXPECTED_TAUS = DEFAULT_TAUS
EXPECTED_KS = DEFAULT_KS

# A coordinate that went through format(x, ".17g") and needed precision will carry
# many significant digits. Six-decimal rounding is the documented failure mode.
SIX_DECIMAL = re.compile(r"^-?\d+\.\d{1,6}$")


class Audit:
    def __init__(self) -> None:
        self.failures: list[str] = []
        self.notes: list[str] = []

    def check(self, ok: bool, label: str, detail: str = "") -> bool:
        mark = "PASS" if ok else "FAIL"
        print(f"  [{mark}] {label}" + (f" -- {detail}" if detail else ""))
        if not ok:
            self.failures.append(label)
        return ok

    def note(self, label: str) -> None:
        """Record something worth reading that must not move the verdict.

        Distinct from a failed `check`: a note never blocks submission. Used where a
        heuristic is inapplicable to the dataset at hand and an exact check already
        covers the same hazard.
        """
        print(f"  [NOTE] {label}")
        self.notes.append(label)


def parse_blocks(text: str) -> list[tuple[float, int, str, str, int]]:
    """Return (tau, k, points_line, claims_line, first_line_number) per block.

    Split on newlines rather than with `splitlines()`: the latter drops a trailing
    empty string, so a final block with an empty claims line -- legal, since the third
    line may be empty -- parsed as truncated and failed a valid submission. Found
    2026-08-09; `giscup.assemble.parse_blocks` had the identical defect.
    """
    lines = text.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    blocks = []
    i = 0
    while i < len(lines):
        while i < len(lines) and not lines[i].strip():
            i += 1
        if i >= len(lines):
            break
        if i + 2 >= len(lines):
            raise ValueError(f"incomplete block starting at line {i + 1}")
        header = lines[i].strip()
        tau_s, k_s = header.strip("()").split(",")
        blocks.append((float(tau_s), int(k_s), lines[i + 1].strip(), lines[i + 2].strip(), i + 1))
        i += 3
    return blocks


def screen_radius(value: str) -> float | None:
    """A screen radius in CRS units, or None for an unbounded screen.

    Unbounded stays reachable because it is the exact answer, but it has to be asked
    for by name. It was the default until 2026-08-09, which meant an ~8-hour audit was
    what you got for omitting a flag -- measured, twice, at 3 h 25 m without finishing
    on a five-block artifact.
    """
    if value.strip().lower() in {"none", "unbounded"}:
        return None
    return float(value)


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--input", required=True)
    ap.add_argument("--solution", required=True)
    ap.add_argument("--eps", type=float, default=1e-7)
    ap.add_argument("--claim-margin", type=float, default=0.0)
    ap.add_argument(
        "--confirm-radius",
        type=float,
        default=800.0,
        help=(
            "Anything the --exact-radius screen flags is re-measured at this radius "
            "before being reported. Must be >= --exact-radius. Set at or beyond the "
            "solver's verification radius (visibility-radius x verify-radius-factor, "
            "800 m by default). Auditing at the screen radius alone produced 25 false "
            "failures and zero real ones on the v2 run."
        ),
    )
    ap.add_argument(
        "--exact-radius", type=screen_radius, default=400.0,
        help=(
            "Radius for the cheap SCREEN stage. Anything it flags is re-measured at "
            "--confirm-radius before being reported, so a tight screen over-flags and "
            "costs nothing but a little confirm work -- it can never let a real overclaim "
            "through, because culling only ever under-reports coverage. "
            "Pass 'none' or 'unbounded' for an unbounded screen: that is the exact "
            "answer, and it is also the ~8-hour path on a full artifact. It used to be "
            "the default, which meant selecting an 8-hour run by forgetting a flag. "
            "Default: %(default)s m."
        ),
    )
    ap.add_argument(
        "--workers", type=int, default=default_verify_workers(),
        help=(
            "Processes for the coverage measurements. Each building is independent, so "
            "the result is identical to serial. The audit is the LAST step before "
            "submission and ran single-core until 2026-08-09. Cost is dominated by the "
            "--exact-radius screen -- see its help before widening it. "
            "On this host: %(default)s."
        ),
    )
    ap.add_argument(
        "--taus", nargs="+", type=float, default=list(EXPECTED_TAUS),
        help=(
            "The tau values the submission must cover. Default: %(default)s. These were "
            "hardcoded until 2026-08-15, which meant a submission solved for a different "
            "published grid would FAIL its own audit at the last gate before upload. "
            "Set them from the dataset's competition-parameters.txt if it disagrees."
        ),
    )
    ap.add_argument(
        "--ks", nargs="+", type=int, default=list(EXPECTED_KS),
        help="The k values the submission must cover. Default: %(default)s.",
    )
    return ap


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    audit = Audit()
    text = Path(args.solution).read_text(encoding="utf-8")
    print(f"auditing {args.solution}\n")

    try:
        blocks = parse_blocks(text)
    except Exception as exc:  # noqa: BLE001
        print(f"  [FAIL] file does not parse into three-line blocks -- {exc}")
        return 1

    expected = subproblem_grid(args.taus, args.ks)

    print("STRUCTURE")
    audit.check(
        len(blocks) == len(expected),
        f"{len(expected)} blocks present",
        f"found {len(blocks)}",
    )
    seen = [(t, k) for t, k, *_ in blocks]
    audit.check(len(set(seen)) == len(seen), "no duplicated (tau, k) block")
    audit.check(
        set(seen) == set(expected),
        f"the {len(expected)} official (tau, k) combinations",
        f"{sorted(set(seen))}",
    )

    print("\nCOORDINATES")
    for tau, k, pts_line, _, ln in blocks:
        points = parse_points(pts_line)
        audit.check(len(points) == k, f"tau={tau} k={k}: exactly k points (counted)", f"{len(points)}")

    rounded = []
    for tau, k, pts_line, _, ln in blocks:
        for tok in re.findall(r"-?\d+\.?\d*", pts_line):
            if SIX_DECIMAL.match(tok):
                rounded.append((tau, k, tok))

    print("\nDATASET-DEPENDENT CHECKS")
    buildings, info = load_buildings(args.input)
    valid_ids = {str(b.id) for b in buildings}
    boundary_index = BoundaryIndex.from_buildings(buildings)
    blocker_index = BlockerIndex.from_buildings(buildings)
    print(f"  (dataset {info.path}, {len(buildings):,} buildings, CRS {info.crs})")

    off_boundary = 0
    for tau, k, pts_line, _, ln in blocks:
        for p in parse_points(pts_line):
            if not boundary_index.is_on_any_boundary(p, eps=args.eps):
                off_boundary += 1
    audit.check(off_boundary == 0, f"every antenna within eps={args.eps:g} of a boundary",
                f"{off_boundary} off-boundary")

    # The rounding heuristic is verdict-relevant only when the SOURCE is high precision.
    #
    # It guards one hazard: that we truncated a coordinate and moved an antenna off its
    # boundary. On the March sample, where 98% of ordinates carry 8-11 decimals, a short
    # token could only have come from us, so it was a sound proxy. The 2026-08-15
    # competition extract is stored at millimetre precision -- 89% of ordinates have
    # exactly 3 decimals -- so an antenna sitting exactly on a source vertex emits a
    # short token through no fault of ours (`%g` also strips trailing zeros). There the
    # proxy cannot separate our rounding from theirs and fires on correct output.
    #
    # `off_boundary` above measures the actual hazard exactly, at eps=1e-7, which is
    # 10,000x tighter than the official 1e-3 bar. When the source is coarse we let that
    # direct check carry the verdict and report the heuristic as a note. Leaving it as a
    # hard failure would print "AUDIT FAILED -- do not submit" on a correct submission,
    # and a real overclaim found in the same run would hide behind a failure already
    # written off. Found by the 2026-08-15 downstream dry-run, before the real artifact.
    coarse_source = sum(
        1
        for b in buildings[:2000]
        for xy in b.polygon.exterior.coords[:-1]
        for tok in (format(xy[0], ".17g"), format(xy[1], ".17g"))
        if SIX_DECIMAL.match(tok)
    )
    if coarse_source:
        audit.note(
            "six-decimal heuristic not applicable -- the SOURCE dataset is coarse "
            f"({coarse_source:,} short-form ordinates in the first 2,000 buildings); "
            f"{len(rounded):,} emitted token(s) match it. Boundary legality is the real "
            "test and is checked exactly above."
        )
    else:
        audit.check(
            not rounded,
            "no coordinate looks six-decimal rounded",
            f"{len(rounded)} suspicious" if rounded else "",
        )

    unknown = 0
    for tau, k, _, claims_line, ln in blocks:
        for cid in (c.strip() for c in claims_line.split(",") if c.strip()):
            if cid not in valid_ids:
                unknown += 1
    audit.check(unknown == 0, "every claimed ID exists in the source dataset", f"{unknown} unknown")

    print("\nCLAIM VALIDITY (exact interval coverage)")
    total_claims = 0
    total_bad = 0
    for tau, k, pts_line, claims_line, ln in blocks:
        claims = [c.strip() for c in claims_line.split(",") if c.strip()]
        total_claims += len(claims)
        if not claims:
            continue
        points = parse_points(pts_line)
        ids = [int(c) if c.isdigit() else c for c in claims]
        # Two stages. The screen radius under-reports coverage, so it flags more and
        # never fewer -- a sound screen and a useless verdict. Auditing v2 at 400 m
        # alone gave 25 false failures and zero true ones in this very block.
        bad = confirm_overclaims(
            claimed=ids,
            antenna_points=points,
            buildings=buildings,
            blocker_index=blocker_index,
            tau=tau,
            screen_radius=args.exact_radius,
            confirm_radius=args.confirm_radius,
            claim_margin=args.claim_margin,
            workers=args.workers,
        )
        total_bad += len(bad)
        worst = f", worst {min(r for _, r in bad):.4f}" if bad else ""
        audit.check(not bad, f"tau={tau} k={k}: all {len(claims)} claims hold exactly",
                    f"{len(bad)} overclaims{worst}" if bad else "")

    print("\nSUMMARY")
    print(f"  blocks       : {len(blocks)}")
    print(f"  total claims : {total_claims}")
    print(f"  overclaims   : {total_bad}")
    if audit.notes:
        print(f"  notes        : {len(audit.notes)} (do not affect the verdict)")
        for n in audit.notes:
            print(f"    - {n}")
    if audit.failures:
        print(f"\nAUDIT FAILED -- {len(audit.failures)} check(s):")
        for f in audit.failures:
            print(f"  - {f}")
        print("\nDo not submit. Never hand-edit the solution file to make this pass.")
        return 1
    print("\nAUDIT PASSED -- every checklist item verified against the file itself.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
