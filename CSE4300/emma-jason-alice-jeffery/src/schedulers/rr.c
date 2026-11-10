#include <stdio.h>

#include "scheduler.h"

static void admit_arrivals(Process procs[], int n, int admitted[],
			   int q[], int *tail, int *count, int clock) {
	for (int i = 0; i < n; i++) {
		if (!admitted[i] && procs[i].arrival_time <= clock) {
			admitted[i] = 1;
			q[*tail] = i;
			*tail = (*tail + 1) % n;
			(*count)++;
		}
	}
}

void run_rr(Process procs[], int n, int quantum)
{
	if (n <= 0)
		return;
	if (quantum <= 0) {
		fprintf(stderr, "[rr] quantum must be greater than 0\n");
		return;
	}

	int q[n];
	int head = 0, tail = 0, count = 0;

	int admitted[n];
	for (int i = 0; i < n; i++)
		admitted[i] = 0;

	int clock = 0;
	int completed = 0;

	admit_arrivals(procs, n, admitted, q, &tail, &count, clock);

	while (completed < n) {
		if (count == 0) {
			int next = -1;
			for (int i = 0; i < n; i++) {
				if (!admitted[i] &&
				    (next == -1 ||
				     procs[i].arrival_time < procs[next].arrival_time))
					next = i;
				}
		clock = procs[next].arrival_time;
		admit_arrivals(procs, n, admitted, q, &tail, &count, clock);
		continue;
		}

		int idx = q[head];
		head = (head + 1) % n;
		count--;
		Process *p = &procs[idx];

		if (p->start_time == -1)
			p->start_time = clock;

		int slice = (p->remaining_time < quantum) ? p-> remaining_time : quantum;
		clock += slice;
		p->remaining_time -= slice;

		admit_arrivals(procs, n, admitted, q, &tail, &count, clock);

		if (p->remaining_time > 0) {
			q[tail] = idx;
			tail = (tail + 1) % n;
			count++;
		} else {
			p->finish_time = clock;
			completed++;
		}
	}
}
