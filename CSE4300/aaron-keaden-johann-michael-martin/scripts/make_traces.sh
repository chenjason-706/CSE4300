#!/usr/bin/env bash
set -euo pipefail

# rebuilds the traces in traces/ from the small c programs in scripts/programs/.
# needs linux on x86-64 with gcc and valgrind (it won't work on a mac).
#
#     bash scripts/make_traces.sh

# find the team folder even if we run this from somewhere else.
script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
project_dir="$(dirname -- "$script_dir")"
program_dir="$script_dir/programs"
trace_dir="$project_dir/traces"

for tool in valgrind gcc gzip awk; do
    if ! command -v "$tool" >/dev/null 2>&1; then
        echo "missing required tool: $tool" >&2
        exit 1
    fi
done

mkdir -p "$trace_dir"
work_dir="$(mktemp -d)"
trap 'rm -rf -- "$work_dir"' EXIT

make_trace() {
    local name="$1"

    # build without the c library. a normal program spends its first ~350,000
    # accesses in the dynamic loader and libc startup, so a trace of something
    # like ls never even reaches ls itself unless it's huge.
    gcc -O1 -static -nostdlib -fno-stack-protector \
        -o "$work_dir/$name" "$program_dir/$name.c"

    # keep the full log in a temporary folder.
    valgrind --tool=lackey --trace-mem=yes \
        --log-file="$work_dir/$name.full.trace" \
        "$work_dir/$name" > /dev/null

    # keep only the memory access lines, then gzip so the repo stays small.
    # trace.py reads .gz files directly.
    awk '/^[[:space:]]*[ILSM][[:space:]]/' "$work_dir/$name.full.trace" > "$work_dir/$name.trace"

    if [[ ! -s "$work_dir/$name.trace" ]]; then
        echo "no memory accesses found for $name" >&2
        exit 1
    fi

    gzip -9 -c "$work_dir/$name.trace" > "$trace_dir/$name.trace.gz"
    echo "saved $trace_dir/$name.trace.gz ($(wc -l < "$work_dir/$name.trace") accesses)"
}

make_trace matmul
make_trace sort
make_trace randwalk
