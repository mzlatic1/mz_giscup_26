"""Assemble the final GIS Cup submission bundle.

Official requirement (re-checked 2026-08-08 against the competition page): the
submission is a zip containing the results file and "your source code, along with
instructions for compiling and running the program". The upload link is not published
yet -- the page says it will appear closer to the competition.

Two rules drive the implementation:

1. **The results file is copied byte for byte, never parsed and rewritten.** Every
   coordinate was emitted with `format(x, ".17g")` and nudged off building interiors.
   Round-tripping through `float()`/`repr()` would move antennas off the boundaries they
   must lie on. Structural checks read a *copy* of the text; the bytes that ship are the
   bytes that were produced.

2. **Nothing from `data/` or `outputs/` ships.** The input dataset is 6.3 MB and the
   visibility matrix cache is 2.77 GB. A repo-wide zip would be unusable.
"""

from __future__ import annotations

import hashlib
import shutil
import zipfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

EXPECTED_BLOCKS = 9

#: Directories and suffixes that must never reach the bundle.
EXCLUDED_DIRS = frozenset({"data", "outputs", ".git", "__pycache__", ".pytest_cache", ".venv"})
EXCLUDED_SUFFIXES = frozenset({".bits", ".geojson", ".pyc", ".pyo", ".npy", ".memmap"})

#: What a source bundle should carry, relative to the repo root.
SOURCE_TREES = ("src", "scripts", "tests", "configs", "docs")
SOURCE_FILES = ("pyproject.toml", "README.md", "CLAUDE.md", "environment.yml", "setup.cfg")


class PackagingError(RuntimeError):
    """The solution or repository is not fit to submit."""


@dataclass(frozen=True)
class Block:
    tau: float
    k: int
    n_points: int
    n_claims: int


def _parse_header(line: str) -> tuple[float, int]:
    stripped = line.strip().lstrip("(").rstrip(")")
    parts = [p.strip() for p in stripped.split(",")]
    if len(parts) != 2:
        raise PackagingError(f"malformed (tau, k) header: {line!r}")
    try:
        return float(parts[0]), int(parts[1])
    except ValueError as exc:
        raise PackagingError(f"malformed (tau, k) header: {line!r}") from exc


def _count_points(line: str) -> int:
    text = line.strip()
    if not text:
        return 0
    return text.count("(")


def inspect_solution(text: str) -> list[Block]:
    """Structural check of a solution file. Never rewrites it.

    Verifies the three-lines-per-subproblem shape and that each block carries exactly
    `k` points -- the constraint that, if violated, invalidates the block outright.
    """
    lines = text.split("\n")
    if lines and lines[-1] == "":
        lines.pop()
    if len(lines) % 3 != 0:
        raise PackagingError(
            f"solution has {len(lines)} lines, not a multiple of 3; every subproblem "
            "needs a (tau, k) line, a coordinate line, and a claims line (which may be "
            "empty but must exist)"
        )
    blocks = []
    for i in range(0, len(lines), 3):
        tau, k = _parse_header(lines[i])
        n_points = _count_points(lines[i + 1])
        if n_points != k:
            raise PackagingError(
                f"block (tau={tau}, k={k}) expected {k} points, found {n_points}"
            )
        claims = [c for c in lines[i + 2].split(",") if c.strip()]
        blocks.append(Block(tau=tau, k=k, n_points=n_points, n_claims=len(claims)))
    if len(blocks) != EXPECTED_BLOCKS:
        raise PackagingError(
            f"expected {EXPECTED_BLOCKS} subproblem blocks, found {len(blocks)}"
        )
    return blocks


def normalize_legacy_separators(text: str) -> str:
    """Strip the blank separator lines written by `format_solution_file` before
    2026-08-08, without touching a single coordinate character.

    Only wholly-empty lines are removed, so every coordinate byte is preserved exactly.

    Refuses when any block legitimately claims nothing. In that case an empty line could
    be either that block's claims line or a separator, and there is no way to tell --
    which is precisely why the separators were removed. Re-run the solver instead.
    """
    lines = text.split("\n")
    if lines and lines[-1] == "":
        lines.pop()
    kept = [line for line in lines if line != ""]
    if len(kept) % 3 != 0:
        raise PackagingError(
            f"cannot normalise: {len(kept)} non-empty lines is not a multiple of 3"
        )
    # A separator always follows a claims line, so the count removed must equal the
    # number of gaps between blocks. Anything else means an empty claims line was eaten.
    expected_removed = len(kept) // 3 - 1
    if len(lines) - len(kept) != expected_removed:
        raise PackagingError(
            "ambiguous: this file has an empty claims line as well as blank separators, "
            "so a blank line cannot be attributed to either. Re-run the solver with the "
            "current output format instead of normalising."
        )
    return "\n".join(kept) + "\n"


def _is_excluded(path: Path, root: Path) -> bool:
    rel = path.relative_to(root)
    if any(part in EXCLUDED_DIRS for part in rel.parts):
        return True
    return path.suffix in EXCLUDED_SUFFIXES


