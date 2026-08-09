"""Submission bundle assembly.

The official page (re-checked 2026-08-08) says the submission is a zip containing:

  1. the results file -- three lines per subproblem, nine subproblems;
  2. "your source code, along with instructions for compiling and running the program".

The submission link itself is not published yet ("The webpage will be updated closer to
the competition time to include a link to submit"), so this covers everything up to the
upload.

The dangerous failure mode here is silent, not loud: a packaging step that *parses and
rewrites* the results file would re-serialise every coordinate through repr() and move
antennas off the boundaries they were carefully nudged onto. The results file must be
copied byte for byte, and `test_results_file_is_copied_byte_for_byte` proves it.

The second failure mode is size: `data/` is 6.3 MB and `outputs/cache` holds a 2.77 GB
visibility matrix. A naive "zip the repo" would produce an unusable bundle.
"""

from __future__ import annotations

import zipfile

import pytest

from giscup.packaging import PackagingError, build_bundle

# A minimal but structurally valid nine-block solution. Coordinates are deliberately
# full-precision and awkward -- if anything re-serialises them, the bytes change.
TAUS = (0.25, 0.5, 0.75)
KS = (2, 3, 4)


def _solution_text() -> str:
    lines = []
    for tau in TAUS:
        for k in KS:
            pts = ", ".join(
                f"({format(500123.45678901234 + i, '.17g')}, "
                f"{format(3712345.6789012345 + i, '.17g')})"
                for i in range(k)
            )
            lines.append(f"({tau}, {k})")
            lines.append(pts)
            lines.append("1, 2, 3")
    return "\n".join(lines) + "\n"


@pytest.fixture
def solution(tmp_path):
    path = tmp_path / "nine.txt"
    path.write_text(_solution_text(), encoding="utf-8")
    return path


@pytest.fixture
def repo(tmp_path):
    """A stand-in source tree with the things that must and must not be included."""
    root = tmp_path / "repo"
    (root / "src" / "giscup").mkdir(parents=True)
    (root / "src" / "giscup" / "solver.py").write_text("# solver\n", encoding="utf-8")
    (root / "src" / "giscup" / "__pycache__").mkdir()
    (root / "src" / "giscup" / "__pycache__" / "solver.pyc").write_bytes(b"\x00compiled")
    (root / "scripts").mkdir()
    (root / "scripts" / "build_matrix.py").write_text("# build\n", encoding="utf-8")
    (root / "pyproject.toml").write_text("[project]\nname='mz-giscup-26'\n", encoding="utf-8")
    # Must NOT be shipped: source data, derived output, the 2.77 GB matrix, git internals.
    (root / "data").mkdir()
    (root / "data" / "GIS-cup-sample-dataset.geojson").write_text("{}", encoding="utf-8")
    (root / "outputs" / "cache").mkdir(parents=True)
    (root / "outputs" / "cache" / "big.bits").write_bytes(b"\x00" * 4096)
    (root / ".git").mkdir()
    (root / ".git" / "config").write_text("[core]\n", encoding="utf-8")
    return root


def _names(zip_path):
    with zipfile.ZipFile(zip_path) as zf:
        return set(zf.namelist())


# --- the precision guarantee ------------------------------------------------


def test_results_file_is_copied_byte_for_byte(repo, solution, tmp_path):
    """The single most important property. Re-serialising coordinates would move
    antennas off building boundaries and invalidate every block."""
    zip_path = build_bundle(repo=repo, solution=solution, dest=tmp_path / "out")
    original = solution.read_bytes()
    with zipfile.ZipFile(zip_path) as zf:
        name = next(n for n in zf.namelist() if n.endswith("solution.txt"))
        assert zf.read(name) == original


# --- structural refusal -----------------------------------------------------


def test_it_refuses_a_solution_without_nine_blocks(repo, tmp_path):
    short = tmp_path / "short.txt"
    short.write_text("(0.25, 2)\n(1.0, 2.0), (3.0, 4.0)\n1, 2\n", encoding="utf-8")
    with pytest.raises(PackagingError, match="9 subproblem"):
        build_bundle(repo=repo, solution=short, dest=tmp_path / "out")


def test_it_refuses_a_solution_whose_point_count_does_not_match_k(repo, tmp_path):
    """Exactly k points is scored. Packaging is the last gate before submission."""
    text = _solution_text().split("\n")
    text[1] = "(1.0, 2.0)"  # first block should have k=2 points, now has 1
    bad = tmp_path / "bad.txt"
    bad.write_text("\n".join(text), encoding="utf-8")
    with pytest.raises(PackagingError, match="expected 2 points"):
        build_bundle(repo=repo, solution=bad, dest=tmp_path / "out")


