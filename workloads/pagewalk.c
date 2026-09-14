/* pagewalk: PAGES regions of 4 KiB; one word in each region holds the index
 * of the next region in one random cycle (as in chase), and the loop follows
 * the chain HOPS times.  Only PAGES cache lines are ever touched (512
 * regions -> 32 KiB, L1-resident), but every hop is on a different 4 KiB
 * page, so the run isolates address translation: TLB misses appear as soon
 * as PAGES x page size exceeds the TLB reach (entries x page size), and
 * every region costs one first-touch page fault.  The word sits at line
 * (i mod 64) of region i rather than at offset 0, so the lines spread over
 * all cache sets instead of colliding on the page-offset index bits. */
#include "common.h"
#define REGION 4096
#define SLOT(i) ((size_t)(i) * REGION + ((size_t)(i) % 64) * 64)
int main(int argc, char **argv) {
    long pages = arg_n(argc, argv, 1, 512);
    long hops = arg_n(argc, argv, 2, 500000);
    uint8_t *buf = aligned_malloc((size_t)pages * REGION, REGION);
    uint32_t *idx = malloc(pages * sizeof(uint32_t));
    if (!buf || !idx) return 1;
    uint64_t s = 4242;
    for (long i = 0; i < pages; i++) idx[i] = (uint32_t)i;
    for (long i = pages - 1; i > 0; i--) {
        long j = (long)(lcg_next(&s) % (uint64_t)i);
        uint32_t t = idx[i]; idx[i] = idx[j]; idx[j] = t;
    }
    for (long i = 0; i < pages; i++)
        *(uint32_t *)(buf + SLOT(idx[i])) = idx[(i + 1) % pages];
    uint32_t p = 0;
    for (long h = 0; h < hops; h++) p = *(uint32_t *)(buf + SLOT(p));
    printf("pagewalk: pages=%ld hops=%ld final=%u\n", pages, hops, p);
    return 0;
}
