from __future__ import annotations

import random
from collections import OrderedDict

Key = tuple[int, int]

POLICIES = ("lru", "random")


class TLB:
    def __init__(
        self,
        size: int,
        policy: str = "lru",
        use_asid: bool = False,
        ways: int | None = None,
        seed: int = 0,
    ) -> None:
        if size <= 0:
            raise ValueError("TLB size must be positive")
        if policy not in POLICIES:
            raise ValueError(f"unknown TLB policy {policy!r}, expected one of {POLICIES}")
        if ways is None:
            ways = size
        if ways <= 0 or size % ways != 0:
            raise ValueError("ways must be positive and divide size evenly")

        self.size = size
        self.policy = policy
        self.use_asid = use_asid
        self.ways = ways
        self.num_sets = size // ways
        self.current_pid: int | None = None
        self._rng = random.Random(seed)

        self._sets: list[OrderedDict[Key, int]] = [OrderedDict() for _ in range(self.num_sets)]

        self.stats: dict[str, int] = {
            "hits": 0,
            "misses": 0,
            "flushes": 0,
            "evictions": 0,
            "invalidations": 0,
        }

    def lookup(self, pid: int, vpn: int) -> int | None:
        entries = self._set_for(vpn)
        key = (pid, vpn)
        frame = entries.get(key)
        if frame is None:
            self.stats["misses"] += 1
            return None
        self.stats["hits"] += 1
        entries.move_to_end(key)
        return frame

    def insert(self, pid: int, vpn: int, frame: int) -> Key | None:
        entries = self._set_for(vpn)
        key = (pid, vpn)

        if key in entries:
            entries[key] = frame
            entries.move_to_end(key)
            return None

        evicted = None
        if len(entries) >= self.ways:
            evicted = self._choose_victim(entries)
            del entries[evicted]
            self.stats["evictions"] += 1

        entries[key] = frame
        return evicted

    def invalidate(self, pid: int, vpn: int) -> None:
        entries = self._set_for(vpn)
        if entries.pop((pid, vpn), None) is not None:
            self.stats["invalidations"] += 1

    def context_switch(self, new_pid: int) -> None:
        if new_pid == self.current_pid:
            return
        if not self.use_asid and self.current_pid is not None:
            self.flush()
        self.current_pid = new_pid

    def flush(self) -> None:
        for entries in self._sets:
            entries.clear()
        self.stats["flushes"] += 1

    @property
    def hit_rate(self) -> float:
        total = self.stats["hits"] + self.stats["misses"]
        return self.stats["hits"] / total if total else 0.0

    def entries(self) -> list[tuple[int, int, int]]:
        return [(pid, vpn, frame) for s in self._sets for (pid, vpn), frame in s.items()]

    def __len__(self) -> int:
        return sum(len(s) for s in self._sets)

    def __contains__(self, key: Key) -> bool:
        pid, vpn = key
        return key in self._set_for(vpn)

    def _set_for(self, vpn: int) -> OrderedDict[Key, int]:
        return self._sets[vpn % self.num_sets]

    def _choose_victim(self, entries: OrderedDict[Key, int]) -> Key:
        if self.policy == "lru":
            return next(iter(entries))
        return self._rng.choice(list(entries))


def effective_access_time(
    hit_rate: float,
    tlb_ns: float = 1.0,
    mem_ns: float = 100.0,
    levels: int = 2,
) -> float:
    hit_time = tlb_ns + mem_ns
    miss_time = tlb_ns + levels * mem_ns + mem_ns
    return hit_rate * hit_time + (1 - hit_rate) * miss_time
