/* Fills an array with random numbers and quicksorts it. Mostly scans
   through the array, with some back-and-forth between the two halves. */
#include "common.h"

#define N 6000

static int nums[N];

static void quicksort(int *x, int lo, int hi) {
    while (lo < hi) {
        int pivot = x[(lo + hi) / 2];
        int i = lo, j = hi;
        while (i <= j) {
            while (x[i] < pivot) i++;
            while (x[j] > pivot) j--;
            if (i <= j) {
                int t = x[i];
                x[i] = x[j];
                x[j] = t;
                i++;
                j--;
            }
        }
        if (j - lo < hi - i) {
            quicksort(x, lo, j);
            lo = i;
        } else {
            quicksort(x, i, hi);
            hi = j;
        }
    }
}

int main(void) {
    for (int i = 0; i < N; i++)
        nums[i] = next_random() % 100000;
    quicksort(nums, 0, N - 1);
    return nums[0] > nums[N - 1];
}
