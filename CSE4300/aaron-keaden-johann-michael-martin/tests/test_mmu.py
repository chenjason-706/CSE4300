import sys
from dataclasses import dataclass
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from vmsim.frames import FrameTable
from vmsim.mmu import MMU
from vmsim.tlb import TLB


@dataclass
class Access:
    pid: int
    op: str
    vaddr: int


class StubPolicy:
    def __init__(self) -> None:
        self.frames: list[int] = []
        self.accesses: list[int] = []

    def on_load(self, frame: int) -> None:
        self.frames.append(frame)

    def on_access(self, frame: int) -> None:
        self.accesses.append(frame)

    def on_evict(self, frame: int) -> None:
        self.frames.remove(frame)

    def choose_victim(self) -> int:
        return self.frames[0]


class StubSwap:
    def __init__(self) -> None:
        self.slots: dict[int, tuple[int, int]] = {}
        self.next_slot = 0
        self.reads: list[int] = []
        self.writes: list[tuple[int, int]] = []

    def write(self, pid: int, vpn: int) -> int:
        slot = self.next_slot
        self.next_slot += 1
        self.writes.append((pid, vpn))
        self.slots[slot] = (pid, vpn)
        return slot

    def read(self, slot: int) -> tuple[int, int]:
        self.reads.append(slot)
        return self.slots[slot]

    def free(self, slot: int) -> None:
        del self.slots[slot]


def make_mmu(
    num_frames: int = 2,
    tlb_capacity: int = 8,
    use_asid: bool = False,
) -> tuple[MMU, TLB, StubPolicy, StubSwap]:
    tlb = TLB(size=tlb_capacity, use_asid=use_asid)
    policy = StubPolicy()
    swap = StubSwap()
    return MMU(num_frames, tlb, policy, swap), tlb, policy, swap


def test_frame_table_allocates_tracks_owners_and_reuses_frames() -> None:
    frames = FrameTable(2)
    first = frames.alloc()
    assert first == 0
    frames.set_owner(first, 4, 17)
    assert frames.owner(first) == (4, 17)

    assert frames.alloc() == 1
    assert frames.alloc() is None
    frames.free(first)
    assert frames.alloc() == first


def test_first_access_fault_and_repeated_tlb_hit() -> None:
    mmu, _, policy, _ = make_mmu()

    first = mmu.access(Access(1, "R", 0x4000A10))
    repeated = mmu.access(Access(1, "R", 0x4000A10))

    assert first == {
        "type": "access",
        "pid": 1,
        "op": "R",
        "vaddr": "0x4000a10",
        "vpn": 0x4000,
        "tlb": "miss",
        "pt": "fault",
        "frame": 0,
        "evict": None,
        "swap_in": False,
        "tlb_evict": None,
    }
    assert repeated["tlb"] == "hit"
    assert repeated["pt"] is None
    assert repeated["frame"] == first["frame"]
    assert policy.accesses == [0, 0]
    assert mmu.stats["accesses"] == 2
    assert mmu.stats["page_faults"] == 1


def test_page_table_hit_and_tlb_eviction_are_reported() -> None:
    mmu, tlb, _, _ = make_mmu(tlb_capacity=1)
    mmu.access(Access(2, "R", 0))

    second = mmu.access(Access(2, "R", 1 << 12))
    assert second["tlb_evict"] == (2, 0)
    tlb.invalidate(2, 1)

    resident = mmu.access(Access(2, "W", 1 << 12))
    assert resident["tlb"] == "miss"
    assert resident["pt"] == "hit"
    pte = mmu.page_tables[2].lookup(1)
    assert pte is not None and pte.referenced and pte.dirty


def test_dirty_eviction_swaps_out_and_page_fault_swaps_back_in() -> None:
    mmu, _, _, swap = make_mmu()
    mmu.access(Access(3, "W", 0))
    mmu.access(Access(3, "R", 1 << 12))

    eviction = mmu.access(Access(3, "R", 2 << 12))
    assert eviction["evict"] == {
        "pid": 3,
        "vpn": 0,
        "dirty": True,
        "swap_slot": 0,
    }
    old_pte = mmu.page_tables[3].lookup(0)
    assert old_pte is not None and not old_pte.valid and old_pte.swap_slot == 0

    swap_in = mmu.access(Access(3, "R", 0))
    assert swap_in["swap_in"]
    assert swap.reads == [0]
    assert swap.slots == {0: (3, 0)}
    assert mmu.page_tables[3].lookup(0).swap_slot == 0
    assert mmu.stats["swap_outs"] == 1
    assert mmu.stats["swap_ins"] == 1


