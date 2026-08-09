"""Progress reporting for long solver runs.

A nine-block run takes ~3 h and used to print nothing until it finished, so a healthy
run and a wedged one looked identical. With one submission attempt and no score
feedback, "is it still working?" must be answerable from the terminal.

Remaining time is estimated from *antennas placed*, not from subproblems finished.
Measured on the official dataset (2026-08-08, nine blocks, 164 min total), runtime is
proportional to `k` at ~2.16 s per antenna with a -24 s intercept -- there is no
meaningful fixed cost per subproblem. Counting subproblems instead would, after the
first k=50 block, promise the remaining 163 minutes in 11.
"""

from __future__ import annotations

import sys
import time
from typing import IO, Sequence


def remaining_seconds(elapsed: float, work_done: float, work_total: float) -> float | None:
    """Seconds left, extrapolating from the observed rate of completed work.

    `work` is measured in antennas (sum of `k`), not subproblems. Returns None when no
    work has completed, because there is then no rate to extrapolate and inventing a
    number is worse than admitting ignorance.
    """
    if work_done <= 0:
        return None
    rate = elapsed / work_done
    return max(0.0, rate * (work_total - work_done))


def greedy_report_interval(k: int) -> int:
    """How many greedy picks to complete between progress lines.

    One pick costs roughly 1 s (measured: the k=500 greedy phase ran 8.3 min), and the
    competition k values are 50 / 500 / 1000. The trade-off is log noise across a 3 h
    nine-block run against how long a stall can hide before you notice it.

    Target ~20 lines per subproblem, capped at 50 picks (~50 s of silence) so a stall is
    caught quickly at large k, and floored at 1 because this is used as a modulus.
    Count-based rather than time-based: the output stays deterministic, which matters
    when diffing two runs' logs to find where they diverged.
    """
    return max(1, min(50, k // 20))


def _minutes(seconds: float | None) -> str:
    return "  ?  " if seconds is None else f"{seconds / 60:5.1f}"


class ProgressReporter:
    """Prints one line per subproblem boundary, plus phase lines inside a subproblem.

    Every write is flushed: background runs are redirected to a file, and block
    buffering would withhold every line until exit -- the exact failure being fixed.
    """

    def __init__(
        self,
        plan: Sequence[tuple[float, int]],
        stream: IO[str] | None = None,
        enabled: bool = True,
    ) -> None:
        if not plan:
            raise ValueError("plan must contain at least one (tau, k) subproblem")
        self.plan = list(plan)
        self.stream = stream if stream is not None else sys.stdout
        self.enabled = enabled
        self.work_total = sum(k for _, k in self.plan)
        self.work_done = 0
        self.index = 0
        self._start = time.perf_counter()
        self._subproblem_start = self._start
        self._current_k = 0

    # -- internals ----------------------------------------------------------

    def _write(self, text: str) -> None:
        if not self.enabled:
            return
        self.stream.write(text + "\n")
        self.stream.flush()

    @property
    def elapsed(self) -> float:
        return time.perf_counter() - self._start

    # -- reporting ----------------------------------------------------------

    def start_subproblem(self, tau: float, k: int) -> None:
        self.index += 1
        self._current_k = k
        self._subproblem_start = time.perf_counter()
        eta = remaining_seconds(self.elapsed, self.work_done, self.work_total)
        tail = "" if eta is None else f"   eta {_minutes(eta)} min"
        self._write(
            f"[{self.index}/{len(self.plan)}] tau={tau:<5g} k={k:<5d} start"
            f"   elapsed {_minutes(self.elapsed)} min{tail}"
        )

    def phase(self, name: str, detail: str = "") -> None:
        since = time.perf_counter() - self._subproblem_start
        self._write(f"          {name:<10} {detail:<22} +{_minutes(since)} min")

    def finish_subproblem(self, claimed: int | None = None) -> None:
        self.work_done += self._current_k
        took = time.perf_counter() - self._subproblem_start
        eta = remaining_seconds(self.elapsed, self.work_done, self.work_total)
        parts = [f"[{self.index}/{len(self.plan)}] done in {_minutes(took)} min"]
        if claimed is not None:
            parts.append(f"claimed {claimed:,}")
        parts.append(f"eta {_minutes(eta)} min")
        self._write("   ".join(parts))
