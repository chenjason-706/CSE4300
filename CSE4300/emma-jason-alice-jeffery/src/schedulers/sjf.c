#include <stdio.h>

#include "scheduler.h"

void run_sjf(Process procs[], int n, int quantum)
{
    (void)quantum;

    if (n <= 0)
	    return;

    int clock = 0;
	int completed = 0;

	while (completed < n) {
		int best = -1;
		for (int i = 0; i < n; i++) {
			if (procs[i].remaining_time <= 0 || procs[i].arrival_time > clock)
				continue;
			if (best == -1 ||
				procs[i].remaining_time < procs[best].remaining_time ||
			(procs[i].remaining_time == procs[best].remaining_time &&
			 procs[i].arrival_time < procs[best].arrival_time))
				best = i;
		}

		if (best == -1) {
			clock++;
			continue;
		}
		if (procs[best].start_time == -1)
			procs[best].start_time = clock;
		
		procs[best].remaining_time--;
		clock++;
		if (procs[best].remaining_time == 0) {
			procs[best].finish_time = clock;
			completed++;
		}
	}
}
