"""Choosing between two solved solutions per subproblem, and merging the winners.

`assemble_blocks` refuses when a `(tau, k)` appears twice -- correct for crash
recovery, where overlap means ambiguity. The approved `k=9` best-of creates that
overlap deliberately: the full grid in one file, three challenger `k=9` blocks in
another, colliding on exactly the subproblems under comparison. Without a tool that
merges *chosen* winners, that step cannot execute at all.

The rules these guard are the ones that invalidate a block (CLAUDE.md): exactly k
points per subproblem, three lines per block with the third present even when empty,
and `.17g` coordinates that must survive byte for byte. Real projected magnitudes
throughout -- a unit square cannot see a formatting regression at 3.7e6.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

SCRIPT =Path(__file__).resolve().parents[1] / "scripts" / "pick_blocks.py"

TAUS = (0.32, 0.49, 0.68)
KS = (9, 49, 484)

E0 = 500_000.0
N0 = 3_700_000.0


def _block(tau: float, k: int, claims: str, *, offset: float = 0.0) -> str:
    pts = ", ".join(
        f"({format(E0 + i + offset, '.17g')}, {format(N0 + i + offset, '.17g')})"
        for i in range(k)
    )
    return f"({tau}, {k})\n{pts}\n{claims}"


def _full_grid(claims: str = "1, 2, 3") -> str:
    return "\n".join(_block(tau, k, claims) for tau in TAUS for k in KS) + "\n"


def _alt_k9(claims: str = "1, 2, 3, 4, 5") -> str:
    # Offset coordinates so a merged block is traceable to its source file.
    return "\n".join(_block(tau, 9, claims, offset=0.5) for tau in TAUS) + "\n"


def _run(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args], capture_output=True, text=True
    )


def _write_pair(tmp_path: Path) -> tuple[Path, Path]:
    base, alt = tmp_path / "final.txt", tmp_path / "k9_baseline.txt"
    base.write_text(_full_grid(), encoding="utf-8")
    alt.write_text(_alt_k9(), encoding="utf-8")
    return base, alt


def _grid_args() -> list[str]:
    return ["--taus", *(str(t) for t in TAUS), "--ks", *(str(k) for k in KS)]


def test_report_mode_writes_nothing_and_compares_claims(tmp_path):
    """The default must be inert. The comparison step should never touch a file."""
    base, alt = _write_pair(tmp_path)
    out = tmp_path / "should_not_exist.txt"

    res = _run("--base", str(base), "--alt", str(alt), *_grid_args(), "--output", str(out))

    assert res.returncode == 0, res.stderr
    assert not out.exists(), "report mode wrote a file"
    assert "Report only" in res.stdout
    # 3 base claims vs 5 alt claims on each k=9 block.
    assert "+2" in res.stdout
    # k=49 and k=484 exist only in base and must not be invented.
    assert res.stdout.count("-\n") >= 1 or "       -" in res.stdout


def test_merge_takes_named_blocks_from_alt_byte_for_byte(tmp_path):
    """The chosen block must arrive unmodified -- coordinates are never reformatted."""
    base, alt = _write_pair(tmp_path)
    out = tmp_path / "bestof.txt"

    res = _run(
        "--base", str(base), "--alt", str(alt), *_grid_args(),
        "--take-alt", "0.32,9", "0.49,9", "--output", str(out),
    )
    assert res.returncode == 0, res.stderr

    lines = out.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 27, "must be exactly nine three-line blocks"

    def points_of(tau: float, k: int, *, offset: float) -> str:
        return _block(tau, k, "", offset=offset).splitlines()[1]

    # Grid is tau-outer, k-inner: (0.32,9) is block 0, (0.49,9) block 3, (0.68,9) block 6.
    # (0.32, 9) and (0.49, 9) were taken from alt, which is offset by 0.5.
    assert lines[1] == points_of(0.32, 9, offset=0.5)
    assert lines[1] != points_of(0.32, 9, offset=0.0)
    assert lines[2] == "1, 2, 3, 4, 5"
    assert lines[10] == points_of(0.49, 9, offset=0.5)
    # (0.68, 9) was not named, so it stays with base and keeps base's claims.
    assert lines[19] == points_of(0.68, 9, offset=0.0)
    assert lines[20] == "1, 2, 3"


def test_refuses_when_alt_lacks_a_requested_block(tmp_path):
    base, alt = _write_pair(tmp_path)
    out = tmp_path / "bestof.txt"

    res = _run(
        "--base", str(base), "--alt", str(alt), *_grid_args(),
        "--take-alt", "0.32,484", "--output", str(out),
    )
    assert res.returncode != 0
    assert "does not contain" in res.stderr
    assert not out.exists(), "refused, but still wrote"


def test_refuses_a_block_whose_point_count_disagrees_with_k(tmp_path):
    """A truncated partial write looks exactly like this and must never ship."""
    base, alt = _write_pair(tmp_path)
    # Eight points under a header declaring k=9. Built directly rather than by string
    # surgery: splitting a coordinate list on ", " also splits each pair between x and
    # y, which silently leaves the "(" count -- and so `_count_points` -- at nine.
    eight_points = _block(0.32, 8, "1", offset=0.5).splitlines()[1]
    alt.write_text(f"(0.32, 9)\n{eight_points}\n1\n", encoding="utf-8")
    out = tmp_path / "bestof.txt"

    res = _run(
        "--base", str(base), "--alt", str(alt), *_grid_args(),
        "--take-alt", "0.32,9", "--output", str(out),
    )
    assert res.returncode != 0
    assert "coordinates but declares k=9" in res.stderr
    assert not out.exists()


def test_refuses_an_incomplete_base(tmp_path):
    """--base is the file the whole grid comes from; a partial one is not usable here."""
    base, alt = tmp_path / "final.txt", tmp_path / "k9.txt"
    base.write_text(
        "\n".join(_block(tau, k, "1") for tau in TAUS[:2] for k in KS) + "\n", encoding="utf-8"
    )
    alt.write_text(_alt_k9(), encoding="utf-8")

    res = _run("--base", str(base), "--alt", str(alt), *_grid_args())
    assert res.returncode != 0
    assert "not a complete grid" in res.stderr


def test_refuses_blocks_outside_the_published_grid(tmp_path):
    """The 2026-08-15 grid was not the assumed one; a stale file must not merge silently."""
    base, alt = _write_pair(tmp_path)
    stale = tmp_path / "stale.txt"
    stale.write_text(_block(0.5, 1000, "1") + "\n", encoding="utf-8")

    res = _run("--base", str(base), "--alt", str(stale), *_grid_args())
    assert res.returncode != 0
    assert "outside the given grid" in res.stderr


def test_empty_claims_line_counts_as_zero_not_one(tmp_path):
    """Filler blocks and blocks servicing nothing both have an empty third line."""
    base, alt = tmp_path / "final.txt", tmp_path / "k9.txt"
    base.write_text(_full_grid(), encoding="utf-8")
    alt.write_text(
        "\n".join(_block(tau, 9, "", offset=0.5) for tau in TAUS) + "\n", encoding="utf-8"
    )

    res = _run("--base", str(base), "--alt", str(alt), *_grid_args())
    assert res.returncode == 0, res.stderr
    assert "-3" in res.stdout, "empty claims should read as 0, i.e. 3 fewer than base"
