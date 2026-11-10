#include <assert.h>
#include <stdio.h>

#include "../include/metrics.h"

int main(void)
{
    Process procs[] = {
        {
            .pid = 1,
            .arrival_time = 0,
            .burst_time = 8,
            .priority = 2,
            .remaining_time = 0,
            .start_time = 0,
            .finish_time = 8,
        },
        {
            .pid = 2,
            .arrival_time = 1,
            .burst_time = 4,
            .priority = 1,
            .remaining_time = 0,
            .start_time = 8,
            .finish_time = 12,
        },
    };

    assert(metrics_turnaround(&procs[0]) == 8);
    assert(metrics_waiting(&procs[0]) == 0);
    assert(metrics_response(&procs[0]) == 0);

    assert(metrics_turnaround(&procs[1]) == 11);
    assert(metrics_waiting(&procs[1]) == 7);
    assert(metrics_response(&procs[1]) == 7);

    assert(metrics_complete(procs, 2) == 1);

    procs[1].remaining_time = 1;
    assert(metrics_complete(procs, 2) == 0);
    procs[1].remaining_time = 0;
    procs[1].start_time = -1;
    assert(metrics_complete(procs, 2) == 0);

    puts("Metrics tests passed");
    return 0;
}
