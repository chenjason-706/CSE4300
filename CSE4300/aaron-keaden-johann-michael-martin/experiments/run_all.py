"""Run repeatable experiments using the team's real MMU and trace parser.

From the team folder: python experiments/run_all.py --trace traces/ls.trace
"""

import argparse
import csv
import random
from dataclasses import dataclass
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from vmsim.mmu import MMU
from vmsim.replacement import make_policy
from vmsim.swap import SwapSpace
from vmsim.tlb import TLB

POLICIES = ("fifo", "clock", "lru", "opt")


@dataclass(frozen=True)
class SyntheticAccess:
    """Access record for synthetic experiments without the trace parser."""
    pid: int
    op: str
    vaddr: int


def synthetic_workload(pid: int, n: int, seed: int = 4300):
    """90% of references target 12 hot pages; the rest target 116 cold pages."""
    rng = random.Random(seed + pid)
    accesses = []
    for _ in range(n):
        vpn = rng.randrange(12) if rng.random() < 0.9 else rng.randrange(12, 128)
        op = "W" if rng.random() < 0.2 else "R"
        accesses.append(SyntheticAccess(pid, op, vpn << 12))
    return accesses


def synthetic_interleave(traces, quantum):
    """Round-robin chunks of synthetic process traces."""
    return [access for start in range(0, max(map(len, traces)), quantum)
            for trace in traces for access in trace[start:start + quantum]]


def simulate(accesses, frames, tlb_size, policy_name, asid=False):
    """Create a fresh simulator for one configuration and collect events."""
    future = [(a.pid, a.vaddr >> 12) for a in accesses] if policy_name == "opt" else None
    swap = SwapSpace()
    tlb = TLB(tlb_size, policy="lru", use_asid=asid)
    mmu = MMU(frames, tlb, make_policy(policy_name, frames, future), swap)
    hits = faults = switches = 0
    previous_pid = None
    for access in accesses:
        if access.pid != previous_pid:
            mmu.context_switch(access.pid)
            if previous_pid is not None:
                switches += 1
            previous_pid = access.pid
        event = mmu.access(access)
        if event["tlb"] not in ("hit", "miss") or event["pt"] not in (None, "hit", "fault"):
            raise ValueError(f"Unexpected MMU event: {event}")
        hits += event["tlb"] == "hit"
        faults += event["pt"] == "fault"
    n = len(accesses)
    if n == 0:
        raise ValueError("Empty trace")
    return {
        "accesses": n, "tlb_hits": hits, "tlb_misses": n - hits,
        "tlb_hit_rate_pct": 100 * hits / n, "page_faults": faults,
        "fault_rate_pct": 100 * faults / n, "swap_reads": swap.stats["reads"],
        "swap_writes": swap.stats["writes"], "context_switches": switches,
    }


def record(rows, experiment, workload, accesses, frames, tlb_size, policy, asid=False, quantum=None):
    result = {
        "experiment": experiment, "workload": workload, "frames": frames,
        "tlb_size": tlb_size, "policy": policy, "asid": asid, "quantum": quantum,
        **simulate(accesses, frames, tlb_size, policy, asid),
    }
    rows.append(result)
    print(f"{experiment}: {policy}, {frames} frames, TLB {tlb_size}, ASID {asid}, quantum {quantum}: "
          f"{result['page_faults']} faults, {result['tlb_hit_rate_pct']:.1f}% TLB hits")
    return result


