/* matmul: C = A x B for N x N doubles.  block = 0 -> naive i-j-k loops whose
 * inner loop walks B column-wise (stride N*8 bytes: one new cache line per
 * multiply, poor spatial locality, and with N=96 the three 72 KiB matrices
 * exceed a 64 KiB L1).  block = B -> classic loop tiling: a B x B tile of
 * each matrix is reused while it is hot in L1 (temporal locality). */
#include "common.h"
#define MIN(a, b) ((a) < (b) ? (a) : (b))
int main(int argc, char **argv) {
    long n = arg_n(argc, argv, 1, 96);
    long bs = arg_n(argc, argv, 2, 0);
    double *A = malloc(n * n * sizeof(double));
    double *B = malloc(n * n * sizeof(double));
    double *C = calloc(n * n, sizeof(double));
    if (!A || !B || !C) return 1;
    uint64_t s = 12345;
    for (long i = 0; i < n * n; i++) {          /* multiples of 1/8: exact */
        A[i] = (double)(lcg_next(&s) % 1000) / 8.0;
        B[i] = (double)(lcg_next(&s) % 1000) / 8.0;
    }
    if (bs <= 0) {
        for (long i = 0; i < n; i++)
            for (long j = 0; j < n; j++) {
                double acc = 0.0;
                for (long k = 0; k < n; k++) acc += A[i * n + k] * B[k * n + j];
                C[i * n + j] = acc;
            }
    } else {
        for (long ii = 0; ii < n; ii += bs)
            for (long jj = 0; jj < n; jj += bs)
                for (long kk = 0; kk < n; kk += bs)
                    for (long i = ii; i < MIN(ii + bs, n); i++)
                        for (long j = jj; j < MIN(jj + bs, n); j++) {
                            double acc = C[i * n + j];
                            for (long k = kk; k < MIN(kk + bs, n); k++)
                                acc += A[i * n + k] * B[k * n + j];
                            C[i * n + j] = acc;
                        }
    }
    double sum = 0.0;                            /* exact: all values are k/8 */
    for (long i = 0; i < n * n; i++) sum += C[i];
    /* printed as a scaled integer: musl's printf("%f") takes an x87 path
     * that gem5's x86 model does not execute correctly (Assignment 4) */
    printf("matmul: n=%ld block=%ld checksum=%lld\n", n, bs, (long long)(sum * 64.0));
    return 0;
}
