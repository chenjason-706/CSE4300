"""Aaron's simulation driver and command line."""

import json
import subprocess
import sys
from pathlib import Path

from vmsim.sim import run_simulation
from vmsim.trace import interleave, load_lackey, synthetic

TEAM = Path(__file__).resolve().parents[1]
SAMPLE = TEAM / "tests" / "data" / "sample.trace"


def test_sample_trace_stats():
    stats = run_simulation(load_lackey(SAMPLE, pid=1), frames=2, tlb_size=2, policy="fifo")
    assert stats["accesses"] == 4
    assert stats["tlb_hits"] == 1
    assert stats["tlb_misses"] == 3
    assert stats["page_faults"] == 3
    assert stats["page_fault_rate"] == 0.75
    assert stats["context_switches"] == 0


def test_event_log_format(tmp_path):
    log = tmp_path / "events.jsonl"
    first = synthetic("loop", n=6, num_pages=3, pid=1)
    second = synthetic("loop", n=6, num_pages=3, pid=2)
    run_simulation(interleave([first, second], quantum=3), frames=2, tlb_size=1,
                   policy="clock", log_path=log)

    lines = [json.loads(line) for line in log.read_text().splitlines()]
    assert lines[0] == {"type": "config", "frames": 2, "tlb_size": 1, "policy": "clock",
                        "tlb_policy": "lru", "asid": False}
    events = lines[1:]
    assert [e["t"] for e in events] == list(range(len(events)))
    assert sum(e["type"] == "switch" for e in events) == 3
    assert sum(e["type"] == "access" for e in events) == 12
    for e in events:
        if e["type"] == "access" and e["tlb_evict"] is not None:
            assert set(e["tlb_evict"]) == {"pid", "vpn"}


def test_context_switches_do_not_count_the_first_process():
    accesses = interleave([synthetic("loop", 10, 2, pid=1), synthetic("loop", 10, 2, pid=2)], 5)
    stats = run_simulation(accesses, frames=4, tlb_size=4)
    assert stats["context_switches"] == 3


def test_opt_works_with_several_processes():
    accesses = interleave([synthetic("random", 200, 8, pid=1), synthetic("loop", 200, 8, pid=2)], 25)
    faults = {p: run_simulation(accesses, frames=4, policy=p)["page_faults"]
              for p in ("fifo", "clock", "lru", "opt")}
    assert faults["opt"] == min(faults.values())


def run_cli(*args):
    return subprocess.run([sys.executable, "-m", "vmsim", *args], cwd=TEAM / "src",
                          capture_output=True, text=True)


def test_command_line_prints_summary():
    result = run_cli("--synthetic", "loop", "--pages", "20", "--n", "5000", "--frames", "8", "--policy", "fifo")
    assert result.returncode == 0
    assert "Total accesses: 5000" in result.stdout
    assert "Page faults: 5000 (100.00%)" in result.stdout


def test_command_line_rejects_bad_input():
    assert run_cli("--synthetic", "loop", "--frames", "0").returncode != 0
    missing = run_cli("--trace", "no_such_file.trace")
    assert missing.returncode != 0
    assert "No such file" in missing.stderr
