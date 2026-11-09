#ifndef QUEUE_H
#define QUEUE_H

#include "process.h"

typedef struct {
    Process **items;
    int size;
    int capacity;
} Queue;


int queue_init(Queue *queue, int capacity);
void queue_destroy(Queue *queue);
int queue_is_empty(const Queue *queue);

int queue_enqueue(Queue *queue, Process *process);

Process *queue_dequeue(Queue *queue);
Process *queue_take_shortest(Queue *queue);

Process *queue_take_highest_priority(Queue *queue);

#endif
