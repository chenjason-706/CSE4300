/* Jumps around a 256 KB array (64 pages) in random order. There is almost
   no locality, so this is the worst case for the TLB and page replacement. */
#include "common.h"

#define SIZE (256 * 1024)
#define STEPS 25000

static char data[SIZE];

int main(void) {
    long total = 0;
    for (int i = 0; i < STEPS; i++) {
        unsigned int spot = next_random() % SIZE;
        data[spot]++;
        total += data[(spot * 7) % SIZE];
    }
    return total < 0;
}
