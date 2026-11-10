#include <stdio.h>

#include "../include/metrics.h"

int metrics_turnaround(const Process *p)
{
    return p->finish_time - p->arrival_time;
}

int metrics_waiting(const Process *p)
{
    return metrics_turnaround(p) - p->burst_time;
}

int metrics_response(const Process *p)
{
    return p->start_time - p->arrival_time;
}

int metrics_complete(const Process procs[], int n)
{
    int i;

    for (i = 0; i < n; i++) {
        if (procs[i].start_time < 0 || procs[i].remaining_time != 0) {
            return 0;
        }
    }
    return 1;
}

void metrics_print(const Process procs[], int n)
{
    int i;
    double sum_turnaround = 0.0;
    double sum_waiting = 0.0;
    double sum_response = 0.0;

    if (n <= 0) {
        printf("No processes to report metrics for.\n");
        return;
    }

    if (!metrics_complete(procs, n)) {
        printf("Metrics unavailable: scheduler did not finish all processes.\n");
        return;
    }

    printf("\n");
    printf("PID  Arrival  Burst  Start  Finish  Turnaround  Waiting  Response\n");
    printf("---  -------  -----  -----  ------  -----------  -------  --------\n");

    for (i = 0; i < n; i++) {
        const Process *p = &procs[i];
        int turnaround = metrics_turnaround(p);
        int waiting = metrics_waiting(p);
        int response = metrics_response(p);

        sum_turnaround += turnaround;
        sum_waiting += waiting;
        sum_response += response;

        printf("%-4d %-8d %-6d %-6d %-7d %-12d %-8d %-8d\n",
               p->pid,
               p->arrival_time,
               p->burst_time,
               p->start_time,
               p->finish_time,
               turnaround,
               waiting,
               response);
    }

    printf("\nAverages:\n");
    printf("  Turnaround: %.2f\n", sum_turnaround / n);
    printf("  Waiting:    %.2f\n", sum_waiting / n);
    printf("  Response:   %.2f\n", sum_response / n);
}
