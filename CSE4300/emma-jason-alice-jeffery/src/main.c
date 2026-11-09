#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "../include/scheduler.h"

#define MAX_PROCESSES 128

static void usage(const char *prog)
{
    fprintf(stderr, "Usage: %s <datafile> <fcfs|sjf|rr> [quantum]\n", prog);
    fprintf(stderr, "Example: %s data/processes1.txt rr 4\n", prog);
}

static int load_processes(const char *path, Process procs[], int max_n)
{
    FILE *fp = fopen(path, "r");
    if (!fp) {
        perror(path);
        return -1;
    }

    char line[256];
    int n = 0;

    while (fgets(line, sizeof(line), fp) != NULL) {
        if (line[0] == '#' || line[0] == '\n' || line[0] == '\0') {
            continue;
        }

        if (n >= max_n) {
            fprintf(stderr, "Too many processes (max %d)\n", max_n);
            fclose(fp);
            return -1;
        }

        Process *p = &procs[n];
        if (sscanf(line, "%d %d %d %d",
                   &p->pid,
                   &p->arrival_time,
                   &p->burst_time,
                   &p->priority) != 4) {
            fprintf(stderr, "Bad line in %s: %s", path, line);
            fclose(fp);
            return -1;
        }

        p->remaining_time = p->burst_time;
        p->start_time = -1;
        p->finish_time = 0;
        n++;
    }

    fclose(fp);
    return n;
}

static const Scheduler *find_scheduler(const char *name)
{
    static const Scheduler table[] = {
        {"fcfs", run_fcfs},
        {"sjf",  run_sjf},
        {"rr",   run_rr},
    };

    size_t i;
    for (i = 0; i < sizeof(table) / sizeof(table[0]); i++) {
        if (strcmp(table[i].name, name) == 0) {
            return &table[i];
        }
    }
    return NULL;
}

static void print_processes(const Process procs[], int n)
{
    int i;

    printf("Loaded %d process(es):\n", n);
    printf("  PID  Arrival  Burst  Priority\n");
    for (i = 0; i < n; i++) {
        printf("  %-4d %-8d %-6d %-8d\n",
               procs[i].pid,
               procs[i].arrival_time,
               procs[i].burst_time,
               procs[i].priority);
    }
}

int main(int argc, char *argv[])
{
    Process procs[MAX_PROCESSES];
    int n;
    int quantum = 0;
    const Scheduler *sched;

    if (argc < 3 || argc > 4) {
        usage(argv[0]);
        return 1;
    }

    sched = find_scheduler(argv[2]);
    if (!sched) {
        fprintf(stderr, "Unknown scheduler: %s\n", argv[2]);
        usage(argv[0]);
        return 1;
    }

    if (argc == 4) {
        quantum = atoi(argv[3]);
        if (quantum <= 0) {
            fprintf(stderr, "Quantum must be a positive integer\n");
            return 1;
        }
    } else if (strcmp(argv[2], "rr") == 0) {
        fprintf(stderr, "Round Robin requires a quantum\n");
        usage(argv[0]);
        return 1;
    }

    n = load_processes(argv[1], procs, MAX_PROCESSES);
    if (n < 0) {
        return 1;
    }
    if (n == 0) {
        fprintf(stderr, "No processes found in %s\n", argv[1]);
        return 1;
    }

    print_processes(procs, n);
    printf("\nRunning scheduler: %s", sched->name);
    if (strcmp(sched->name, "rr") == 0) {
        printf(" (quantum=%d)", quantum);
    }
    printf("\n");

    sched->run(procs, n, quantum);

    return 0;
}
