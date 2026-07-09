from giscup.models import Solution
from giscup.output import format_float, format_solution_block, parse_points


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
