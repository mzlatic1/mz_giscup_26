import pytest

from giscup.models import Solution
from giscup.output import (
    format_float,
    format_solution_block,
    format_solution_file,
    parse_points,
)


def test_format_float_uses_17_significant_digits():
    assert format_float(1.0 / 3.0) == "0.33333333333333331"


def test_solution_block_has_three_lines_and_parses_points():
    solution = Solution(tau=0.5, k=2, antenna_points=[(1.0, 2.0), (3.5, 4.25)], claimed_building_ids=[1, 7])
    block = format_solution_block(solution)
    lines = block.splitlines()
    assert len(lines) == 3
    assert lines[0] == "(0.5, 2)"
    assert parse_points(lines[1]) == [(1.0, 2.0), (3.5, 4.25)]
    assert lines[2] == "1, 7"


def test_solution_block_rejects_wrong_point_count():
    solution = Solution(tau=0.5, k=2, antenna_points=[(1.0, 2.0)], claimed_building_ids=[])

    with pytest.raises(ValueError, match="has 1 antenna points"):
        format_solution_block(solution)


def test_nine_blocks_emit_exactly_27_lines_with_no_blank_separators():
    """The official spec is "three lines per sub-problem". Blank separators between
    blocks make the file 35 lines, and a parser reading three lines at a time
    misaligns on the first one.

    The separators are not merely redundant, they are ambiguous: the spec also allows
    an EMPTY third line ("may be empty but must still exist"). A block that claims
    nothing, followed by a separator, produces two consecutive blank lines that no
    parser can disambiguate. The two features cannot coexist, so the separator goes.
    """
    solutions = [
        Solution(tau=tau, k=k, antenna_points=[(1.0, 2.0)] * k, claimed_building_ids=[1, 2])
        for tau in (0.25, 0.5, 0.75)
        for k in (2, 3, 4)
    ]
    text = format_solution_file(solutions)
    lines = text.split("\n")
    assert lines[-1] == "", "file must end with a trailing newline"
    lines.pop()
    assert len(lines) == 27, f"expected 27 lines for nine blocks, got {len(lines)}"
    assert not any(line == "" for line in lines), "no blank separator lines"


def test_a_block_claiming_nothing_still_emits_its_third_line():
    """The empty claims line must survive as a real, positioned line."""
    solutions = [
        Solution(tau=0.75, k=1, antenna_points=[(1.0, 2.0)], claimed_building_ids=[]),
        Solution(tau=0.75, k=1, antenna_points=[(3.0, 4.0)], claimed_building_ids=[7]),
    ]
    lines = format_solution_file(solutions).split("\n")[:-1]
    assert len(lines) == 6
    assert lines[2] == "", "empty claims line must be present"
    assert lines[3] == "(0.75, 1)", "the next block must start immediately after it"


def test_claimed_ids_are_emitted_in_sorted_order():
    """Claim order is incidental today -- verify.py returns list(set), so the order is
    whatever the set happened to iterate. The spec imposes no order, but sorting is free
    and makes the file reproducible: the bundle ships source, so an evaluator may re-run
    and diff against ours."""
    solutions = [
        Solution(tau=0.5, k=1, antenna_points=[(1.0, 2.0)], claimed_building_ids=[9448, 7, 1200, 3])
    ]
    assert format_solution_file(solutions).split("\n")[2] == "3, 7, 1200, 9448"


def test_claimed_ids_sort_numerically_not_lexicographically():
    """Lexicographic order would put 1200 before 7, which reads as corrupted output."""
    solutions = [
        Solution(tau=0.5, k=1, antenna_points=[(1.0, 2.0)], claimed_building_ids=[7, 1200, 30])
    ]
    ids = format_solution_file(solutions).split("\n")[2].split(", ")
    assert ids == ["7", "30", "1200"]


def test_string_ids_still_sort_without_raising():
    """Building.id is typed `int | str`. A dataset with string IDs must not crash the
    emitter on a mixed or non-numeric sort."""
    solutions = [
        Solution(tau=0.5, k=1, antenna_points=[(1.0, 2.0)], claimed_building_ids=["b10", "a2"])
    ]
    assert format_solution_file(solutions).split("\n")[2] == "a2, b10"