def save_lines(path, series, xlabel, ylabel, title, log_x=False):
    fig, ax = plt.subplots(figsize=(8, 4.8), layout="constrained")
    for label, x, y in series:
        ax.plot(x, y, marker="o", label=label)
    ax.set(xlabel=xlabel, ylabel=ylabel, title=title)
    ax.grid(alpha=0.25)
    if log_x:
        xs = sorted({value for _, x, _ in series for value in x})
        ax.set_xscale("log", base=2)
        ax.set_xticks(xs, [str(value) for value in xs])
    # Let the y-axis fit the data. Real fault rates are only a few percent,
    # so a fixed 0-100% axis made every line look flat.
    ax.set_ylim(bottom=0)
    if len(series) > 1:
        ax.legend()
    fig.savefig(path, dpi=180)
    plt.close(fig)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--trace", type=Path, action="append", help="Small lackey trace; repeat for multiple processes")
    parser.add_argument("--synthetic", action="store_true", help="Run explicitly synthetic workloads without trace.py")
    parser.add_argument("--limit", type=int, default=1_000_000, help="Maximum accesses per real trace (the first ~20k are mostly program startup)")
    parser.add_argument("--output", type=Path, default=ROOT / "experiments")
    args = parser.parse_args()
    if args.limit <= 0:
        parser.error("--limit must be positive")
    plots = args.output / "plots"
    results = args.output / "results"
    plots.mkdir(parents=True, exist_ok=True)
    results.mkdir(parents=True, exist_ok=True)
    if args.synthetic:
        if args.trace:
            parser.error("Choose either --synthetic or --trace")
        paths = [Path(f"synthetic_pid{i}.trace") for i in range(3)]
        traces = [synthetic_workload(i, args.limit) for i in range(3)]
        interleave = synthetic_interleave
        Access = SyntheticAccess
    else:
        paths = args.trace or sorted((ROOT / "traces").glob("*.trace"))
        if not paths:
            parser.error("No real trace found. Supply --trace PATH or explicitly use --synthetic.")
        try:
            from vmsim.trace import Access, interleave, load_lackey
        except ImportError as exc:
            parser.error(f"Real traces require the team's trace.py: {exc}")
        traces = [load_lackey(path, pid=pid, limit=args.limit) for pid, path in enumerate(paths)]
    for path, trace in zip(paths, traces):
        if not trace:
            parser.error(f"No accesses parsed from {path}")
    rows = []

    # Use the exact same ordered trace for all replacement policies.
    workload = traces[0]
    label = "Synthetic hot/cold workload" if args.synthetic else paths[0].name
    frame_counts = [4, 8, 16, 32, 64, 128]
    series = []
    for policy in POLICIES:
        rates = [record(rows, "replacement", label, workload, frames, 16, policy)["fault_rate_pct"]
                 for frames in frame_counts]
        series.append((policy.upper(), frame_counts, rates))
    save_lines(plots / "fault_rate_vs_frames.png", series, "Physical frames", "Page-fault rate (%)",
               f"Replacement policies — {label}", log_x=True)

    # Classic reference string: known FIFO anomaly, not a real trace.
    belady = [Access(pid=0, op="R", vaddr=vpn << 12) for vpn in (1, 2, 3, 4, 1, 2, 5, 1, 2, 3, 4, 5)]
    counts = [record(rows, "belady", "classic reference string", belady, frames, 2, "fifo")["page_faults"]
              for frames in (3, 4)]
    if counts != [9, 10]:
        raise RuntimeError(f"Expected Belady counts [9, 10]; got {counts}")
    fig, ax = plt.subplots(figsize=(6, 4), layout="constrained")
    bars = ax.bar(["3 frames", "4 frames"], counts)
    ax.bar_label(bars)
    ax.set(ylabel="Page faults", title="Belady's anomaly — FIFO", ylim=(0, 12))
    fig.savefig(plots / "belady_anomaly.png", dpi=180)
    plt.close(fig)

    # Johann's TLB size comparison, holding the physical memory fixed.
    sizes = [4, 8, 16, 32, 64]
    rates = [record(rows, "tlb_size", label, workload, 128, size, "lru")["tlb_hit_rate_pct"] for size in sizes]
    save_lines(plots / "tlb_hit_rate_vs_size.png", [("LRU", sizes, rates)], "TLB entries", "TLB hit rate (%)", f"TLB size — {label}", log_x=True)

    # If only one trace is supplied, model two separate processes running it.
    if len(traces) == 1:
        second = [Access(pid=1, op=a.op, vaddr=a.vaddr) for a in workload]
        multi_traces = [workload, second]
        multi_label = f"two process copies of {label}"
    else:
        multi_traces = traces
        multi_label = ", ".join(path.name for path in paths)
    quantums = [10, 50, 100, 500, 1000]
    series = []
    for asid in (False, True):
        rates = [record(rows, "context_switch", multi_label, interleave(multi_traces, quantum), 128, 32, "lru", asid, quantum)["tlb_hit_rate_pct"]
                 for quantum in quantums]
        series.append(("ASIDs" if asid else "Flush on switch", quantums, rates))
    save_lines(plots / "tlb_context_switch.png", series, "Accesses per quantum", "TLB hit rate (%)", f"Context switches — {multi_label}", log_x=True)

    # Aaron's locality chart. A point represents one logged memory access.
    for i, (path, trace) in enumerate(zip(paths, traces)):
        # The stack sits at a huge address far from the code and data, so plotting
        # raw page numbers squashes everything into one line. Number the pages the
        # program touched in address order instead (0 = lowest page).
        pages = sorted({a.vaddr >> 12 for a in trace})
        rank = {page: i for i, page in enumerate(pages)}
        fig, ax = plt.subplots(figsize=(8, 4.8), layout="constrained")
        ax.scatter(range(len(trace)), [rank[a.vaddr >> 12] for a in trace], s=2, alpha=0.5)
        ax.set(xlabel="Access index", ylabel="Page (numbered in address order)",
               title=f"Memory locality — {path.name} ({len(pages)} pages)")
        name = path.name.split(".")[0]
        fig.savefig(plots / f"locality_{i}_{name}.png", dpi=180)
        plt.close(fig)

    with (results / "results.csv").open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    print(f"Saved {len(rows)} experiment configurations in {results / 'results.csv'}")
    print(f"Charts: {plots}")


if __name__ == "__main__":
    main()
