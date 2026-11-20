# CSE 4300 Group Project: Virtual Memory Simulator

Team members: Aaron, Keaden, Johann, Michael, Martin

This project simulates what the MMU and the operating system do every time a program touches memory. For each memory access we check the TLB, walk a two-level page table if the TLB misses, handle a page fault if the page isn't in memory, and pick a page to kick out (writing it to swap if it's dirty) when there's no free frame.

The input is real memory traces. We ran small C programs under Valgrind's lackey tool, which logs every load and store, and the simulator replays those accesses. It prints stats like TLB hit rate and page fault rate, makes charts comparing different settings, and can write an event log that our web visualizer plays back step by step.

The full write-up is in [docs/design.md](docs/design.md) (PDF copy: [docs/design.pdf](docs/design.pdf)). Our slides are linked in [slides/README.md](slides/README.md).

## Setup

You need Python 3.10 or newer. From this folder:

```bash
python3 -m pip install -r requirements.txt
```

That installs matplotlib (for charts) and pytest (for tests). The simulator itself only uses the Python standard library.

## Running the simulator

Run it from the `src` folder:

```bash
cd src
python3 -m vmsim --trace ../traces/matmul.trace.gz --frames 8 --tlb 16 --policy lru
```

Example output:

```
Total accesses: 613263
TLB hits: 613247 (100.00%)
TLB misses: 16
Page faults: 16 (0.00%)
Swap reads: 4
Swap writes: 6
Context switches: 0
```

To simulate several processes at once, give `--trace` more than once. Each trace becomes its own process, and the simulator switches between them every `--quantum` accesses:

```bash
python3 -m vmsim --trace ../traces/matmul.trace.gz --trace ../traces/sort.trace.gz \
    --trace ../traces/randwalk.trace.gz --frames 16 --policy clock --quantum 500
```

You can also run a made-up trace instead of a real one:

```bash
python3 -m vmsim --synthetic loop --pages 20 --n 5000 --frames 8 --policy fifo
```

### Options

| Option | What it does | Default |
|---|---|---|
| `--trace FILE` | lackey trace to run (plain or `.gz`), repeat for more processes | |
| `--synthetic KIND` | use a made-up trace instead: `sequential`, `random` or `loop` | |
| `--pages`, `--n` | number of pages and accesses for `--synthetic` | 20, 5000 |
| `--limit N` | only use the first N accesses of each trace | 1,000,000 |
| `--frames N` | number of physical frames (shared by all processes) | 64 |
| `--tlb N` | number of TLB entries | 16 |
| `--policy NAME` | page replacement: `fifo`, `clock`, `lru` or `opt` | clock |
| `--tlb-policy NAME` | TLB replacement: `lru` or `random` | lru |
| `--quantum N` | accesses each process gets before a context switch | 1000 |
| `--asid` | keep TLB entries across context switches instead of flushing | off |
| `--log FILE` | write every event to a JSON Lines file for the visualizer | |

## Visualizer

The visualizer is a single web page that replays an event log. It doesn't need a server.

1. Make a small log (keep it to a few hundred accesses or it gets slow to step through):

   ```bash
   cd src
   python3 -m vmsim --trace ../traces/matmul.trace.gz --trace ../traces/sort.trace.gz \
       --limit 150 --quantum 50 --frames 4 --tlb 4 --policy clock --log ../demo.jsonl
   ```

2. Open `visualizer/index.html` in a browser and pick `demo.jsonl` with the file picker.
3. Use Next, Previous, Play and the speed slider to step through it.

Green means a TLB hit, yellow means a TLB miss that the page table handled, and red means a page fault. There's also a small hand-made example in `visualizer/sample.jsonl`.

## Tests

From this folder:

```bash
python3 -m pytest tests
```

There are 89 tests covering the trace parser, simulation driver and command line, page table, MMU, TLB, replacement policies and swap space. Some of them run the replacement policies inside the real MMU and TLB, and one runs a small trace through the whole simulator.

## Experiments

These make every chart in the design doc. Charts go in `experiments/plots/` and the numbers go in `experiments/results/`.

```bash
python3 experiments/run_all.py --trace traces/randwalk.trace.gz --trace traces/matmul.trace.gz --trace traces/sort.trace.gz
python3 experiments/tlb_experiments.py --trace traces/randwalk.trace.gz --trace traces/matmul.trace.gz --trace traces/sort.trace.gz
```

The first one takes about a minute. It compares the four replacement policies on the first trace, checks Belady's anomaly, and runs the TLB size and context switch experiments. The second one compares LRU and random TLB replacement and flushing vs ASIDs.

## Traces

The three traces in `traces/` come from small C programs in `scripts/programs/`:

| Trace | What the program does | Accesses | Pages |
|---|---|---|---|
| `matmul.trace.gz` | multiplies two 40x40 matrices | 613,263 | 12 |
| `sort.trace.gz` | quicksorts 6,000 random numbers | 1,357,392 | 8 |
| `randwalk.trace.gz` | jumps around a 256 KB array at random | 400,017 | 67 |

The programs are built without the C library. Otherwise every trace would start with about 350,000 accesses from libc starting up, and the program itself would barely show up. The traces are gzipped to keep the repo small, and the parser reads them directly.

To rebuild them you need Linux on x86-64 with gcc and valgrind (it won't work on a Mac):

```bash
bash scripts/make_traces.sh
```

## Folder layout

```
README.md                 this file
requirements.txt
docs/design.md            design document (and design.pdf)
src/vmsim/
    __main__.py           command line (python -m vmsim)
    sim.py                runs a trace through the MMU, writes the log, prints stats
    trace.py              reads lackey traces, makes synthetic ones, interleaves processes
    mmu.py                ties everything together for each memory access
    pagetable.py          two-level page tables
    frames.py             physical frame table
    tlb.py                the TLB
    replacement.py        FIFO, Clock, LRU and OPT
    swap.py               swap space
tests/                    pytest tests
traces/                   the three lackey traces
scripts/                  make_traces.sh and the C programs
experiments/              experiment scripts, plots/ and results/
visualizer/index.html     the web visualizer
slides/                   link to our slides
```

## Who did what

| Person | Part |
|---|---|
| Aaron | trace parser, simulation driver, command line, traces |
| Michael | page tables, frame table, MMU |
| Johann | TLB, team test setup, TLB experiments |
| Martin | replacement policies, swap space, experiments |
| Keaden | visualizer, slides |
