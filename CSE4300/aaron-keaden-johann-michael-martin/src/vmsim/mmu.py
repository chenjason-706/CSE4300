"""Memory management unit for the virtual memory simulator."""

from typing import Any

from .frames import FrameTable
from .pagetable import PageTable


class MMU:
    """Translate memory accesses and coordinate memory-management components."""

    def __init__(self, num_frames: int, tlb: Any, policy: Any, swap: Any) -> None:
        self.frames = FrameTable(num_frames)
        self.tlb = tlb
        self.policy = policy
        self.swap = swap
        self.page_tables: dict[int, PageTable] = {}
        self.current_pid: int | None = None
        self.stats = {
            "accesses": 0,
            "page_faults": 0,
            "evictions": 0,
            "swap_ins": 0,
            "swap_outs": 0,
            "context_switches": 0,
        }

    def _page_table(self, pid: int) -> PageTable:
        return self.page_tables.setdefault(pid, PageTable())

    def _tlb_flush_count(self) -> int:
        flushes = getattr(self.tlb, "flushes", None)
        if flushes is not None:
            return flushes
        stats = getattr(self.tlb, "stats", None)
        if isinstance(stats, dict) and "flushes" in stats:
            return stats["flushes"]
        raise AttributeError("TLB must expose its flush counter as flushes or stats['flushes']")

    def _insert_tlb(self, pid: int, vpn: int, frame: int) -> tuple[int, int] | None:
        return self.tlb.insert(pid, vpn, frame)

    def access(self, a: Any) -> dict:
        """Translate and record one memory access."""
        pid, op, vaddr = a.pid, a.op, a.vaddr
        if op not in ("R", "W"):
            raise ValueError(f"unsupported memory operation: {op}")

        vpn = vaddr >> 12
        page_table = self._page_table(pid)
        tlb_frame = self.tlb.lookup(pid, vpn)
        pte = page_table.lookup(vpn)
        tlb_status = "hit" if tlb_frame is not None else "miss"
        pt_status = None
        evict = None
        tlb_evict = None
        swap_in = False

        if tlb_frame is not None:
            if pte is None or not pte.valid or pte.frame != tlb_frame:
                raise RuntimeError(f"stale TLB translation for pid {pid}, vpn {vpn}")
            frame = tlb_frame
        elif pte is not None and pte.valid:
            frame = pte.frame
            if frame is None:
                raise RuntimeError(f"valid PTE has no frame for pid {pid}, vpn {vpn}")
            pt_status = "hit"
            tlb_evict = self._insert_tlb(pid, vpn, frame)
        else:
            pt_status = "fault"
            self.stats["page_faults"] += 1
            frame = self.frames.alloc()

            if frame is None:
                frame = self.policy.choose_victim()
                if frame is None:
                    raise RuntimeError("replacement policy returned no victim when memory is full")
                victim_pid, victim_vpn = self.frames.owner(frame)
                victim_table = self._page_table(victim_pid)
                victim_pte = victim_table.lookup(victim_vpn)
                if victim_pte is None or not victim_pte.valid or victim_pte.frame != frame:
                    raise RuntimeError(
                        f"frame {frame} owner does not have a matching valid page-table entry"
                    )

                victim_dirty = victim_pte.dirty
                swap_slot = victim_pte.swap_slot
                if victim_dirty:
                    swap_slot = self.swap.write(victim_pid, victim_vpn)
                    victim_pte.swap_slot = swap_slot
                    self.stats["swap_outs"] += 1

                evict = {
                    "pid": victim_pid,
                    "vpn": victim_vpn,
                    "dirty": victim_dirty,
                    "swap_slot": swap_slot,
                }
                victim_table.unmap(victim_vpn)
                self.tlb.invalidate(victim_pid, victim_vpn)
                self.policy.on_evict(frame)
                self.stats["evictions"] += 1

            if pte is not None and pte.swap_slot is not None:
                # Keep the swap copy. If this page is evicted again without
                # being written, the copy in swap is still up to date, and the
                # next fault has to read it back from swap again.
                self.swap.read(pte.swap_slot)
                swap_in = True
                self.stats["swap_ins"] += 1

            page_table.map(vpn, frame)
            self.frames.set_owner(frame, pid, vpn)
            self.policy.on_load(frame)
            tlb_evict = self._insert_tlb(pid, vpn, frame)
            pte = page_table.lookup(vpn)

        if pte is None:
            raise RuntimeError(f"missing PTE after translating pid {pid}, vpn {vpn}")
        pte.referenced = True
        if op == "W":
            pte.dirty = True
        self.policy.on_access(frame)
        self.stats["accesses"] += 1

        return {
            "type": "access",
            "pid": pid,
            "op": op,
            "vaddr": hex(vaddr),
            "vpn": vpn,
            "tlb": tlb_status,
            "pt": pt_status,
            "frame": frame,
            "evict": evict,
            "swap_in": swap_in,
            "tlb_evict": tlb_evict,
        }

    def context_switch(self, new_pid: int) -> dict:
        """Switch processes and report whether the TLB was flushed."""
        previous_pid = self.current_pid
        flushes_before = self._tlb_flush_count()
        self.tlb.context_switch(new_pid)
        flushed = self._tlb_flush_count() > flushes_before
        self.current_pid = new_pid
        self.stats["context_switches"] += 1
        return {
            "type": "switch",
            "from": previous_pid,
            "to": new_pid,
            "flushed": flushed,
        }
