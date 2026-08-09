"""Assembling a nine-block submission out of separately-solved blocks.

The runbook promises "partial output is written after every block -- if the run dies
at block 7, you still have six blocks". That was true and useless: nothing could
consume those six blocks, so recovery meant re-running all nine.

It stopped being hypothetical on 2026-08-09. The lever A run was killed at block 6 of
9, and the evidence for #17 ended up split across two files that had to be compared by
ad-hoc script. Combining them into a submission would have meant hand-editing the
file that decides the competition -- exactly the clerical risk the runbook exists to
remove.

Every check here maps to a rule that invalidates a submission block if broken. See
CLAUDE.md: exactly k points per subproblem, three lines per block, third line may be
empty but must exist.
"""

from __future__ import annotations

import pytest

from giscup.assemble import assemble_blocks, parse_blocks

# One block, k=2, two coordinates. Real projected magnitudes so nothing here can pass
# by accident on unit-square coordinates.
E0 = 500_000.0
N0 = 3_700_000.0


def _block(tau: float, k: int, claims: str = "1, 2") -> str:
    pts = ", ".join(
        f"({E0 + i:.17g}, {N0 + i:.17g})" for i in range(k)
    )
    return f"({tau}, {k})\n{pts}\n{claims}"


def _nine() -> list[str]:
    return [_block(tau, k) for tau in (0.25, 0.5, 0.75) for k in (50, 500, 1000)]


def test_two_fragments_become_one_nine_block_file():
    """The situation that motivated this: five blocks in one file, four in another."""
    first = "\n".join(_nine()[:5])
    rest = "\n".join(_nine()[5:])
    out = assemble_blocks([first, rest])
    assert len(out.splitlines()) == 27


def test_blocks_come_out_in_tau_outer_k_inner_order_regardless_of_input_order():
    """Order is how a reader keys blocks to subproblems. Assembling fragments in the
    order they happened to finish must not reorder the submission."""
    shuffled = [_block(0.75, 1000), _block(0.25, 500), _block(0.5, 50)]
    shuffled += [
        _block(t, k) for t in (0.25, 0.5, 0.75) for k in (50, 500, 1000)
        if (t, k) not in {(0.75, 1000), (0.25, 500), (0.5, 50)}
    ]
    out = assemble_blocks(["\n".join(shuffled)])
    headers = out.splitlines()[::3]
    assert headers == [
        "(0.25, 50)", "(0.25, 500)", "(0.25, 1000)",
        "(0.5, 50)", "(0.5, 500)", "(0.5, 1000)",
        "(0.75, 50)", "(0.75, 500)", "(0.75, 1000)",
    ]


def test_a_duplicated_subproblem_is_refused_and_named():
    """Two files each containing (0.5, 500) is the likeliest recovery mistake: a
    re-run that overlapped what the partial already had. Silently keeping one would
    pick a winner arbitrarily between two different solutions."""
    with pytest.raises(ValueError) as excinfo:
        assemble_blocks(["\n".join(_nine()), _block(0.5, 500)])
    assert "0.5" in str(excinfo.value) and "500" in str(excinfo.value)


def test_a_missing_subproblem_is_refused_and_named():
    """A file with eight blocks scores ~0 on the ninth. Refusing loudly is the only
    safe behaviour -- there is one submission and no feedback."""
    with pytest.raises(ValueError) as excinfo:
        assemble_blocks(["\n".join(_nine()[:-1])])
    message = str(excinfo.value)
    assert "0.75" in message and "1000" in message


def test_a_block_with_the_wrong_number_of_points_is_refused():
    """THE competition constraint: exactly k, not fewer, not more. A truncated
    partial write is precisely how a short block would reach this function."""
    short = f"({0.25}, {50})\n({E0}, {N0})\n1, 2"
    others = "\n".join(b for b in _nine() if not b.startswith("(0.25, 50)"))
    with pytest.raises(ValueError) as excinfo:
        assemble_blocks([short, others])
    assert "50" in str(excinfo.value)


def test_an_empty_claims_line_is_preserved_not_dropped():
    """The third line may be empty but must exist. A block claiming nothing is legal
    -- and if the line vanished, every subsequent block would shift by one."""
    empty = _block(0.25, 50, claims="")
    others = "\n".join(b for b in _nine() if not b.startswith("(0.25, 50)"))
    out = assemble_blocks([empty, others])
    lines = out.splitlines()
    assert len(lines) == 27
    assert lines[2] == ""


def test_assembling_a_complete_file_returns_it_byte_for_byte():
    """The identity case. If this ever alters a valid file, the tool is a liability
    rather than a recovery path.

    Compared as bytes, not by `splitlines()`. The first version of this test used
    `splitlines()` and passed while the assembler dropped the trailing newline --
    caught only by round-tripping a real nine-block file on disk. A comparison that
    normalises away the thing under test proves nothing.
    """
    complete = "\n".join(_nine()) + "\n"
    assert assemble_blocks([complete]) == complete


def test_the_assembled_file_matches_what_the_solver_itself_writes():
    """`format_solution_file` terminates with a newline, so an assembled file must
    too -- a recovered submission should be indistinguishable from a solved one."""
    from giscup.models import Solution
    from giscup.output import format_solution_file

    written = format_solution_file([
        Solution(tau=0.25, k=1, antenna_points=[(E0, N0)], claimed_building_ids=[1],
                 diagnostics={}),
    ])
    assert assemble_blocks([written], required=((0.25, 1),)) == written


def test_coordinates_pass_through_verbatim():
    """CLAUDE.md: never round, never reproject, never normalize. The assembler moves
    text between files and must not reformat a single digit."""
    exact = "(500000.12345678901, 3700000.9876543211)"
    one = f"(0.25, 1)\n{exact}\n7"
    out = assemble_blocks([one], required=((0.25, 1),))
    assert exact in out


def test_blank_separator_lines_in_input_are_tolerated():
    """Older builds emitted blank separators between blocks (35 lines, not 27). A
    recovery tool that choked on a legacy partial would be useless exactly when
    needed."""
    legacy = "\n\n".join(_nine())
    assert len(assemble_blocks([legacy]).splitlines()) == 27


def test_parse_blocks_reads_what_format_solution_file_writes():
    """Guards the round trip against a format change on either side."""
    from giscup.models import Solution
    from giscup.output import format_solution_file

    solutions = [
        Solution(tau=0.25, k=2, antenna_points=[(E0, N0), (E0 + 1, N0 + 1)],
                 claimed_building_ids=[3, 1], diagnostics={}),
    ]
    parsed = parse_blocks(format_solution_file(solutions))
    assert len(parsed) == 1
    assert parsed[0].tau == 0.25 and parsed[0].k == 2
