#ifndef METRICS_H
#define METRICS_H

#include "process.h"

/* turnaround = finish - arrival */
int metrics_turnaround(const Process *p);

/* waiting = turnaround - burst */
int metrics_waiting(const Process *p);

/* response = start - arrival */
int metrics_response(const Process *p);

/* true if every process was scheduled and finished. */
int metrics_complete(const Process procs[], int n);

/* print per-process table and averages, no-op message if incomplete. */
void metrics_print(const Process procs[], int n);

#endif
