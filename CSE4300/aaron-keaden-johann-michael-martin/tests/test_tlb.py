import pytest

from vmsim.tlb import TLB, effective_access_time


def test_miss_before_insert_then_hit_after():
    tlb = TLB(size=4)
    assert tlb.lookup(1, 10) is None
    tlb.insert(1, 10, frame=3)
    assert tlb.lookup(1, 10) == 3
    assert tlb.stats["misses"] == 1
    assert tlb.stats["hits"] == 1
    assert tlb.hit_rate == 0.5


def test_same_vpn_different_pid_is_a_different_entry():
    tlb = TLB(size=4, use_asid=True)
    tlb.insert(1, 10, frame=3)
    assert tlb.lookup(2, 10) is None


def test_insert_existing_entry_updates_frame_without_evicting():
    tlb = TLB(size=2)
    tlb.insert(1, 10, frame=3)
    tlb.insert(1, 11, frame=4)
    assert tlb.insert(1, 10, frame=7) is None
    assert tlb.lookup(1, 10) == 7
    assert len(tlb) == 2


def test_size_limit_is_respected():
    tlb = TLB(size=3)
    for vpn in range(10):
        tlb.insert(1, vpn, frame=vpn)
    assert len(tlb) == 3
    assert tlb.stats["evictions"] == 7


def test_lru_evicts_least_recently_used():
    tlb = TLB(size=3, policy="lru")
    tlb.insert(1, 1, 10)
    tlb.insert(1, 2, 20)
    tlb.insert(1, 3, 30)
    tlb.lookup(1, 1)
    evicted = tlb.insert(1, 4, 40)
    assert evicted == (1, 2)
    assert (1, 1) in tlb
    assert (1, 2) not in tlb


def test_random_policy_stays_within_size_and_is_repeatable():
    def run(seed):
        tlb = TLB(size=4, policy="random", seed=seed)
        return [tlb.insert(1, vpn, vpn) for vpn in range(20)]

    assert run(seed=42) == run(seed=42)
    tlb = TLB(size=4, policy="random")
    for vpn in range(20):
        tlb.insert(1, vpn, vpn)
    assert len(tlb) == 4


def test_invalidate_removes_only_that_entry():
    tlb = TLB(size=4)
    tlb.insert(1, 1, 10)
    tlb.insert(1, 2, 20)
    tlb.invalidate(1, 1)
    assert (1, 1) not in tlb
    assert (1, 2) in tlb
    tlb.invalidate(1, 99)
    assert tlb.stats["invalidations"] == 1


def test_context_switch_flushes_without_asid():
    tlb = TLB(size=4, use_asid=False)
    tlb.context_switch(1)
    tlb.insert(1, 1, 10)
    tlb.insert(1, 2, 20)
    tlb.context_switch(2)
    assert len(tlb) == 0
    assert tlb.stats["flushes"] == 1


def test_switching_to_same_pid_does_not_flush():
    tlb = TLB(size=4)
    tlb.context_switch(1)
    tlb.insert(1, 1, 10)
    tlb.context_switch(1)
    assert len(tlb) == 1
    assert tlb.stats["flushes"] == 0


def test_asid_keeps_entries_across_switches():
    tlb = TLB(size=4, use_asid=True)
    tlb.context_switch(1)
    tlb.insert(1, 1, 10)
    tlb.context_switch(2)
    tlb.insert(2, 1, 20)
    tlb.context_switch(1)
    assert tlb.lookup(1, 1) == 10
    assert tlb.lookup(2, 1) == 20
    assert tlb.stats["flushes"] == 0


def test_asid_beats_flushing_when_processes_take_turns():
    def hit_rate(use_asid):
        tlb = TLB(size=8, use_asid=use_asid)
        for _ in range(50):
            for pid in (1, 2):
                tlb.context_switch(pid)
                for vpn in range(3):
                    if tlb.lookup(pid, vpn) is None:
                        tlb.insert(pid, vpn, vpn)
        return tlb.hit_rate

    assert hit_rate(use_asid=True) > hit_rate(use_asid=False)


def test_set_associative_only_evicts_within_a_set():
    tlb = TLB(size=4, ways=2)
    tlb.insert(1, 0, 0)
    tlb.insert(1, 2, 2)
    tlb.insert(1, 1, 1)
    evicted = tlb.insert(1, 4, 4)
    assert evicted == (1, 0)
    assert (1, 1) in tlb


def test_bad_arguments_raise():
    with pytest.raises(ValueError):
        TLB(size=0)
    with pytest.raises(ValueError):
        TLB(size=4, policy="fifo")
    with pytest.raises(ValueError):
        TLB(size=6, ways=4)


def test_effective_access_time():
    assert effective_access_time(1.0, tlb_ns=1, mem_ns=100) == 101
    assert effective_access_time(0.0, tlb_ns=1, mem_ns=100, levels=2) == 301
    assert effective_access_time(0.5, tlb_ns=1, mem_ns=100) == pytest.approx(201)


def test_end_to_end_small_trace():
    mmu_mod = pytest.importorskip("vmsim.mmu")
    trace_mod = pytest.importorskip("vmsim.trace")
    repl_mod = pytest.importorskip("vmsim.replacement")
    swap_mod = pytest.importorskip("vmsim.swap")

    accesses = trace_mod.synthetic("loop", n=200, num_pages=6, pid=0)
    future = [(a.pid, a.vaddr >> 12) for a in accesses]
    mmu = mmu_mod.MMU(
        num_frames=4,
        tlb=TLB(size=2),
        policy=repl_mod.make_policy("fifo", 4, future=future),
        swap=swap_mod.SwapSpace(),
    )
    events = [mmu.access(a) for a in accesses]

    assert len(events) == 200
    assert all(e["tlb"] in ("hit", "miss") for e in events)
    assert all(e["pt"] is None for e in events if e["tlb"] == "hit")
