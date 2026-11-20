from __future__ import annotations

import argparse
import csv
import random
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from vmsim.tlb import TLB

PAGE_SHIFT = 12
SIZES = [2, 4, 8, 16, 32, 64, 128]
QUANTA = [10, 50, 100, 500, 1000, 5000, 10000]


def synthetic_streams(num_procs: int = 3, n: int = 60_000, seed: int = 1) -> list[list[int]]:
    rng = random.Random(seed)
    streams = []
    for p in range(num_procs):
        base = 1000 * (p + 1)
        hot_start = 0
        vpns = []
        for i in range(n):
            if i % 2000 == 0:
                hot_start = rng.randrange(0, 200)
            if rng.random() < 0.9:
                vpns.append(base + hot_start + rng.randrange(12))
            else:
                vpns.append(base + rng.randrange(400))
        streams.append(vpns)
    return streams


def trace_streams(paths: list[str], limit: int) -> list[list[int]]:
    from vmsim.trace import load_lackey

    return [[a.vaddr >> PAGE_SHIFT for a in load_lackey(path, pid, limit)]
            for pid, path in enumerate(paths, start=1)]


def round_robin(streams: list[list[int]], quantum: int) -> list[tuple[int, int]]:
    out = []
    pos = [0] * len(streams)
    while any(pos[i] < len(s) for i, s in enumerate(streams)):
        for pid, s in enumerate(streams, start=1):
            chunk = s[pos[pid - 1]: pos[pid - 1] + quantum]
            out.extend((pid, vpn) for vpn in chunk)
            pos[pid - 1] += quantum
    return out


def run(accesses: list[tuple[int, int]], size: int, use_asid: bool, policy: str = "lru") -> float:
    tlb = TLB(size=size, policy=policy, use_asid=use_asid)
    for pid, vpn in accesses:
        tlb.context_switch(pid)
        if tlb.lookup(pid, vpn) is None:
            tlb.insert(pid, vpn, frame=0)
    return tlb.hit_rate


def main() -> None:
    ap = argparse.ArgumentParser(description="TLB experiments: hit rate vs size, and flushing vs ASIDs")
    ap.add_argument("--trace", action="append", help="lackey trace file (repeat for more processes)")
    ap.add_argument("--limit", type=int, default=1_000_000, help="max accesses per trace")
    ap.add_argument("--quantum", type=int, default=1000, help="quantum used for the size sweep")
    ap.add_argument("--asid-size", type=int, default=64, help="TLB size used for the flush vs ASID sweep")
    args = ap.parse_args()

    streams = trace_streams(args.trace, args.limit) if args.trace else synthetic_streams()
    workload = "lackey traces" if args.trace else "synthetic workload"

    plots = ROOT / "experiments" / "plots"
    results = ROOT / "experiments" / "results"
    plots.mkdir(parents=True, exist_ok=True)
    results.mkdir(parents=True, exist_ok=True)

    accesses = round_robin(streams, args.quantum)
    size_rows = []
    for policy in ("lru", "random"):
        for size in SIZES:
            size_rows.append((policy, size, run(accesses, size, use_asid=False, policy=policy)))

    plt.figure(figsize=(6, 4))
    for policy in ("lru", "random"):
        xs = [s for p, s, _ in size_rows if p == policy]
        ys = [100 * h for p, _, h in size_rows if p == policy]
        plt.plot(xs, ys, marker="o", label=policy.upper() if policy == "lru" else "Random")
    plt.xscale("log", base=2)
    plt.xticks(SIZES, [str(s) for s in SIZES])
    plt.xlabel("TLB size (entries)")
    plt.ylabel("TLB hit rate (%)")
    plt.title(f"TLB hit rate vs size ({workload})")
    plt.grid(alpha=0.3)
    plt.legend()
    plt.tight_layout()
    plt.savefig(plots / "tlb_size_lru_vs_random.png", dpi=150)
    plt.close()

    asid_rows = []
    for q in QUANTA:
        acc = round_robin(streams, q)
        asid_rows.append((q, run(acc, args.asid_size, False), run(acc, args.asid_size, True)))

    plt.figure(figsize=(6, 4))
    plt.plot([q for q, _, _ in asid_rows], [100 * f for _, f, _ in asid_rows], marker="o", label="Flush on switch")
    plt.plot([q for q, _, _ in asid_rows], [100 * a for _, _, a in asid_rows], marker="s", label="ASIDs")
    plt.xscale("log")
    plt.xlabel("Accesses between context switches (quantum)")
    plt.ylabel("TLB hit rate (%)")
    plt.title(f"Flushing vs ASIDs, {args.asid_size}-entry TLB")
    plt.grid(alpha=0.3)
    plt.legend()
    plt.tight_layout()
    plt.savefig(plots / "tlb_flush_vs_asid.png", dpi=150)
    plt.close()

    with open(results / "tlb_results.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["experiment", "policy_or_quantum", "size", "hit_rate_flush", "hit_rate_asid"])
        for policy, size, h in size_rows:
            w.writerow(["size_sweep", policy, size, f"{h:.4f}", ""])
        for q, fl, asid in asid_rows:
            w.writerow(["asid_sweep", q, args.asid_size, f"{fl:.4f}", f"{asid:.4f}"])

    print("TLB size sweep (LRU, flushing):")
    for policy, size, h in size_rows:
        if policy == "lru":
            print(f"  {size:>4} entries: {100 * h:5.1f}%")
    print(f"\nFlush vs ASID ({args.asid_size} entries):")
    for q, fl, asid in asid_rows:
        print(f"  quantum {q:>6}: flush {100 * fl:5.1f}%   asid {100 * asid:5.1f}%")
    print(f"\nCharts saved to {plots}")


if __name__ == "__main__":
    main()
