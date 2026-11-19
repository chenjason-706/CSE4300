import gzip
import random
from collections import deque
from dataclasses import dataclass
from pathlib import Path


PAGE_SIZE = 4096
OP_TYPES = {"I": "R", "L": "R", "S": "W", "M": "W"}


@dataclass
class Access:
    pid: int
    op: str
    vaddr: int


def load_lackey(
    path: str | Path, pid: int, limit: int | None = None
) -> list[Access]:
    """turn the lackey log into a list of memory accesses."""
    if limit is None:
        limit = 1_000_000
    if limit < 0:
        raise ValueError("limit must be non-negative")
    if limit == 0:
        return []

    accesses = []
    # traces in traces/ are gzipped to keep the repo small, so open both kinds.
    path = Path(path)
    opener = gzip.open if path.suffix == ".gz" else open
    with opener(path, "rt", encoding="utf-8") as trace:
        for line in trace:
            # skip the valgrind headers and anything that isn't a memory access.
            parts = line.split()
            if len(parts) != 2 or parts[0] not in OP_TYPES:
                continue

            op, location = parts
            address, comma, size = location.partition(",")
            if not comma or not size.isdecimal():
                continue

            try:
                vaddr = int(address, 16)
            except ValueError:
                continue

            accesses.append(Access(pid, OP_TYPES[op], vaddr))
            if len(accesses) == limit:
                break

    return accesses


def synthetic(kind: str, n: int, num_pages: int, pid: int = 0) -> list[Access]:
    """make a trace for testing without running valgrind."""
    if n < 0 or num_pages <= 0:
        raise ValueError("n must be non-negative and num_pages must be positive")

    if kind == "sequential":
        # move 8 bytes at a time so we read the same page for a while.
        addresses = (i * 8 % (num_pages * PAGE_SIZE) for i in range(n))
    elif kind == "loop":
        # touch one address on each page, then go back to the first page.
        addresses = ((i % num_pages) * PAGE_SIZE for i in range(n))
    elif kind == "random":
        # use the same seed so we can compare runs with the same trace.
        rng = random.Random(0)
        addresses = (rng.randrange(num_pages) * PAGE_SIZE for _ in range(n))
    else:
        raise ValueError(f"unknown synthetic trace kind: {kind}")

    return [Access(pid, "R", address) for address in addresses]


def interleave(traces: list[list[Access]], quantum: int) -> list[Access]:
    """give each process up to quantum accesses before switching."""
    if quantum <= 0:
        raise ValueError("quantum must be positive")

    pending = deque((trace, 0) for trace in traces if trace)
    accesses = []
    while pending:
        trace, start = pending.popleft()
        end = start + quantum
        accesses.extend(trace[start:end])

        # only put this trace back in line if it has accesses left.
        if end < len(trace):
            pending.append((trace, end))

    return accesses