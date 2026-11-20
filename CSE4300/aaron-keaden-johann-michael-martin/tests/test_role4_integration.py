"""Martin's policies and swap space running inside the real MMU and TLB."""

import random

import pytest

from vmsim.mmu import MMU
from vmsim.replacement import make_policy
from vmsim.swap import SwapSpace
from vmsim.tlb import TLB
from vmsim.trace import Access

POLICIES = ["fifo", "clock", "lru", "opt"]


def run(accesses, frames, policy, tlb_size=4, asid=False):
    future = [(a.pid, a.vaddr >> 12) for a in accesses]
    swap = SwapSpace()
    tlb = TLB(tlb_size, use_asid=asid)
    mmu = MMU(frames, tlb, make_policy(policy, frames, future=future), swap)
    current = None
    events = []
    for a in accesses:
        if a.pid != current:
            mmu.context_switch(a.pid)
            current = a.pid
        events.append(mmu.access(a))
    return mmu, swap, tlb, events


def pages(numbers, pid=0, op="R"):
    return [Access(pid, op, n << 12) for n in numbers]


def random_trace(seed, n=400, num_pages=12, num_procs=2):
    rng = random.Random(seed)
    return [
        Access(rng.randrange(num_procs) + 1, "W" if rng.random() < 0.3 else "R",
               rng.randrange(num_pages) << 12)
        for _ in range(n)
    ]


@pytest.mark.parametrize("policy, expected", [("fifo", 7), ("clock", 7), ("lru", 5), ("opt", 5)])
def test_lecture_example_through_the_mmu(policy, expected):
    mmu, _, _, _ = run(pages([0, 1, 2, 0, 1, 3, 0, 3, 1, 2, 1]), 3, policy)
    assert mmu.stats["page_faults"] == expected


def test_belady_anomaly_through_the_mmu():
    belady = pages([1, 2, 3, 4, 1, 2, 5, 1, 2, 3, 4, 5])
    assert run(belady, 3, "fifo")[0].stats["page_faults"] == 9
    assert run(belady, 4, "fifo")[0].stats["page_faults"] == 10


@pytest.mark.parametrize("policy", POLICIES)
@pytest.mark.parametrize("asid", [False, True])
def test_memory_stays_consistent_with_every_policy(policy, asid):
    accesses = random_trace(seed=7)
    mmu, swap, tlb, _ = run(accesses, frames=4, policy=policy, asid=asid)

    # every frame's owner has a valid page table entry pointing back at it
    resident = 0
    for frame in range(4):
        pid, vpn = mmu.frames.owner(frame)
        pte = mmu.page_tables[pid].lookup(vpn)
        assert pte.valid and pte.frame == frame
        resident += 1
    valid = sum(
        1
        for pid, table in mmu.page_tables.items()
        for vpn in {a.vaddr >> 12 for a in accesses if a.pid == pid}
        if (pte := table.lookup(vpn)) is not None and pte.valid
    )
    assert valid == resident == 4

    # the TLB only holds translations that match the page tables
    for pid, vpn, frame in tlb.entries():
        assert mmu.page_tables[pid].lookup(vpn).frame == frame

    # the MMU and the swap space agree on the I/O counts
    assert swap.stats["writes"] == mmu.stats["swap_outs"]
    assert swap.stats["reads"] == mmu.stats["swap_ins"]


@pytest.mark.parametrize("seed", range(5))
def test_opt_never_has_more_faults_than_the_others(seed):
    accesses = random_trace(seed)
    faults = {p: run(accesses, 4, p)[0].stats["page_faults"] for p in POLICIES}
    assert faults["opt"] == min(faults.values())


def test_clean_pages_are_never_written_to_swap():
    mmu, swap, _, events = run(pages([0, 1, 2, 3, 0, 1, 2, 3]), 2, "fifo")
    assert mmu.stats["evictions"] > 0
    assert swap.stats["writes"] == 0
    assert all(not e["evict"]["dirty"] for e in events if e["evict"])


def test_dirty_page_goes_to_swap_and_comes_back():
    accesses = pages([0], op="W") + pages([1, 2, 0])
    mmu, swap, _, events = run(accesses, 2, "fifo")
    assert events[2]["evict"] == {"pid": 0, "vpn": 0, "dirty": True, "swap_slot": 0}
    assert events[3]["swap_in"]
    assert swap.stats == {"reads": 1, "writes": 1}


def test_tlb_hits_still_count_as_accesses_for_lru():
    # page 0 is only ever hit in the TLB after the first touch, but LRU still
    # has to see those accesses or it would wrongly evict page 0
    accesses = pages([0, 1, 0, 0, 0, 2])
    mmu, _, _, events = run(accesses, 2, "lru", tlb_size=4)
    assert [e["tlb"] for e in events[2:5]] == ["hit", "hit", "hit"]
    assert events[5]["evict"]["vpn"] == 1
