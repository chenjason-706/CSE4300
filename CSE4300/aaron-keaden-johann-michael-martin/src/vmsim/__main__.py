import argparse
from pathlib import Path

from .sim import print_summary, run_simulation
from .trace import interleave, load_lackey, synthetic


def positive_int(value: str) -> int:
    number = int(value)
    if number <= 0:
        raise argparse.ArgumentTypeError("enter a number greater than 0")
    return number


def main() -> None:
    parser = argparse.ArgumentParser(description="virtual memory simulator")
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--trace", action="append", type=Path)
    source.add_argument("--synthetic", choices=("sequential", "random", "loop"))

    parser.add_argument("--pages", type=positive_int, default=20)
    parser.add_argument("--n", type=positive_int, default=5000)
    parser.add_argument("--limit", type=positive_int, default=1_000_000)
    parser.add_argument("--frames", type=positive_int, default=64)
    parser.add_argument("--tlb", type=positive_int, default=16)
    parser.add_argument("--policy", choices=("fifo", "clock", "lru", "opt"), default="clock")
    parser.add_argument("--tlb-policy", choices=("lru", "random"), default="lru")
    parser.add_argument("--quantum", type=positive_int, default=1000)
    parser.add_argument("--asid", action="store_true")
    parser.add_argument("--log", type=Path)
    args = parser.parse_args()

    try:
        if args.trace:
            # each trace gets its own pid so the mmu can tell them apart.
            traces = [
                load_lackey(path, pid, args.limit)
                for pid, path in enumerate(args.trace, start=1)
            ]
            accesses = interleave(traces, args.quantum)
        else:
            accesses = synthetic(args.synthetic, args.n, args.pages)

        stats = run_simulation(
            accesses,
            frames=args.frames,
            tlb_size=args.tlb,
            policy=args.policy,
            tlb_policy=args.tlb_policy,
            asid=args.asid,
            log_path=args.log,
        )
    except (OSError, ValueError) as error:
        parser.error(str(error))

    print_summary(stats)


if __name__ == "__main__":
    main()