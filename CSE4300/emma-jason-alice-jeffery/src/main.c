#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>

#include "../include/metrics.h"
#include "../include/scheduler.h"

#define MAX_PROCESSES 128
#define COMPARE_CSV_PATH "build/compare.csv"
#define DEFAULT_COMPARE_QUANTUM 4

typedef struct {
    const char *name;
    MetricsSummary summary;
} CompareResult;

static void usage(const char *prog)
{
    fprintf(stderr, "Usage: %s <datafile> <fcfs|sjf|rr|priority|compare> [quantum]\n", prog);
    fprintf(stderr, "Example: %s data/processes1.txt rr 4\n", prog);
    fprintf(stderr, "Compare: %s data/processes1.txt compare 4\n", prog);
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
        {"fcfs",     run_fcfs},
        {"sjf",      run_sjf},
        {"rr",       run_rr},
        {"priority", run_priority},
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

static int ensure_build_dir(void)
{
    struct stat st;

    if (stat("build", &st) == 0) {
        if (S_ISDIR(st.st_mode)) {
            return 0;
        }
        fprintf(stderr, "build exists but is not a directory\n");
        return -1;
    }
    if (mkdir("build", 0755) != 0) {
        perror("mkdir build");
        return -1;
    }
    return 0;
}

static int write_compare_csv(const CompareResult results[], int count)
{
    FILE *fp;
    int i;

    if (ensure_build_dir() != 0) {
        return -1;
    }

    fp = fopen(COMPARE_CSV_PATH, "w");
    if (!fp) {
        perror(COMPARE_CSV_PATH);
        return -1;
    }

    fprintf(fp, "algorithm,avg_waiting,avg_turnaround,avg_response\n");
    for (i = 0; i < count; i++) {
        fprintf(fp, "%s,%.2f,%.2f,%.2f\n",
                results[i].name,
                results[i].summary.avg_waiting,
                results[i].summary.avg_turnaround,
                results[i].summary.avg_response);
    }

    fclose(fp);
    return 0;
}

static void print_compare_table(const CompareResult results[], int count, int quantum)
{
    int i;

    printf("\nComparison (RR quantum=%d)\n", quantum);
    printf("%-10s  %12s  %14s  %12s\n",
           "Algorithm", "Avg waiting", "Avg turnaround", "Avg response");
    printf("%-10s  %12s  %14s  %12s\n",
           "----------", "------------", "--------------", "------------");

    for (i = 0; i < count; i++) {
        printf("%-10s  %12.2f  %14.2f  %12.2f\n",
               results[i].name,
               results[i].summary.avg_waiting,
               results[i].summary.avg_turnaround,
               results[i].summary.avg_response);
    }
}

static int run_compare(const Process base[], int n, int quantum)
{
    static const Scheduler algos[] = {
        {"fcfs",     run_fcfs},
        {"sjf",      run_sjf},
        {"rr",       run_rr},
        {"priority", run_priority},
    };
    CompareResult results[sizeof(algos) / sizeof(algos[0])];
    size_t i;
    int count = (int)(sizeof(algos) / sizeof(algos[0]));

    printf("\nRunning comparison across %d algorithms (RR quantum=%d)\n",
           count, quantum);

    for (i = 0; i < sizeof(algos) / sizeof(algos[0]); i++) {
        Process copy[MAX_PROCESSES];

        memcpy(copy, base, (size_t)n * sizeof(Process));
        algos[i].run(copy, n, quantum);

        results[i].name = algos[i].name;
        if (metrics_summarize(copy, n, &results[i].summary) != 0) {
            fprintf(stderr, "Failed to summarize metrics for %s\n", algos[i].name);
            return 1;
        }
    }

    print_compare_table(results, count, quantum);

    if (write_compare_csv(results, count) != 0) {
        return 1;
    }

    printf("\nWrote %s\n", COMPARE_CSV_PATH);
    printf("Chart: python3 scripts/plot_compare.py %s\n", COMPARE_CSV_PATH);
    return 0;
}

int main(int argc, char *argv[])
{
    Process procs[MAX_PROCESSES];
    int n;
    int quantum = 0;
    int is_compare;

    if (argc < 3 || argc > 4) {
        usage(argv[0]);
        return 1;
    }

    is_compare = strcmp(argv[2], "compare") == 0;

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
    } else if (is_compare) {
        quantum = DEFAULT_COMPARE_QUANTUM;
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

    if (is_compare) {
        return run_compare(procs, n, quantum);
    }

    {
        const Scheduler *sched = find_scheduler(argv[2]);

        if (!sched) {
            fprintf(stderr, "Unknown scheduler: %s\n", argv[2]);
            usage(argv[0]);
            return 1;
        }

        printf("\nRunning scheduler: %s", sched->name);
        if (strcmp(sched->name, "rr") == 0) {
            printf(" (quantum=%d)", quantum);
        }
        printf("\n");

        sched->run(procs, n, quantum);
        metrics_print(procs, n);
    }

    return 0;
}
