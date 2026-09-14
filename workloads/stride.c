/* stride: K cache lines spaced STRIDE bytes apart are read round-robin
 * ITERS times.  When STRIDE equals the cache's way size (size / assoc, e.g.
 * 32 KiB for a 64 KiB 2-way cache) every one of the K lines maps to the SAME
 * set, so a cache with fewer than K ways misses on every access although the
 * live data is only K x 64 bytes: pure conflict misses, exactly what higher
 * associativity or a small fully-associative victim cache removes.
 * The buffer is accessed through a volatile pointer so that the compiler
 * cannot hoist the K loop-invariant loads out of the ITERS loop, and it is
 * swept once before the timed loop (see the comment in main). */
#include "common.h"
int main(int argc, char **argv) {
    long stride = arg_n(argc, argv, 1, 32768);
    long k = arg_n(argc, argv, 2, 8);
    long iters = arg_n(argc, argv, 3, 200000);
    uint64_t *buf = aligned_malloc((size_t)stride * k, 4096);
    if (!buf) return 1;
    /* Touch the whole buffer in address order first.  gem5's caches are
     * physically indexed and its SE mode gives a page a physical frame on
     * first touch, so touching only the K lines would scatter them over K
     * consecutive frames and hide the conflict; a sequential sweep makes
     * the buffer physically contiguous, as a large page would. */
    memset(buf, 0, (size_t)stride * k);
    for (long i = 0; i < k; i++) buf[i * (stride / 8)] = 1000 + i;
    volatile uint64_t *vb = buf;                 /* every load really happens */
    uint64_t sum = 0;
    for (long it = 0; it < iters; it++)
        for (long i = 0; i < k; i++) sum += vb[i * (stride / 8)];
    printf("stride: stride=%ld lines=%ld iters=%ld checksum=%llu\n", stride, k,
           iters, (unsigned long long)sum);
    return 0;
}
