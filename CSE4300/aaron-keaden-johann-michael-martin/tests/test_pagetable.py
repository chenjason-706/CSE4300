import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from vmsim.pagetable import PTE, PageTable


def test_pte_defaults() -> None:
    assert PTE() == PTE(
        frame=None,
        valid=False,
        dirty=False,
        referenced=False,
        swap_slot=None,
    )


def test_map_and_lookup_use_both_levels() -> None:
    page_table = PageTable()
    first_vpn = (3 << 18) | 5
    same_outer_vpn = (3 << 18) | 6
    next_outer_vpn = (4 << 18) | 5

    page_table.map(first_vpn, 2)
    page_table.map(same_outer_vpn, 4)
    page_table.map(next_outer_vpn, 6)

    assert page_table.lookup(first_vpn).frame == 2
    assert page_table.lookup(same_outer_vpn).frame == 4
    assert page_table.lookup(next_outer_vpn).frame == 6
    assert page_table.lookup((3 << 18) | 7) is None


def test_unmap_preserves_pte_swap_information() -> None:
    page_table = PageTable()
    vpn = (1 << 18) | 9
    page_table.map(vpn, 3)
    pte = page_table.lookup(vpn)
    assert pte is not None
    pte.swap_slot = 12
    pte.dirty = True
    pte.referenced = True

    page_table.unmap(vpn)

    assert page_table.lookup(vpn) is pte
    assert pte.frame is None
    assert not pte.valid
    assert pte.swap_slot == 12
    assert pte.dirty
    assert pte.referenced


def test_unmap_unknown_vpn_is_a_no_op() -> None:
    page_table = PageTable()

    page_table.unmap(123)

    assert page_table.lookup(123) is None
