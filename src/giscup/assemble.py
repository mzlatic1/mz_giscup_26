"""Assemble a nine-block submission from separately-solved blocks.

`solve-all` writes `<output>.partial` after every block, so a run that dies at block
7 leaves six good blocks on disk. Until now nothing could consume them: recovery
meant re-running all nine, which at measured rates is 2.85 h for baseline and ~5 h
for lever A -- time submission day does not have.

This stopped being hypothetical on 2026-08-09, when the lever A run was killed at
block 6 of 9 and its evidence ended up split across two files.

The tool is deliberately dumb about geometry and strict about structure. It moves
block text between files verbatim -- **coordinates are never reparsed or
reformatted**, because `format(x, ".17g")` output must survive byte for byte -- and
refuses anything that would produce an invalid submission:

* a duplicated `(tau, k)`, which would otherwise pick a winner arbitrarily between
  two different solutions for the same subproblem;
* a missing `(tau, k)`, which scores ~0 on that subproblem;
* a block whose coordinate count does not equal its own `k`, which is the one
  constraint that invalidates a block outright, and exactly what a truncated partial
  write would produce.

Validating structure is all this can do. It cannot tell you the blocks are *good* --
run `scripts/audit_submission.py` on the assembled file for that.
"""

from __future__ import annotations

from typing import NamedTuple, Sequence

#: The nine subproblems, tau-outer and k-inner, which is also the emission order.
REQUIRED_SUBPROBLEMS: tuple[tuple[float, int], ...] = tuple(
    (tau, k) for tau in (0.25, 0.5, 0.75) for k in (50, 500, 1000)
)


class Block(NamedTuple):
    """One subproblem, as text. `points` and `claims` are never interpreted."""

    tau: float
    k: int
    points: str
    claims: str


def _format_key(tau: float, k: int) -> str:
    return f"({tau:g}, {k})"


def parse_blocks(text: str) -> list[Block]:
    """Three-line blocks, tolerating blank lines between them.

    Builds before 2026-08-08 emitted blank separators (35 lines for nine blocks
    rather than 27). A recovery tool that choked on a legacy partial would be useless
    at exactly the moment it is needed, so separators are skipped on input and never
    reproduced on output.

    A blank *claims* line is content, not a separator -- a block may legitimately
    claim nothing. That is why lines are consumed in threes after a header rather
    than by filtering blanks globally, which would silently shift every later block.

    **Split on newlines, not with `splitlines()`.** `"...\\npts\\n".splitlines()` yields
    two elements, not three: the trailing empty string is dropped. So a *final* block
    that claims nothing -- legal, and the reason the third line is allowed to be empty
    -- would parse as truncated and be rejected. Splitting explicitly keeps it.

    `scripts/audit_submission.py` carries its own variant of this parser that also
    tracks line numbers for its diagnostics; keep the two in step.
    """
    lines = text.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    blocks: list[Block] = []
    i = 0
    while i < len(lines):
        while i < len(lines) and not lines[i].strip():
            i += 1
        if i >= len(lines):
            break
        header = lines[i].strip()
        if not (header.startswith("(") and header.endswith(")")):
            raise ValueError(f"line {i + 1}: expected a (tau, k) header, got {header!r}")
        try:
            tau_s, k_s = header.strip("()").split(",")
            tau, k = float(tau_s), int(k_s)
        except ValueError as exc:
            raise ValueError(f"line {i + 1}: cannot read a (tau, k) header from {header!r}") from exc
        if i + 2 >= len(lines):
            raise ValueError(
                f"line {i + 1}: block {header} is incomplete -- a block is three lines, "
                f"and the third may be empty but must exist"
            )
        blocks.append(Block(tau, k, lines[i + 1].strip(), lines[i + 2].strip()))
        i += 3
    return blocks


def _count_points(points: str) -> int:
    """Coordinates in a points line, without parsing the numbers.

    Counting `(` is enough and avoids touching the digits. `parse_points` would give
    the same answer, but round-tripping through float and back is precisely the thing
    this module refuses to do.
    """
    return points.count("(")


def assemble_blocks(
    texts: Sequence[str],
    required: Sequence[tuple[float, int]] | None = None,
) -> str:
    """One valid solution file from several partial ones.

    `required` exists for tests and for a hypothetical rule change; on submission day
    it is the nine published subproblems and should be left alone.
    """
    wanted = tuple(required) if required is not None else REQUIRED_SUBPROBLEMS

    found: dict[tuple[float, int], Block] = {}
    for source, text in enumerate(texts):
        for block in parse_blocks(text):
            key = (block.tau, block.k)
            if key in found:
                raise ValueError(
                    f"subproblem {_format_key(*key)} appears more than once (again in "
                    f"input {source}). Two solutions for one subproblem means picking "
                    f"a winner arbitrarily, so nothing is assembled. Drop the "
                    f"overlapping input and re-run."
                )
            expected = _count_points(block.points)
            if expected != block.k:
                raise ValueError(
                    f"subproblem {_format_key(*key)} has {expected} coordinates but "
                    f"declares k={block.k}. A block must contain exactly k antenna "
                    f"points -- this one is unusable, and a truncated partial write "
                    f"looks exactly like this."
                )
            found[key] = block

    missing = [key for key in wanted if key not in found]
    if missing:
        listed = ", ".join(_format_key(*key) for key in missing)
        raise ValueError(
            f"missing {len(missing)} of {len(wanted)} subproblems: {listed}. An absent "
            f"block scores ~0 on that subproblem and there is one submission with no "
            f"feedback, so nothing is assembled. Solve the missing blocks and re-run."
        )
    extra = [key for key in found if key not in wanted]
    if extra:
        listed = ", ".join(_format_key(*key) for key in extra)
        raise ValueError(f"unexpected subproblems not in the published set: {listed}")

    # Trailing newline to match `format_solution_file` exactly: a recovered submission
    # should be byte-indistinguishable from a solved one. Omitting it survived the
    # first version of the identity test, which compared `splitlines()`.
    return "\n".join(
        f"{_format_key(*key)}\n{found[key].points}\n{found[key].claims}" for key in wanted
    ) + "\n"
