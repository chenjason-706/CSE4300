#ifndef PROCESS_H
#define PROCESS_H

typedef struct {
    int pid;
    int arrival_time;
    int burst_time;
    int priority;
    int remaining_time;
    int start_time;    /* -1 until first scheduled */
    int finish_time;
} Process;

#endif 
