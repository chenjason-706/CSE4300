"""Sparse two-level page tables."""

from dataclasses import dataclass


_INDEX_BITS = 18
_INDEX_MASK = (1 << _INDEX_BITS) - 1


@dataclass
class PTE:
    """Translation and state for one virtual page."""

    frame: int | None = None
    valid: bool = False
    dirty: bool = False
    referenced: bool = False
    swap_slot: int | None = None


class PageTable:
    """Sparse two-level page table for one process."""

    def __init__(self) -> None:
        self._entries: dict[int, dict[int, PTE]] = {}

    @staticmethod
    def _indices(vpn: int) -> tuple[int, int]:
        return vpn >> _INDEX_BITS, vpn & _INDEX_MASK

    def lookup(self, vpn: int) -> PTE | None:
        """Return the PTE for vpn, or None if no entry exists."""
        outer, inner = self._indices(vpn)
        return self._entries.get(outer, {}).get(inner)

    def map(self, vpn: int, frame: int) -> None:
        """Map vpn to frame, creating its PTE when necessary."""
        outer, inner = self._indices(vpn)
        pte = self._entries.setdefault(outer, {}).setdefault(inner, PTE())
        pte.frame = frame
        pte.valid = True
        pte.dirty = False
        pte.referenced = False

    def unmap(self, vpn: int) -> None:
        """Invalidate vpn while retaining its PTE and swap metadata."""
        pte = self.lookup(vpn)
        if pte is not None:
            pte.frame = None
            pte.valid = False
