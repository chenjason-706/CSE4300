#include <stdlib.h>

#include "../include/queue.h"

int queue_init(Queue *queue, int capacity)
{
    queue->items = NULL;
    queue->size = 0;
    queue->capacity = 0;
    if (capacity <= 0) {
        return -1;
    }
    queue->items = calloc((size_t)capacity, sizeof(*queue->items));
    if (queue->items == NULL) {
        return -1;
    }
    queue->capacity = capacity;
    return 0;
}

void queue_destroy(Queue *queue)
{
    free(queue->items);
    queue->items = NULL;
    queue->size = 0;
    queue->capacity = 0;
}

int queue_is_empty(const Queue *queue)
{
    return queue->size == 0;
}

int queue_enqueue(Queue *queue, Process *process)
{
    int i;
    if (process == NULL || queue->size >= queue->capacity) {
        return -1;
    }
    for (i = 0; i < queue->size; i++) {
        if (queue->items[i] == process) {
            return -1;
        }
    }
    queue->items[queue->size++] = process;
    return 0;
}

static Process *remove_at(Queue *queue, int index)
{
    Process *process = queue->items[index];
    int i;
    for (i = index + 1; i < queue->size; i++) {
        queue->items[i - 1] = queue->items[i];
    }
    queue->items[--queue->size] = NULL;
    return process;
}

Process *queue_dequeue(Queue *queue)
{
    return queue_is_empty(queue) ? NULL : remove_at(queue, 0);
}

Process *queue_take_shortest(Queue *queue)
{
    int best = 0;
    int i;
    if (queue_is_empty(queue)) {
        return NULL;
    }
    for (i = 1; i < queue->size; i++) {
        if (queue->items[i]->burst_time < queue->items[best]->burst_time) {
            best = i;
        }
    }
    return remove_at(queue, best);
}

Process *queue_take_highest_priority(Queue *queue)
{
    int best = 0;
    int i;
    if (queue_is_empty(queue)) {
        return NULL;
    }
    for (i = 1; i < queue->size; i++) {
        if (queue->items[i]->priority < queue->items[best]->priority) {
            best = i;
        }
    }
    return remove_at(queue, best);
}
