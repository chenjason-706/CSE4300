import pytest

from vmsim.replacement import ClockPolicy, FIFOPolicy, LRUPolicy, OPTPolicy, make_policy
from vmsim.swap import SwapSpace

LECTURE = [0, 1, 2, 0, 1, 3, 0, 3, 1, 2, 1]
BELADY = [1, 2, 3, 4, 1, 2, 5, 1, 2, 3, 4, 5]


def count_faults(policy_name, pages, num_frames, pid=0):
    """Run a list of page numbers through a policy on its own, without the MMU."""
    future = [(pid, page) for page in pages]
    policy = make_policy(policy_name, num_frames, future=future)
    where = {}
    free = list(range(num_frames))
    faults = 0
    for page in pages:
        if page not in where:
            faults += 1
            if free:
                frame = free.pop(0)
            else:
                frame = policy.choose_victim()
                policy.on_evict(frame)
                del where[next(p for p, f in where.items() if f == frame)]
            where[page] = frame
            policy.on_load(frame)
        policy.on_access(where[page])
    return faults


# ---- lecture examples ----

@pytest.mark.parametrize("name, expected", [("fifo", 7), ("clock", 7), ("lru", 5), ("opt", 5)])
def test_lecture_example(name, expected):
    assert count_faults(name, LECTURE, 3) == expected


def test_belady_anomaly_with_fifo():
    assert count_faults("fifo", BELADY, 3) == 9
    assert count_faults("fifo", BELADY, 4) == 10


def test_lru_and_opt_do_not_get_worse_with_more_frames():
    for name in ("lru", "opt"):
        faults = [count_faults(name, BELADY, n) for n in (1, 2, 3, 4, 5)]
        assert faults == sorted(faults, reverse=True)


# ---- each policy's victim choice ----

def test_fifo_ignores_accesses():
    fifo = FIFOPolicy(3)
    for frame in (0, 1, 2):
        fifo.on_load(frame)
    fifo.on_access(0)
    fifo.on_access(0)
    assert fifo.choose_victim() == 0


def test_lru_evicts_least_recently_accessed():
    lru = LRUPolicy(3)
    for frame in (0, 1, 2):
        lru.on_load(frame)
        lru.on_access(frame)
    lru.on_access(0)
    assert lru.choose_victim() == 1


def test_clock_gives_referenced_frames_a_second_chance():
    clock = ClockPolicy(3)
    for frame in (0, 1, 2):
        clock.on_load(frame)
    clock.on_access(0)
    clock.on_access(2)
    # the hand clears frame 0's bit, then stops at frame 1 (bit already clear)
    assert clock.choose_victim() == 1
    clock.on_evict(1)
    clock.on_load(1)
    # the hand is now at frame 2: it clears 2's bit, then frame 0 has no bit left
    assert clock.choose_victim() == 0


def test_clock_clears_bits_when_everything_is_referenced():
    clock = ClockPolicy(2)
    for frame in (0, 1):
        clock.on_load(frame)
        clock.on_access(frame)
    assert clock.choose_victim() == 0
    assert clock.referenced == {0: False, 1: False}


def test_opt_evicts_page_used_furthest_away_or_never():
    future = [(0, p) for p in (1, 2, 3, 1, 2, 4)]
    opt = OPTPolicy(3, future)
    for frame in (0, 1, 2):
        opt.on_load(frame)
        opt.on_access(frame)
    # page 3 (frame 2) is never used again
    assert opt.choose_victim() == 2


def test_opt_keeps_processes_separate():
    future = [(1, 7), (2, 7), (1, 7), (1, 8), (1, 7)]
    opt = OPTPolicy(2, future)
    opt.on_load(0)
    opt.on_access(0)
    opt.on_load(1)
    opt.on_access(1)
    opt.on_access(0)
    # (2, 7) is never used again, (1, 7) is, so evict process 2's page
    assert opt.choose_victim() == 1


def test_opt_notices_when_mmu_and_trace_disagree():
    opt = OPTPolicy(2, [(0, 1)])
    opt.on_load(0)
    opt.on_access(0)
    with pytest.raises(RuntimeError):
        opt.on_access(0)


# ---- make_policy and bad input ----

def test_make_policy_by_name():
    assert isinstance(make_policy("FIFO", 2), FIFOPolicy)
    assert isinstance(make_policy("lru", 2), LRUPolicy)
    assert isinstance(make_policy("clock", 2), ClockPolicy)
    assert isinstance(make_policy("opt", 2, future=[]), OPTPolicy)


def test_make_policy_errors():
    with pytest.raises(ValueError):
        make_policy("random", 2)
    with pytest.raises(ValueError):
        make_policy("opt", 2)
    with pytest.raises(ValueError):
        make_policy("fifo", 0)


@pytest.mark.parametrize("name", ["fifo", "clock", "lru", "opt"])
def test_choose_victim_with_no_pages_is_an_error(name):
    with pytest.raises(RuntimeError):
        make_policy(name, 2, future=[]).choose_victim()


@pytest.mark.parametrize("name", ["fifo", "clock", "lru"])
def test_loading_a_frame_twice_is_an_error(name):
    policy = make_policy(name, 2)
    policy.on_load(0)
    with pytest.raises(ValueError):
        policy.on_load(0)


# ---- swap space ----

def test_swap_counts_reads_and_writes():
    swap = SwapSpace()
    slot = swap.write(1, 10)
    swap.read(slot)
    swap.read(slot)
    assert swap.stats == {"reads": 2, "writes": 1}
    assert swap.slots == {slot: (1, 10)}


def test_swap_reuses_a_pages_own_slot():
    swap = SwapSpace()
    first = swap.write(1, 10)
    swap.write(1, 11)
    assert swap.write(1, 10) == first
    assert swap.stats["writes"] == 3


def test_swap_reuses_freed_slots_lowest_first():
    swap = SwapSpace()
    slots = [swap.write(1, vpn) for vpn in range(3)]
    assert slots == [0, 1, 2]
    swap.free(2)
    swap.free(0)
    assert swap.write(2, 50) == 0
    assert swap.write(2, 51) == 2
    assert swap.write(2, 52) == 3


def test_swap_rejects_unknown_slots():
    swap = SwapSpace()
    with pytest.raises(ValueError):
        swap.read(0)
    with pytest.raises(ValueError):
        swap.free(0)
