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

int metrics_summarize(const Process procs[], int n, MetricsSummary *out)
{
    int i;
    double sum_turnaround = 0.0;
    double sum_waiting = 0.0;
    double sum_response = 0.0;

    if (out == NULL || n <= 0 || !metrics_complete(procs, n)) {
        return -1;
    }

    for (i = 0; i < n; i++) {
        sum_turnaround += metrics_turnaround(&procs[i]);
        sum_waiting += metrics_waiting(&procs[i]);
        sum_response += metrics_response(&procs[i]);
    }

    out->avg_turnaround = sum_turnaround / n;
    out->avg_waiting = sum_waiting / n;
    out->avg_response = sum_response / n;
    return 0;
}

void metrics_print(const Process procs[], int n)
{
    int i;
    MetricsSummary summary;

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

    if (metrics_summarize(procs, n, &summary) != 0) {
        return;
    }

    printf("\nAverages:\n");
    printf("  Turnaround: %.2f\n", summary.avg_turnaround);
    printf("  Waiting:    %.2f\n", summary.avg_waiting);
    printf("  Response:   %.2f\n", summary.avg_response);
}
