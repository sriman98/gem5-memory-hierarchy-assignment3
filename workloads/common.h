/* Shared helpers for the Assignment 3 memory-hierarchy workloads
 * (Sriman Cherukuru, University of the Cumberlands, September 2026).
 * Every program is a small, self-checking kernel: it takes optional
 * arguments, runs, and prints its parameters plus a checksum so correct
 * execution inside gem5 can be verified against a native run. */
#ifndef MEMHIER_COMMON_H
#define MEMHIER_COMMON_H
#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>
#include <string.h>
static inline uint64_t lcg_next(uint64_t *s) {           /* fixed-seed PRNG */
    *s = *s * 6364136223846793005ULL + 1442695040888963407ULL;
    return *s >> 33;
}
static inline long arg_n(int argc, char **argv, int i, long dflt) {
    return argc > i ? atol(argv[i]) : dflt;
}
/* malloc with the start aligned to `align` bytes (align = power of two). */
static inline void *aligned_malloc(size_t bytes, size_t align) {
    char *raw = malloc(bytes + align);
    if (!raw) return NULL;
    uintptr_t p = ((uintptr_t)raw + align) & ~(uintptr_t)(align - 1);
    return (void *)p;
}
#endif
