#!/usr/bin/env python3
"""smoke tests for phases 1-5: headers, build, load, dispatch stubs, metrics."""

from __future__ import annotations

import os
import subprocess
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
SCHEDULER = os.path.join(ROOT, "scheduler")
DATA = os.path.join(ROOT, "data", "processes1.txt")


def run(cmd, *, expect_ok=True):
    result = subprocess.run(
        cmd,
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    ok = result.returncode == 0
    if expect_ok and not ok:
        raise AssertionError(
            f"Command failed ({result.returncode}): {' '.join(cmd)}\n"
            f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"
        )
    if not expect_ok and ok:
        raise AssertionError(f"Expected failure, but succeeded: {' '.join(cmd)}")
    return result


def test_required_files_exist():
    required = [
        "include/process.h",
        "include/scheduler.h",
        "include/queue.h",
        "include/metrics.h",
        "src/main.c",
        "src/queue.c",
        "src/metrics.c",
        "src/schedulers/fcfs.c",
        "src/schedulers/sjf.c",
        "src/schedulers/rr.c",
        "Makefile",
        "data/processes1.txt",
    ]
    missing = [p for p in required if not os.path.isfile(os.path.join(ROOT, p))]
    assert not missing, f"Missing files: {missing}"


def test_headers_define_expected_api():
    process_h = open(os.path.join(ROOT, "include/process.h"), encoding="utf-8").read()
    scheduler_h = open(os.path.join(ROOT, "include/scheduler.h"), encoding="utf-8").read()
    metrics_h = open(os.path.join(ROOT, "include/metrics.h"), encoding="utf-8").read()

    for field in (
        "pid",
        "arrival_time",
        "burst_time",
        "priority",
        "remaining_time",
        "start_time",
        "finish_time",
    ):
        assert field in process_h, f"process.h missing field: {field}"

    assert "typedef struct" in scheduler_h
    assert "run_fcfs" in scheduler_h
    assert "run_sjf" in scheduler_h
    assert "run_rr" in scheduler_h

    assert "metrics_turnaround" in metrics_h
    assert "metrics_waiting" in metrics_h
    assert "metrics_response" in metrics_h
    assert "metrics_print" in metrics_h


def test_make_builds():
    run(["make", "clean"])
    run(["make"])
    assert os.path.isfile(SCHEDULER), "scheduler binary was not produced"


def test_fcfs_loads_and_dispatches():
    result = run([SCHEDULER, DATA, "fcfs"])
    assert "Loaded 4 process(es)" in result.stdout
    assert "Running scheduler: fcfs" in result.stdout
    assert "[fcfs] stub" in result.stdout
    assert "Metrics unavailable" in result.stdout


def test_sjf_loads_and_dispatches():
    result = run([SCHEDULER, DATA, "sjf"])
    assert "Loaded 4 process(es)" in result.stdout
    assert "Running scheduler: sjf" in result.stdout
    assert "[sjf] stub" in result.stdout
    assert "Metrics unavailable" in result.stdout


def test_rr_requires_quantum_and_dispatches():
    bad = run([SCHEDULER, DATA, "rr"], expect_ok=False)
    assert bad.returncode != 0

    result = run([SCHEDULER, DATA, "rr", "4"])
    assert "Loaded 4 process(es)" in result.stdout
    assert "Running scheduler: rr (quantum=4)" in result.stdout
    assert "[rr] stub" in result.stdout
    assert "Metrics unavailable" in result.stdout


def test_unknown_scheduler_fails():
    result = run([SCHEDULER, DATA, "nope"], expect_ok=False)
    assert result.returncode != 0
    assert "Unknown scheduler" in result.stderr


def test_metrics_unit():
    run([
        "gcc",
        "-Wall",
        "-Wextra",
        "-Iinclude",
        "-o",
        "test_metrics",
        "src/metrics.c",
        "tests/test_metrics.c",
    ])
    result = run([os.path.join(ROOT, "test_metrics")])
    assert "Metrics tests passed" in result.stdout
    os.remove(os.path.join(ROOT, "test_metrics"))


def main():
    tests = [
        test_required_files_exist,
        test_headers_define_expected_api,
        test_make_builds,
        test_fcfs_loads_and_dispatches,
        test_sjf_loads_and_dispatches,
        test_rr_requires_quantum_and_dispatches,
        test_unknown_scheduler_fails,
        test_metrics_unit,
    ]

    failed = 0
    for test in tests:
        name = test.__name__
        try:
            test()
            print(f"PASS  {name}")
        except Exception as exc:
            failed += 1
            print(f"FAIL  {name}: {exc}")

    print()
    if failed:
        print(f"{failed}/{len(tests)} tests failed")
        return 1

    print(f"All {len(tests)} phase 1-5 smoke tests passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
