# CPU Scheduler Simulator
A program that simulates CPU scheduling algorithms on a list of jobs loaded from a text file. Algorithms share one function signature so `main.c` can choose which to run at runtime.

```text
./scheduler <datafile> <fcfs|sjf|rr|priority|compare> [quantum]
```

Examples:

```bash
make
./scheduler data/processes1.txt fcfs
./scheduler data/processes1.txt sjf
./scheduler data/processes1.txt rr 4
./scheduler data/processes1.txt priority
```

Compare all algorithms and plot a chart:

```bash
./scheduler data/processes1.txt compare 4
python3 scripts/plot_compare.py build/compare.csv
# or in one step:
make compare
```

`compare` runs FCFS, SJF, RR, and Priority on the same input, prints a side-by-side averages table, writes `build/compare.csv`, and the plot script writes `build/compare.svg`. If no quantum is given for `compare`, RR uses quantum **4**.

Run tests:

```bash
make test
# or
python3 tests/run_tests.py
```

---

## Project layout

```text
emma-jason-alice-jeffery/
├── Makefile
├── README.md
├── include/
│   ├── process.h       # Process (job) struct
│   ├── scheduler.h     # shared scheduler interface
│   ├── queue.h         # ready-queue helpers
│   └── metrics.h       # waiting / turnaround / response + summarize
├── src/
│   ├── main.c          # args, load file, dispatch, compare mode
│   ├── queue.c
│   ├── metrics.c
│   └── schedulers/
│       ├── fcfs.c
│       ├── sjf.c
│       ├── rr.c
│       └── priority.c
├── scripts/
│   └── plot_compare.py # CSV → SVG comparison chart
├── data/
│   └── processes1.txt
├── tests/
│   ├── run_tests.py
│   ├── test_queue.c
│   └── test_metrics.c
└── build/
    ├── compare.csv
    └── compare.svg
```

---

## Supported algorithms

| CLI name | Algorithm | Behavior |
| --- | --- | --- |
| `fcfs` | First-Come, First-Served | Run jobs in arrival order to completion |
| `sjf` | Shortest Job First | Non-preemptive; among ready jobs, pick shortest burst |
| `rr` | Round Robin | Ready queue + time quantum (required); preempt and re-enqueue |
| `priority` | Priority | Non-preemptive; among ready jobs, pick highest priority |
| `compare` | All of the above | Run each algo on a fresh copy of the jobs; table + CSV |

**Priority convention:** a lower `priority` number means higher importance (same rule as `queue_take_highest_priority`). Quantum is required for `rr`, optional for `compare` (defaults to 4), ignored by the others.

---

## Input format

```text
# pid arrival burst priority
1 0 8 2
2 1 4 1
3 2 9 3
4 3 5 2
```

On load, `remaining_time` is set to `burst_time` and `start_time` is set to `-1`.

---

## Design

**Shared interface** (`include/scheduler.h`):

```c
typedef struct {
    const char *name;
    void (*run)(Process procs[], int n, int quantum);
} Scheduler;
```

Every algorithm implements `void run_*(Process procs[], int n, int quantum)`.

**Ready queue** (`queue.h` / `queue.c`): used by Round Robin (`enqueue` / `dequeue`) and Priority (`queue_take_highest_priority`).

**Metrics** (after a run fills `start_time` / `finish_time`):

- Turnaround = finish − arrival  
- Waiting = turnaround − burst  
- Response = start − arrival  

---

## Phases

### Phase 1 — Process data model 
`include/process.h` — PCB-like job fields including `priority`.

### Phase 2 — Shared scheduler interface 
`include/scheduler.h` — `Scheduler` + `run_fcfs` / `run_sjf` / `run_rr` / `run_priority`.

### Phase 3 — Build plumbing 
Makefile, sample data, `main.c` load/dispatch.

### Phase 4 — Ready queue 
`queue.h` / `queue.c` with enqueue, dequeue, shortest, and highest-priority helpers.

### Phase 5 — Metrics 
`metrics.h` / `metrics.c` — per-process table and averages.

### Phase 6 — Scheduling algorithms 
FCFS, non-preemptive SJF, Round Robin, and non-preemptive Priority Scheduling.

### Phase 7 — Tests, compare mode, and charts
Automated checks plus cross-algorithm evaluation:
- `make test`: queue/metrics unit tests and `tests/run_tests.py` (CLI, expected times, edge cases, compare mode)
- `compare` mode: `./scheduler <datafile> compare [quantum]` runs FCFS, SJF, RR, and Priority on fresh copies of the same jobs
- Prints a side-by-side averages table (waiting, turnaround, response)
- Writes `build/compare.csv`
- `scripts/plot_compare.py` turns that CSV into `build/compare.svg` (grouped bar chart; no extra Python packages)
- Shortcut: `make compare` runs the comparison and plot on `data/processes1.txt` with quantum 4

---

## Status summary

| Phase | Status |
| --- | --- |
| 1 Process model | Done |
| 2 Scheduler interface | Done |
| 3 Makefile, main, data | Done |
| 4 Ready queue | Done |
| 5 Metrics | Done |
| 6 Algorithms (FCFS / SJF / RR / Priority) | Done |
| 7 Tests + compare/chart | Done |