def test_multiple_processes_can_map_the_same_vpn() -> None:
    mmu, tlb, _, _ = make_mmu(use_asid=True)
    vpn = 7

    first = mmu.access(Access(1, "R", vpn << 12))
    mmu.context_switch(2)
    second = mmu.access(Access(2, "R", vpn << 12))

    assert first["frame"] != second["frame"]
    assert mmu.page_tables[1].lookup(vpn).frame == first["frame"]
    assert mmu.page_tables[2].lookup(vpn).frame == second["frame"]
    assert tlb.lookup(1, vpn) == first["frame"]
    assert tlb.lookup(2, vpn) == second["frame"]


def test_page_eviction_invalidates_its_tlb_entry() -> None:
    mmu, tlb, _, _ = make_mmu(num_frames=1)
    mmu.access(Access(1, "R", 0))
    assert (1, 0) in tlb

    eviction = mmu.access(Access(1, "R", 1 << 12))

    assert eviction["evict"]["vpn"] == 0
    assert (1, 0) not in tlb
    assert tlb.stats["invalidations"] == 1


def test_clean_page_eviction_does_not_allocate_swap_slot() -> None:
    mmu, _, _, swap = make_mmu(num_frames=1)
    mmu.access(Access(1, "R", 0))

    event = mmu.access(Access(1, "R", 1 << 12))

    assert event["evict"] == {
        "pid": 1,
        "vpn": 0,
        "dirty": False,
        "swap_slot": None,
    }
    assert swap.writes == []
    assert swap.slots == {}


def test_repeated_dirty_swap_in_cycles_keep_latest_swap_copy() -> None:
    mmu, _, _, swap = make_mmu(num_frames=1)
    mmu.access(Access(1, "W", 0))
    first_eviction = mmu.access(Access(1, "R", 1 << 12))
    assert first_eviction["evict"]["swap_slot"] == 0

    first_swap_in = mmu.access(Access(1, "W", 0))
    assert first_swap_in["swap_in"]

    second_eviction = mmu.access(Access(1, "R", 1 << 12))
    assert second_eviction["evict"]["dirty"]
    assert second_eviction["evict"]["swap_slot"] == 1
    second_swap_in = mmu.access(Access(1, "R", 0))

    assert second_swap_in["swap_in"]
    assert swap.writes == [(1, 0), (1, 0)]
    assert swap.reads == [0, 1]
    assert mmu.page_tables[1].lookup(0).swap_slot == 1
    assert mmu.stats["swap_outs"] == 2
    assert mmu.stats["swap_ins"] == 2


def test_clean_page_from_swap_is_read_again_after_clean_eviction() -> None:
    mmu, _, _, swap = make_mmu(num_frames=1)
    mmu.access(Access(1, "W", 0))
    mmu.access(Access(1, "R", 1 << 12))
    mmu.access(Access(1, "R", 0))

    clean_eviction = mmu.access(Access(1, "R", 1 << 12))
    assert clean_eviction["evict"] == {
        "pid": 1,
        "vpn": 0,
        "dirty": False,
        "swap_slot": 0,
    }

    back_again = mmu.access(Access(1, "R", 0))
    assert back_again["swap_in"]
    assert swap.writes == [(1, 0)]
    assert swap.reads == [0, 0]
    assert mmu.stats["swap_ins"] == 2


def test_context_switch_event_and_flush_without_asids() -> None:
    mmu, _, _, _ = make_mmu()

    first = mmu.context_switch(5)
    second = mmu.context_switch(6)

    assert first == {
        "type": "switch",
        "from": None,
        "to": 5,
        "flushed": False,
    }
    assert second == {
        "type": "switch",
        "from": 5,
        "to": 6,
        "flushed": True,
    }
    assert mmu.stats["context_switches"] == 2


def test_context_switches_preserve_entries_with_asids() -> None:
    mmu, tlb, _, _ = make_mmu(use_asid=True)

    first_switch = mmu.context_switch(1)
    first_access = mmu.access(Access(1, "R", 0))
    second_switch = mmu.context_switch(2)
    second_access = mmu.access(Access(2, "R", 0))
    return_switch = mmu.context_switch(1)
    repeated = mmu.access(Access(1, "R", 0))

    assert first_switch["flushed"] is False
    assert second_switch["flushed"] is False
    assert return_switch["flushed"] is False
    assert first_access["frame"] != second_access["frame"]
    assert repeated["tlb"] == "hit"
    assert tlb.stats["flushes"] == 0


def test_access_event_has_project_format() -> None:
    mmu, _, _, _ = make_mmu()

    event = mmu.access(Access(4, "W", 0x4000A10))

    assert event == {
        "type": "access",
        "pid": 4,
        "op": "W",
        "vaddr": "0x4000a10",
        "vpn": 0x4000,
        "tlb": "miss",
        "pt": "fault",
        "frame": 0,
        "evict": None,
        "swap_in": False,
        "tlb_evict": None,
    }
