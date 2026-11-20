#ifndef METRICS_H
#define METRICS_H

#include "process.h"

typedef struct {
    double avg_waiting;
    double avg_turnaround;
    double avg_response;
} MetricsSummary;

/* Turnaround = finish - arrival */
int metrics_turnaround(const Process *p);

/* Waiting = turnaround - burst */
int metrics_waiting(const Process *p);

/* Response = start - arrival */
int metrics_response(const Process *p);

/* True if every process was scheduled and finished. */
int metrics_complete(const Process procs[], int n);

/* Average waiting / turnaround / response. Returns 0 on success, -1 if incomplete. */
int metrics_summarize(const Process procs[], int n, MetricsSummary *out);

/* Print per-process table and averages. */
void metrics_print(const Process procs[], int n);

#endif /* METRICS_H */
