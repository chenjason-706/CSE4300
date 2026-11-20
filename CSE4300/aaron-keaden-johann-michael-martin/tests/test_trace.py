import gzip
from pathlib import Path

from vmsim.trace import Access, interleave, load_lackey, synthetic


SAMPLE = Path(__file__).parent / "data" / "sample.trace"


def test_load_lackey():
    # check that the header is skipped and each operation gets the right type
    assert load_lackey(SAMPLE, pid=1) == [
        Access(1, "R", 0x1000),
        Access(1, "R", 0x1008),
        Access(1, "W", 0x2000),
        Access(1, "W", 0x3000),
    ]


def test_load_lackey_gzip(tmp_path):
    # the real traces are stored gzipped, so make sure those load the same way
    zipped = tmp_path / "sample.trace.gz"
    zipped.write_bytes(gzip.compress(SAMPLE.read_bytes()))
    assert load_lackey(zipped, pid=1) == load_lackey(SAMPLE, pid=1)


def test_load_lackey_limit():
    assert len(load_lackey(SAMPLE, pid=1, limit=2)) == 2


def test_synthetic_loop():
    accesses = synthetic("loop", n=5, num_pages=3)
    assert [a.vaddr for a in accesses] == [0, 4096, 8192, 0, 4096]


def test_interleave():
    first = synthetic("loop", n=3, num_pages=3, pid=1)
    second = synthetic("loop", n=2, num_pages=2, pid=2)

    # give each process two accesses per turn
    assert interleave([first, second], quantum=2) == [
        first[0], first[1], second[0], second[1], first[2]
    ]