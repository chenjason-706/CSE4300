#ifndef SCHEDULER_H
#define SCHEDULER_H

#include "process.h"

typedef struct {
    const char *name;
    void (*run)(Process procs[], int n, int quantum);
} Scheduler;

void run_fcfs(Process procs[], int n, int quantum);
void run_sjf(Process procs[], int n, int quantum);
void run_rr(Process procs[], int n, int quantum);

#endif 
