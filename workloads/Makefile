# Cross-compile the workloads for gem5's x86-64 SE mode on macOS with zig
# (no glibc x86-64 gcc exists on the Mac; see Assignment 2).  Static musl
# binaries run in gem5 as-is.  Vectorization and unrolling are disabled so
# the kernels stay simple scalar loops whose memory access pattern is
# exactly the one described in each source file.
ZIG    ?= zig
TARGET ?= x86_64-linux-musl
CFLAGS ?= -O2 -static -fno-vectorize -fno-slp-vectorize -fno-unroll-loops
PROGS   = hello matmul stream stride chase pagewalk
BIN     = ../bin
NATIVE  = ../native

all: $(addprefix $(BIN)/,$(PROGS))

native: $(addprefix $(NATIVE)/,$(PROGS))   # host builds, for checksum validation

$(BIN)/%: %.c common.h
	@mkdir -p $(BIN)
	$(ZIG) cc -target $(TARGET) $(CFLAGS) $< -o $@

$(NATIVE)/%: %.c common.h
	@mkdir -p $(NATIVE)
	cc -O2 -fno-vectorize -fno-slp-vectorize -fno-unroll-loops $< -o $@

clean:
	rm -rf $(BIN) $(NATIVE)
.PHONY: all native clean
