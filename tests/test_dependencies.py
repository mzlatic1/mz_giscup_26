"""Declared dependencies must match what the code actually needs.

These are submission tests, not hygiene tests. The bundle ships source plus install
instructions, and it gets installed on a machine we will never see, resolving versions
we do not control. A wrong floor or a superfluous package is a failed evaluation, and
there is no second attempt.

Found by the 2026-08-08 packaging dry run: a clean venv resolved numpy 2.5.1 while the
dev environment had 2.4.6, which is what prompted checking the floor at all.
"""

from __future__ import annotations

import re
import tomllib
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]

#: Needed at runtime but not imported by name anywhere in our source.
INDIRECT = {"pyogrio"}  # geopandas' default IO engine


def _declared() -> dict[str, str]:
    data = tomllib.loads((REPO / "pyproject.toml").read_text(encoding="utf-8"))
    out = {}
    for spec in data["project"]["dependencies"]:
        match = re.match(r"^([A-Za-z0-9_.\-]+)\s*(.*)$", spec)
        out[match.group(1).lower()] = match.group(2)
    return out


def _imported() -> set[str]:
    names = set()
    pattern = re.compile(r"^\s*(?:import|from)\s+([A-Za-z0-9_]+)", re.MULTILINE)
    for folder in ("src", "scripts"):
        for path in (REPO / folder).rglob("*.py"):
            names |= set(pattern.findall(path.read_text(encoding="utf-8")))
    return names


def test_numpy_floor_covers_bitwise_count():
    """`np.bitwise_count` is used in the matrix hot path and was added in NumPy 2.0.
    Declaring `numpy>=1.26` lets a resolver pick a version that AttributeErrors deep
    inside the solver, after the expensive setup has already run."""
    sources = list((REPO / "src").rglob("*.py"))
    assert any("bitwise_count" in p.read_text(encoding="utf-8") for p in sources)

    spec = _declared()["numpy"]
    floor = re.search(r">=\s*(\d+)", spec)
    assert floor, f"numpy needs a lower bound, got {spec!r}"
    assert int(floor.group(1)) >= 2, (
        f"numpy floor is {spec!r} but np.bitwise_count needs >=2.0"
    )


def test_the_same_numpy_floor_is_declared_everywhere():
    """Three files declare dependencies. An evaluator may follow any of them."""
    floors = {}
    for name in ("pyproject.toml", "requirements.txt", "environment.yml"):
        path = REPO / name
        if not path.exists():
            continue
        found = re.search(r"numpy\s*>=\s*([0-9.]+)", path.read_text(encoding="utf-8"))
        assert found, f"{name} does not pin a numpy floor"
        floors[name] = found.group(1)
    assert len(set(floors.values())) == 1, f"numpy floors disagree: {floors}"


def test_every_declared_dependency_is_actually_used():
    """Each unused package is install surface that can fail on the evaluator's machine
    while buying nothing. The dry run found four."""
    unused = set(_declared()) - _imported() - INDIRECT
    assert not unused, f"declared but never imported: {sorted(unused)}"


def test_every_imported_third_party_package_is_declared():
    stdlib_or_local = {
        "giscup", "__future__", "argparse", "json", "os", "sys", "math", "time",
        "pathlib", "dataclasses", "typing", "collections", "itertools", "functools",
        "hashlib", "shutil", "zipfile", "datetime", "re", "random", "multiprocessing",
        "concurrent", "contextlib", "tempfile", "warnings", "csv", "statistics",
        "textwrap", "subprocess", "enum", "abc", "copy", "traceback", "io", "numbers",
        "tomllib", "unittest", "pytest",
    }
    missing = _imported() - stdlib_or_local - set(_declared())
    assert not missing, f"imported but not declared: {sorted(missing)}"
