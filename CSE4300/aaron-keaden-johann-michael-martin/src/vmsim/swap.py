"""Metadata-only simulation of a reusable, unbounded swap space."""

import heapq


class SwapSpace:
    """Manage swap slots and count I/O operations, not actual page bytes."""

    def __init__(self) -> None:
        self.slots: dict[int, tuple[int, int]] = {}
        self._page_slots: dict[tuple[int, int], int] = {}
        self._free_slots: list[int] = []
        self._next_slot = 0
        self.stats = {"reads": 0, "writes": 0}

    def write(self, pid: int, vpn: int) -> int:
        """Write a dirty page; reuse its existing backing slot if present."""
        page = (pid, vpn)
        if page in self._page_slots:
            slot = self._page_slots[page]
        elif self._free_slots:
            slot = heapq.heappop(self._free_slots)
        else:
            slot = self._next_slot
            self._next_slot += 1
        self.slots[slot] = page
        self._page_slots[page] = slot
        self.stats["writes"] += 1
        return slot

    def read(self, slot: int) -> None:
        """Read a valid slot; keep its backing copy until explicitly freed."""
        if slot not in self.slots:
            raise ValueError(f"Invalid swap slot: {slot}")
        self.stats["reads"] += 1

    def free(self, slot: int) -> None:
        """Release a slot so later writes can reuse it."""
        if slot not in self.slots:
            raise ValueError(f"Invalid swap slot: {slot}")
        page = self.slots.pop(slot)
        del self._page_slots[page]
        heapq.heappush(self._free_slots, slot)
