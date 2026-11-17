#include <stdio.h>

#include "../../include/queue.h"
#include "../../include/scheduler.h"

/*
 * Non-preemptive priority scheduling.
 * Lower priority number = higher importance (matches queue_take_highest_priority).
 * Once a job starts, it runs to completion. Equal priorities keep ready-queue
 * order (earlier arrival after sorting).
 */
static void sort_by_arrival(Process procs[], int n)
{
    int i;

    for (i = 1; i < n; i++) {
        Process key = procs[i];
        int j = i - 1;

        while (j >= 0 && procs[j].arrival_time > key.arrival_time) {
            procs[j + 1] = procs[j];
            j--;
        }
        procs[j + 1] = key;
    }
}

static void admit_arrivals(Process procs[], int n, int admitted[],
                           Queue *ready, int clock)
{
    int i;

    for (i = 0; i < n; i++) {
        if (!admitted[i] && procs[i].arrival_time <= clock) {
            admitted[i] = 1;
            queue_enqueue(ready, &procs[i]);
        }
    }
}

static int next_unadmitted(Process procs[], int n, const int admitted[])
{
    int i;
    int next = -1;

    for (i = 0; i < n; i++) {
        if (!admitted[i] &&
            (next == -1 || procs[i].arrival_time < procs[next].arrival_time)) {
            next = i;
        }
    }
    return next;
}

void run_priority(Process procs[], int n, int quantum)
{
    Queue ready;
    int admitted[n];
    int clock = 0;
    int completed = 0;
    int i;

    (void)quantum;

    if (n <= 0) {
        return;
    }

    sort_by_arrival(procs, n);

    if (queue_init(&ready, n) != 0) {
        fprintf(stderr, "[priority] failed to init ready queue\n");
        return;
    }

    for (i = 0; i < n; i++) {
        admitted[i] = 0;
    }

    admit_arrivals(procs, n, admitted, &ready, clock);

    while (completed < n) {
        Process *p;

        if (queue_is_empty(&ready)) {
            int next = next_unadmitted(procs, n, admitted);

            if (next < 0) {
                break;
            }
            clock = procs[next].arrival_time;
            admit_arrivals(procs, n, admitted, &ready, clock);
            continue;
        }

        p = queue_take_highest_priority(&ready);
        p->start_time = clock;
        clock += p->burst_time;
        p->remaining_time = 0;
        p->finish_time = clock;
        completed++;

        admit_arrivals(procs, n, admitted, &ready, clock);
    }

    queue_destroy(&ready);
}
