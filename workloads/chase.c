/* chase: dependent pointer chasing over a FOOTPRINT-KiB array of 64-byte
 * nodes linked in ONE random cycle (Sattolo's algorithm), so every hop is a
 * load that depends on the previous load and lands on an unpredictable line:
 * no memory-level parallelism, no prefetchable pattern.  Sweeping the
 * footprint exposes the L1 and L2 capacity cliffs; large footprints also
 * scatter the accesses over many pages and stress the TLB. */
#include "common.h"
struct node { uint32_t next; uint8_t pad[60]; };
int main(int argc, char **argv) {
    long kib = arg_n(argc, argv, 1, 1024);
    long hops = arg_n(argc, argv, 2, 500000);
    long n = kib * 1024 / (long)sizeof(struct node);
    struct node *a = aligned_malloc((size_t)n * sizeof(struct node), 64);
    uint32_t *idx = malloc(n * sizeof(uint32_t));
    if (!a || !idx) return 1;
    uint64_t s = 777;
    for (long i = 0; i < n; i++) idx[i] = (uint32_t)i;
    for (long i = n - 1; i > 0; i--) {           /* Sattolo: a single cycle */
        long j = (long)(lcg_next(&s) % (uint64_t)i);
        uint32_t t = idx[i]; idx[i] = idx[j]; idx[j] = t;
    }
    for (long i = 0; i < n; i++) a[idx[i]].next = idx[(i + 1) % n];
    uint32_t p = 0;
    for (long h = 0; h < hops; h++) p = a[p].next;
    printf("chase: footprint_kib=%ld nodes=%ld hops=%ld final=%u\n", kib, n, hops, p);
    return 0;
}
