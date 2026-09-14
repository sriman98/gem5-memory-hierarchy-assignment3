/* stream: sequential sweeps over a WORDS-element array of 8-byte words
 * (default 512 Ki words = 4 MiB, larger than a 2 MiB L2): one write pass
 * (a[i] = i*const) then PASSES read passes summing the array.  Pure spatial
 * locality: every miss brings a line whose remaining words are used next,
 * so block size and next-line/stride prefetching matter, capacity does not
 * until the whole array fits. */
#include "common.h"
int main(int argc, char **argv) {
    long words = arg_n(argc, argv, 1, 512 * 1024);
    long passes = arg_n(argc, argv, 2, 2);
    uint64_t *a = malloc(words * sizeof(uint64_t));
    if (!a) return 1;
    for (long i = 0; i < words; i++) a[i] = (uint64_t)i * 2654435761ULL;
    uint64_t sum = 0;
    for (long p = 0; p < passes; p++)
        for (long i = 0; i < words; i++) sum += a[i];
    printf("stream: words=%ld passes=%ld checksum=%016llx\n", words, passes,
           (unsigned long long)sum);
    return 0;
}
