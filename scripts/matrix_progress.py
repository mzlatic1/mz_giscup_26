#!/usr/bin/env python
"""Read-only progress probe for an in-flight visibility matrix build.

The matrix is an np.memmap that is fully preallocated and zero-filled before any
worker starts, so file size and `du` are both useless as progress signals. What IS
a signal: `build_visibility_matrix` splits the candidate rows into `workers * 4`
contiguous chunks and each worker writes only its own disjoint row range. A row
that has not been processed yet is therefore still exactly zero, and a candidate
that has been processed is essentially never all-zero (it always sees boundary
samples near itself).

So: sample small windows across the file and map the zero/nonzero frontier. With
8 workers on 32 chunks the pattern is not one frontier but eight -- chunks are
handed out in order, so expect a run of finished chunks, then up to 8 partially
filled ones, then untouched tail.

Touches nothing. Drops the pages it reads so it does not evict the build's cache.
"""

from __future__ import annotations

import argparse
import os
import sys


def probe(path: str, windows: int, win_bytes: int) -> list[tuple[int, bool]]:
    size = os.path.getsize(path)
    step = size // windows
    out: list[tuple[int, bool]] = []
    fd = os.open(path, os.O_RDONLY)
    try:
        for i in range(windows):
            off = i * step
            os.lseek(fd, off, os.SEEK_SET)
            buf = os.read(fd, min(win_bytes, size - off))
            out.append((off, any(buf)))
        try:  # keep the build's page cache intact
            os.posix_fadvise(fd, 0, 0, os.POSIX_FADV_DONTNEED)
        except (AttributeError, OSError):
            pass
    finally:
        os.close(fd)
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--bits", required=True)
    ap.add_argument("--windows", type=int, default=320)
    ap.add_argument("--win-bytes", type=int, default=65536)
    ap.add_argument("--chunks", type=int, default=32, help="workers * 4, the build's chunk count")
    args = ap.parse_args()

    size = os.path.getsize(args.bits)
    res = probe(args.bits, args.windows, args.win_bytes)
    per_chunk = args.windows // args.chunks

    print(f"file {size:,} bytes   {args.windows} windows of {args.win_bytes:,} B")
    print()
    bar = "".join("#" if nz else "." for _, nz in res)
    for c in range(args.chunks):
        seg = bar[c * per_chunk : (c + 1) * per_chunk]
        filled = seg.count("#")
        state = "DONE" if filled == per_chunk else ("empty" if filled == 0 else f"partial {filled}/{per_chunk}")
        print(f"  chunk {c:2d}  [{seg}]  {state}")

    nz = sum(1 for _, v in res if v)
    print()
    print(f"nonzero windows: {nz}/{args.windows} = {100.0 * nz / args.windows:.1f}%")
    return 0


if __name__ == "__main__":
    sys.exit(main())
