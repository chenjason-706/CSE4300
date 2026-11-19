/* Multiplies two 40x40 matrices. Reads a row by row (good locality) and
   b column by column (jumps a page every few steps). */
#include "common.h"

#define N 40

static double a[N][N], b[N][N], c[N][N];

int main(void) {
    for (int i = 0; i < N; i++)
        for (int j = 0; j < N; j++) {
            a[i][j] = i + j;
            b[i][j] = i - j;
        }

    for (int i = 0; i < N; i++)
        for (int j = 0; j < N; j++) {
            double sum = 0;
            for (int k = 0; k < N; k++)
                sum += a[i][k] * b[k][j];
            c[i][j] = sum;
        }

    return c[N - 1][N - 1] > 0;
}
