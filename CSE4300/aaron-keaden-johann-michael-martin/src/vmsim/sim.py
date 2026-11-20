import json
from contextlib import nullcontext
from pathlib import Path

from .mmu import MMU
from .tlb import TLB
from .trace import Access


def run_simulation(
    accesses: list[Access],
    *,
    frames: int = 64,
    tlb_size: int = 16,
    policy: str = "clock",
    tlb_policy: str = "lru",
    asid: bool = False,
    log_path: str | Path | None = None,
) -> dict[str, int | float]:
    """run the accesses through the mmu and return the stats."""
    from .replacement import make_policy
    from .swap import SwapSpace

    # only opt needs the full list of pages ahead of time.
    future = [(a.pid, a.vaddr >> 12) for a in accesses] if policy == "opt" else None
    tlb = TLB(tlb_size, policy=tlb_policy, use_asid=asid)
    mmu = MMU(frames, tlb, make_policy(policy, frames, future=future), SwapSpace())

    config = {
        "type": "config",
        "frames": frames,
        "tlb_size": tlb_size,
        "policy": policy,
        "tlb_policy": tlb_policy,
        "asid": asid,
    }

    log_file = nullcontext()
    if log_path is not None:
        path = Path(log_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        log_file = path.open("w", encoding="utf-8")

    step = 0
    switches = 0
    previous_pid = None
    with log_file as log:
        if log is not None:
            log.write(json.dumps(config) + "\n")

        for access in accesses:
            if access.pid != previous_pid:
                event = mmu.context_switch(access.pid)
                # the first process is just getting started.
                if previous_pid is not None:
                    switches += 1
                    if log is not None:
                        log.write(json.dumps({**event, "t": step}) + "\n")
                    step += 1
                previous_pid = access.pid

            event = mmu.access(access)
            if log is not None:
                if event["tlb_evict"] is not None:
                    pid, vpn = event["tlb_evict"]
                    event["tlb_evict"] = {"pid": pid, "vpn": vpn}
                log.write(json.dumps({**event, "t": step}) + "\n")
            step += 1

    total = mmu.stats["accesses"]
    faults = mmu.stats["page_faults"]
    return {
        "accesses": total,
        "tlb_hits": tlb.stats["hits"],
        "tlb_misses": tlb.stats["misses"],
        "tlb_hit_rate": tlb.hit_rate,
        "page_faults": faults,
        "page_fault_rate": faults / total if total else 0.0,
        "swap_reads": mmu.stats["swap_ins"],
        "swap_writes": mmu.stats["swap_outs"],
        "context_switches": switches,
    }


def print_summary(stats: dict[str, int | float]) -> None:
    """print the stats at the end of a run."""
    print(f"Total accesses: {stats['accesses']}")
    print(f"TLB hits: {stats['tlb_hits']} ({stats['tlb_hit_rate']:.2%})")
    print(f"TLB misses: {stats['tlb_misses']}")
    print(f"Page faults: {stats['page_faults']} ({stats['page_fault_rate']:.2%})")
    print(f"Swap reads: {stats['swap_reads']}")
    print(f"Swap writes: {stats['swap_writes']}")
    print(f"Context switches: {stats['context_switches']}")