def test_it_refuses_a_missing_third_line(repo, tmp_path):
    """The claims line may be empty but must exist."""
    lines = _solution_text().split("\n")
    del lines[2]
    bad = tmp_path / "bad.txt"
    bad.write_text("\n".join(lines), encoding="utf-8")
    with pytest.raises(PackagingError):
        build_bundle(repo=repo, solution=bad, dest=tmp_path / "out")


def test_an_empty_claims_line_is_accepted(repo, tmp_path):
    """Claiming nothing is legal; the line must merely be present."""
    lines = []
    for tau in TAUS:
        for k in KS:
            lines += [f"({tau}, {k})", ", ".join("(1.0, 2.0)" for _ in range(k)), ""]
    ok = tmp_path / "ok.txt"
    ok.write_text("\n".join(lines) + "\n", encoding="utf-8")
    assert build_bundle(repo=repo, solution=ok, dest=tmp_path / "out").exists()


# --- bundle contents --------------------------------------------------------


def test_bundle_contains_source_and_instructions(repo, solution, tmp_path):
    names = _names(build_bundle(repo=repo, solution=solution, dest=tmp_path / "out"))
    assert any(n.endswith("src/giscup/solver.py") for n in names)
    assert any(n.endswith("scripts/build_matrix.py") for n in names)
    assert any(n.endswith("pyproject.toml") for n in names)
    assert any("INSTRUCTIONS" in n for n in names)


def test_instructions_tell_the_evaluator_how_to_run_it(repo, solution, tmp_path):
    zip_path = build_bundle(repo=repo, solution=solution, dest=tmp_path / "out")
    with zipfile.ZipFile(zip_path) as zf:
        name = next(n for n in zf.namelist() if "INSTRUCTIONS" in n)
        text = zf.read(name).decode("utf-8")
    assert "solve-all" in text
    assert "pip install" in text or "conda" in text
    assert "python" in text.lower()


def test_bundle_excludes_data_outputs_caches_and_git(repo, solution, tmp_path):
    """A naive repo zip would carry a 2.77 GB visibility matrix and the input dataset."""
    names = _names(build_bundle(repo=repo, solution=solution, dest=tmp_path / "out"))
    for forbidden in ("data/", "outputs/", ".git/", "__pycache__", ".bits", ".geojson"):
        assert not any(forbidden in n for n in names), f"{forbidden} leaked into the bundle"


def test_bundle_is_small_enough_to_upload(repo, solution, tmp_path):
    zip_path = build_bundle(repo=repo, solution=solution, dest=tmp_path / "out")
    assert zip_path.stat().st_size < 5 * 1024 * 1024


def test_manifest_records_a_checksum_of_the_results_file(repo, solution, tmp_path):
    """So a corrupted upload is detectable after the fact."""
    import hashlib

    zip_path = build_bundle(repo=repo, solution=solution, dest=tmp_path / "out")
    expected = hashlib.sha256(solution.read_bytes()).hexdigest()
    with zipfile.ZipFile(zip_path) as zf:
        name = next(n for n in zf.namelist() if "MANIFEST" in n)
        assert expected in zf.read(name).decode("utf-8")


def test_the_zip_is_readable_and_uncorrupted(repo, solution, tmp_path):
    zip_path = build_bundle(repo=repo, solution=solution, dest=tmp_path / "out")
    with zipfile.ZipFile(zip_path) as zf:
        assert zf.testzip() is None


# --- legacy files written before the separator fix --------------------------


def test_legacy_separators_are_rejected_with_a_useful_message(repo, tmp_path):
    """Files written before 2026-08-08 join blocks with a blank line, making them 35
    lines. That form misaligns a three-lines-at-a-time parser, so it must not ship."""
    legacy = tmp_path / "legacy.txt"
    legacy.write_text(_solution_text().replace("\n(0.", "\n\n(0."), encoding="utf-8")
    with pytest.raises(PackagingError, match="multiple of 3"):
        build_bundle(repo=repo, solution=legacy, dest=tmp_path / "out")


def test_legacy_normalisation_strips_separators_without_touching_coordinates():
    from giscup.packaging import normalize_legacy_separators

    original = _solution_text()
    legacy = original.replace("\n(0.", "\n\n(0.")
    assert normalize_legacy_separators(legacy) == original


def test_legacy_normalisation_refuses_when_a_block_claims_nothing():
    """If any block has an empty claims line, an empty line is genuinely ambiguous --
    it could be that claims line or a separator. Refuse rather than guess."""
    from giscup.packaging import normalize_legacy_separators

    lines = []
    for tau in TAUS:
        for k in KS:
            lines += [f"({tau}, {k})", ", ".join("(1.0, 2.0)" for _ in range(k)), ""]
    legacy = "\n\n".join("\n".join(lines[i : i + 3]) for i in range(0, len(lines), 3)) + "\n"
    with pytest.raises(PackagingError, match="ambiguous"):
        normalize_legacy_separators(legacy)