def _iter_source(repo: Path):
    for name in SOURCE_FILES:
        candidate = repo / name
        if candidate.is_file() and not _is_excluded(candidate, repo):
            yield candidate
    for tree in SOURCE_TREES:
        base = repo / tree
        if not base.is_dir():
            continue
        for path in sorted(base.rglob("*")):
            if path.is_file() and not _is_excluded(path, repo):
                yield path


def _instructions(blocks: list[Block], solution_name: str) -> str:
    listing = "\n".join(
        f"  {i + 1}. tau={b.tau:<6g} k={b.k:<6d} {b.n_claims:,} buildings claimed"
        for i, b in enumerate(blocks)
    )
    return f"""# mz_giscup_26 — ACM SIGSPATIAL 2026 GIS Cup submission

## Contents

- `{solution_name}` — the results file, nine subproblems, three lines each.
- `source/` — full source, tests, and configuration.
- `MANIFEST.txt` — SHA-256 of every shipped file.

## Results file format

Three lines per subproblem, nine subproblems, in this order:

```
(tau, k)
(x1, y1), (x2, y2), ..., (xk, yk)
id1, id2, id3, ...
```

Coordinates are emitted with `format(x, ".17g")` and are never rounded, reprojected,
snapped, or normalised. The third line is present for every block and may be empty.

Blocks in this submission:

{listing}

## Environment

Python 3.11. Shapely 2.1.2, NumPy 2.4.6 (needs `np.bitwise_count`), SciPy 1.17.1.

```bash
conda create -n mz-giscup-26 python=3.11
conda activate mz-giscup-26
cd source
pip install -e .
```

There is nothing to compile — the solver is pure Python with compiled dependencies
installed by pip.

## Reproducing the results file

```bash
giscup solve-all \\
    --input <path-to-dataset.geojson> \\
    --taus {" ".join(str(b.tau) for b in blocks[:3])} \\
    --ks {" ".join(str(b.k) for b in blocks[::3])} \\
    --visibility-radius 400 \\
    --cache-dir outputs/cache \\
    --matrix-workers 12 \\
    --verify-band 0.10 \\
    --verify-max-buildings 2000 \\
    --output solution.txt
```

The first run builds a radius-culled visibility matrix into `--cache-dir` and reuses it
across all nine subproblems; that build dominates the runtime. Progress is printed per
subproblem with an ETA. Measured on the 12,860-building sample dataset: about 3 hours
end to end on 16 cores, needing roughly 3 GB of RAM plus ~2.8 GB of disk for the cache.

## Verifying the results file

```bash
giscup validate-output \\
    --input <path-to-dataset.geojson> \\
    --solution {solution_name} \\
    --sampling-profile accurate
```

## Notes on correctness

- Visibility is blocked only where a sight line crosses a building *interior*; tangency,
  vertex contact, and boundary-only contact do not block. Implemented as
  `line.relate_pattern(polygon.buffer(-1e-6), "T********")`.
- All geometric tolerances are absolute, in CRS units. The dataset is EPSG:32611 with
  northings around 3.7e6, where relative tolerances such as `np.isclose`'s default
  `rtol=1e-5` correspond to roughly 37 metres.
- Emitted antennas are nudged off building interiors so each lies on a boundary within
  1e-7 of the polygon boundary.
"""


def build_bundle(repo: Path, solution: Path, dest: Path, name: str | None = None) -> Path:
    """Validate, stage, and zip a submission. Returns the path to the zip.

    Raises `PackagingError` before writing anything if the solution is not fit to ship.
    """
    repo, solution, dest = Path(repo), Path(solution), Path(dest)
    if not solution.is_file():
        raise PackagingError(f"solution file not found: {solution}")

    raw = solution.read_bytes()
    blocks = inspect_solution(raw.decode("utf-8"))

    stamp = datetime.now(timezone.utc).strftime("%Y%m%d")
    bundle_name = name or f"mz_giscup_26_submission_{stamp}"
    staging = dest / bundle_name
    if staging.exists():
        shutil.rmtree(staging)
    (staging / "source").mkdir(parents=True)

    # Byte-for-byte. Never parse-and-rewrite: that would re-serialise coordinates.
    (staging / "solution.txt").write_bytes(raw)

    digests = [("solution.txt", hashlib.sha256(raw).hexdigest())]
    for path in _iter_source(repo):
        rel = path.relative_to(repo)
        target = staging / "source" / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, target)
        digests.append((f"source/{rel.as_posix()}", hashlib.sha256(path.read_bytes()).hexdigest()))

    (staging / "INSTRUCTIONS.md").write_text(
        _instructions(blocks, "solution.txt"), encoding="utf-8"
    )
    manifest = "\n".join(f"{digest}  {rel}" for rel, digest in digests)
    (staging / "MANIFEST.txt").write_text(
        f"# mz_giscup_26 submission manifest\n# generated {datetime.now(timezone.utc).isoformat()}\n"
        f"# {len(blocks)} subproblem blocks, {sum(b.k for b in blocks):,} antennas, "
        f"{sum(b.n_claims for b in blocks):,} claims\n\n{manifest}\n",
        encoding="utf-8",
    )

    zip_path = dest / f"{bundle_name}.zip"
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for path in sorted(staging.rglob("*")):
            if path.is_file():
                zf.write(path, path.relative_to(staging).as_posix())
    return zip_path
