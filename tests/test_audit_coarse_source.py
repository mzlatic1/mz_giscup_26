"""The six-decimal heuristic must not fail a correct submission on a coarse dataset.

`audit_submission.py` flags any emitted ordinate matching `^-?\\d+\\.\\d{1,6}$` on the
theory that we rounded it. That was sound on the March sample, where ~98% of source
ordinates carry 8-11 decimals: a short token could only have come from us.

The competition extract published 2026-08-15 is stored at **millimetre precision** --
89% of ordinates have exactly 3 decimals. An antenna sitting exactly on a source vertex
therefore emits a short token through no fault of ours, and `%g` strips trailing zeros
on top of that. The heuristic fired on 591 tokens of a provably legal solution and
exited 1.

That matters more than a cosmetic false alarm. The audit is the last gate before upload,
and a spurious "AUDIT FAILED -- do not submit" is one a tired operator learns to wave
through -- at which point a *real* overclaim discovered in the same run is hidden behind
a failure already written off.

The hazard the heuristic proxies for -- a truncated coordinate leaving its boundary --
is measured exactly by the `is_on_any_boundary(p, eps=1e-7)` check, 10,000x tighter than
the official 1e-3 bar. So: keep the heuristic as a hard failure where it discriminates
(high-precision source), and demote it to a note where it cannot (coarse source).

Found by the 2026-08-15 downstream dry-run, before the real artifact existed.
"""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

# Real projected magnitudes; a unit square cannot exercise any of this.
E0 = 500_000.0
N0 = 3_700_000.0


def _load_script(name: str):
    root = Path(__file__).resolve().parents[1]
    spec = importlib.util.spec_from_file_location(name, root / "scripts" / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _square(bid: int, x: float, y: float, size: float):
    """One axis-aligned square at whatever precision the caller's offsets carry."""
    ring = [
        (x, y), (x + size, y), (x + size, y + size), (x, y + size), (x, y),
    ]
    return {
        "type": "Feature",
        "properties": {"id": bid},
        "geometry": {"type": "Polygon", "coordinates": [[list(p) for p in ring]]},
    }


# Whether a coarse decimal survives `.17g` as a short token depends on the exact double:
# 460012.87 formats to "460012.87" but 500000.123 formats to "500000.12300000002". Only
# exactly-representable binary fractions are guaranteed short, so the coarse fixture uses
# those -- it must reproduce the competition dataset's *observable* property (short
# emitted tokens), not merely look coarse in the file.
COARSE = (0.25, 0.5)
PRECISE = (0.123456789, 0.987654321)


def _dataset(path: Path, ndigits: int | None) -> Path:
    """Two well-separated squares. `ndigits=3` stands in for the coarse extract."""
    dx, dy = COARSE if ndigits is not None else PRECISE
    feats = [
        _square(1, E0 + dx, N0 + dy, 20.0),
        _square(2, E0 + 300 + dx, N0 + 300 + dy, 20.0),
    ]
    path.write_text(json.dumps({
        "type": "FeatureCollection",
        "crs": {"type": "name", "properties": {"name": "urn:ogc:def:crs:EPSG::32611"}},
        "features": feats,
    }))
    return path


def _solution(path: Path, dataset: Path, k: int) -> Path:
    """Exactly k antennas taken verbatim from source vertices, claiming nothing.

    Vertices are on the boundary by construction, so this is legal by the exact check
    no matter what precision the source carries -- which is the whole point.
    """
    data = json.loads(dataset.read_text())
    verts = [tuple(p) for f in data["features"] for p in f["geometry"]["coordinates"][0][:-1]]
    pts = ", ".join(f"({format(x, '.17g')}, {format(y, '.17g')})" for x, y in verts[:k])
    path.write_text(f"(0.32, {k})\n{pts}\n\n")
    return path


def _run(tmp_path: Path, ndigits: int | None, k: int = 4):
    audit = _load_script("audit_submission")
    ds = _dataset(tmp_path / f"ds_{ndigits}.geojson", ndigits)
    sol = _solution(tmp_path / f"sol_{ndigits}.txt", ds, k)
    rc = audit.main([
        "--input", str(ds), "--solution", str(sol),
        "--taus", "0.32", "--ks", str(k),
        "--exact-radius", "400", "--confirm-radius", "800", "--workers", "1",
    ])
    return rc


def test_a_coarse_source_does_not_fail_a_legal_submission(tmp_path, capsys):
    """The 2026-08-15 case: millimetre-precision source, antennas on real vertices."""
    rc = _run(tmp_path, ndigits=3)
    out = capsys.readouterr().out

    assert rc == 0, "a legal submission must not be failed by the rounding heuristic"
    assert "[NOTE] six-decimal heuristic not applicable" in out
    assert "0 off-boundary" in out, "the exact check must still be the one carrying the verdict"
    assert "do not affect the verdict" in out


def test_a_high_precision_source_keeps_the_heuristic_as_a_hard_failure(tmp_path, capsys):
    """The guard must survive where it still discriminates.

    With a full-precision source, a short ordinate can only mean we truncated it, so
    this must remain a FAIL and exit 1 -- exactly the March behaviour.
    """
    audit = _load_script("audit_submission")
    ds = _dataset(tmp_path / "precise.geojson", ndigits=None)
    # Emit deliberately rounded coordinates: the mistake the heuristic exists to catch.
    data = json.loads(ds.read_text())
    verts = [tuple(p) for f in data["features"] for p in f["geometry"]["coordinates"][0][:-1]]
    pts = ", ".join(f"({x:.6f}, {y:.6f})" for x, y in verts[:4])
    sol = tmp_path / "rounded.txt"
    sol.write_text(f"(0.32, 4)\n{pts}\n\n")

    rc = audit.main([
        "--input", str(ds), "--solution", str(sol),
        "--taus", "0.32", "--ks", "4",
        "--exact-radius", "400", "--confirm-radius", "800", "--workers", "1",
    ])
    out = capsys.readouterr().out

    assert rc == 1
    assert "no coordinate looks six-decimal rounded" in out
    assert "[NOTE] six-decimal heuristic not applicable" not in out


def test_the_note_never_masks_a_real_overclaim(tmp_path, capsys):
    """Demoting the heuristic must not weaken overclaim detection on a coarse dataset.

    The negative control from the dry-run: on the real 50,000-building extract the same
    change still caught all 45 bogus claims.

    tau is 0.99 deliberately. Building 2 sits 300 m away with nothing between them, so
    its near faces *are* visible and a modest tau genuinely holds -- an earlier draft of
    this test asserted a failure that never came. Only near-total perimeter coverage is
    unreachable from four antennas on one side.
    """
    audit = _load_script("audit_submission")
    ds = _dataset(tmp_path / "coarse.geojson", ndigits=3)
    data = json.loads(ds.read_text())
    verts = [tuple(p) for f in data["features"] for p in f["geometry"]["coordinates"][0][:-1]]
    pts = ", ".join(f"({format(x, '.17g')}, {format(y, '.17g')})" for x, y in verts[:4])
    sol = tmp_path / "overclaim.txt"
    sol.write_text(f"(0.99, 4)\n{pts}\n2\n")

    rc = audit.main([
        "--input", str(ds), "--solution", str(sol),
        "--taus", "0.99", "--ks", "4",
        "--exact-radius", "400", "--confirm-radius", "800", "--workers", "1",
    ])
    out = capsys.readouterr().out

    assert rc == 1, "an overclaim must still fail on a coarse dataset"
    assert "[NOTE] six-decimal heuristic not applicable" in out
    assert "overclaims   : 1" in out
