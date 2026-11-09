#include <assert.h>
#include <stddef.h>
#include <stdio.h>

#include "../include/queue.h"

int main(void)
{
    Queue queue;
    Process a = {.pid = 1, .burst_time = 8, .priority = 3};
    Process b = {.pid = 2, .burst_time = 2, .priority = 1};
    Process c = {.pid = 3, .burst_time = 2, .priority = 1};

    assert(queue_init(&queue, 0) == -1);
    queue_destroy(&queue);
    assert(queue_init(&queue, 3) == 0);
    assert(queue_is_empty(&queue));
    assert(queue_dequeue(&queue) == NULL);
    assert(queue_take_shortest(&queue) == NULL);
    assert(queue_take_highest_priority(&queue) == NULL);
    assert(queue_enqueue(&queue, NULL) == -1);
    assert(queue_enqueue(&queue, &a) == 0);
    assert(queue_enqueue(&queue, &a) == -1);
    assert(queue_enqueue(&queue, &b) == 0);
    assert(queue_enqueue(&queue, &c) == 0);
    assert(queue_enqueue(&queue, &a) == -1);

    /* Round Robin */
    Process *running = queue_dequeue(&queue);
    assert(running == &a);
    running->remaining_time = 4;
    assert(a.remaining_time == 4);
    assert(queue_enqueue(&queue, running) == 0);
    assert(queue_dequeue(&queue) == &b);
    assert(queue_dequeue(&queue) == &c);
    assert(queue_dequeue(&queue) == &a);

    assert(queue_enqueue(&queue, &a) == 0);
    assert(queue_enqueue(&queue, &b) == 0);
    assert(queue_enqueue(&queue, &c) == 0);
    assert(queue_take_shortest(&queue) == &b);
    assert(queue_take_shortest(&queue) == &c);
    assert(queue_dequeue(&queue) == &a);
    assert(queue_enqueue(&queue, &a) == 0);
    assert(queue_enqueue(&queue, &b) == 0);
    assert(queue_enqueue(&queue, &c) == 0);
    assert(queue_take_highest_priority(&queue) == &b);
    assert(queue_take_highest_priority(&queue) == &c);
    assert(queue_dequeue(&queue) == &a);
    assert(queue_is_empty(&queue));
    queue_destroy(&queue);
    queue_destroy(&queue);
    puts("Queue tests passed");
    return 0;
}
