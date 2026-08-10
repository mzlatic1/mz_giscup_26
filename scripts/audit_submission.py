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

from giscup.audit import confirm_overclaims  # noqa: E402
from giscup.gate_model import default_verify_workers  # noqa: E402
from giscup.geometry import BoundaryIndex  # noqa: E402
from giscup.io import load_buildings  # noqa: E402
from giscup.output import parse_points  # noqa: E402
from giscup.visibility import BlockerIndex  # noqa: E402

EXPECTED_TAUS = (0.25, 0.5, 0.75)
EXPECTED_KS = (50, 500, 1000)

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
        "--exact-radius", type=float, default=None,
        help=(
            "Radius for the exact claim re-check. OMIT for unbounded, which is the true "
            "coverage and the answer that matters. Setting a radius only ever *under*-reports "
            "coverage, so it can raise false alarms on valid claims but can never let a real "
            "overclaim through -- useful as a fast pre-check, not as the final word."
        ),
    )
    ap.add_argument(
        "--workers", type=int, default=default_verify_workers(),
        help=(
            "Processes for the coverage measurements. Each building is independent, so "
            "the result is identical to serial. The audit is the LAST step before "
            "submission and ran single-core until 2026-08-09. Cost is dominated by the "
            "--exact-radius screen, which must be passed explicitly -- see its help. "
            "On this host: %(default)s."
        ),
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

    print("STRUCTURE")
    audit.check(len(blocks) == 9, "nine blocks present", f"found {len(blocks)}")
    seen = [(t, k) for t, k, *_ in blocks]
    audit.check(len(set(seen)) == len(seen), "no duplicated (tau, k) block")
    audit.check(
        set(seen) == {(t, k) for t in EXPECTED_TAUS for k in EXPECTED_KS},
        "the nine official (tau, k) combinations",
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
    audit.check(
        not rounded,
        "no coordinate looks six-decimal rounded",
        f"{len(rounded)} suspicious" if rounded else "",
    )

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
