"""
memhier_config.py -- gem5 syscall-emulation (SE) configuration for
Assignment 3, "Exploring Memory Hierarchy Design in gem5", by
Sriman Cherukuru (University of the Cumberlands, September 2026).

One script drives every experiment of Part 2.  With no options it builds
exactly the system that gem5's stock
  configs/deprecated/example/se.py --cpu-type=TimingSimpleCPU --caches --l2cache
builds (64 KiB 2-way L1D, 32 KiB 2-way L1I, 2 MiB 8-way L2, 64-byte lines,
LRU, no prefetcher, 64-entry TLBs, 4 KiB pages, 2 GHz CPU, DDR3-1600), so
the stock run is the baseline and every option below is one deviation.

  cache geometry   --l1d-size/--l1d-assoc/--l1i-size/--l1i-assoc/--l2-size/
                   --l2-assoc/--line/--no-l2, latencies --l1-lat/--l2-lat,
                   --l1-mshrs/--l2-mshrs
  optimizations    --l1d-pf/--l2-pf none|tagged|stride (+ --pf-degree),
                   --l1d-repl/--l2-repl lru|random|treeplru|fifo|rrip|nru,
                   --victim N  (N-line fully associative victim buffer
                                between L1D and L2)
  virtual memory   --dtlb/--itlb entries, --page-size 4KiB|64KiB|2MiB...,
                   --tlb-miss-lat / --fault-lat cycles (the SE-mode
                   penalties added to gem5 for this assignment)
  core             --cpu timing (in-order, default) | o3 (out-of-order)

Example:
  build/X86/gem5.opt --outdir=m5out configs/memhier_config.py \
      --l1d-size 32KiB --l1d-assoc 4 --l2-pf stride --cmd bin/matmul:96:0
"""
import argparse
import os

import m5
from m5.objects import *

# ---------------------------------------------------------------- options
parser = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
g = parser.add_argument_group("core")
g.add_argument("--cpu", choices=["timing", "o3"], default="timing",
               help="timing = in-order TimingSimpleCPU (default), o3 = out-of-order")
g.add_argument("--clock", default="2GHz", help="CPU clock (default 2GHz, as se.py)")
g.add_argument("--sys-clock", default="1GHz", help="memory-side clock (default 1GHz)")
g.add_argument("--maxinsts", type=int, default=0, help="stop after N instructions")

g = parser.add_argument_group("cache geometry (defaults = gem5 se.py defaults)")
g.add_argument("--l1d-size", default="64KiB")
g.add_argument("--l1d-assoc", type=int, default=2)
g.add_argument("--l1i-size", default="32KiB")
g.add_argument("--l1i-assoc", type=int, default=2)
g.add_argument("--l1-lat", type=int, default=2, help="L1 tag/data/response latency (cycles)")
g.add_argument("--l1-mshrs", type=int, default=4)
g.add_argument("--l2-size", default="2MiB")
g.add_argument("--l2-assoc", type=int, default=8)
g.add_argument("--l2-lat", type=int, default=20, help="L2 tag/data/response latency (cycles)")
g.add_argument("--l2-mshrs", type=int, default=20)
g.add_argument("--no-l2", action="store_true", help="L1s talk to DRAM directly")
g.add_argument("--line", type=int, default=64, help="cache line (block) size in bytes, all levels")

g = parser.add_argument_group("cache optimizations")
g.add_argument("--l1d-pf", choices=["none", "tagged", "stride"], default="none",
               help="L1D hardware prefetcher (tagged = next-line, stride = PC-based stride)")
g.add_argument("--l2-pf", choices=["none", "tagged", "stride"], default="none")
g.add_argument("--pf-degree", type=int, default=0,
               help="prefetch degree (0 = gem5 default: tagged 2, stride 4)")
g.add_argument("--l1d-repl", choices=["lru", "random", "treeplru", "fifo", "rrip", "nru"], default="lru")
g.add_argument("--l2-repl", choices=["lru", "random", "treeplru", "fifo", "rrip", "nru"], default="lru")
g.add_argument("--victim", type=int, default=0,
               help="add an N-line fully associative victim buffer behind L1D (0 = none)")

g = parser.add_argument_group("virtual memory")
g.add_argument("--dtlb", type=int, default=64, help="data TLB entries (default 64)")
g.add_argument("--itlb", type=int, default=64, help="instruction TLB entries (default 64)")
g.add_argument("--page-size", default="4KiB", help="emulated page size (4KiB, 16KiB, 64KiB, 2MiB ...)")
g.add_argument("--tlb-miss-lat", type=int, default=0,
               help="cycles charged per TLB miss (SE-mode page-walk penalty; 0 = stock gem5)")
g.add_argument("--fault-lat", type=int, default=0,
               help="extra cycles charged per first-touch page fault (0 = stock gem5)")

g = parser.add_argument_group("memory and workload")
g.add_argument("--mem-size", default="1GiB")
g.add_argument("--mem-type", default="DDR3_1600_8x8")
g.add_argument("--cmd", required=True, metavar="BIN[:ARG[:ARG...]]",
               help="program to run, arguments separated by ':'")
args = parser.parse_args()

# --------------------------------------------------------------- helpers
def repl_policy(kind):
    return {"lru": LRURP, "random": RandomRP, "treeplru": TreePLRURP,
            "fifo": FIFORP, "rrip": BRRIPRP, "nru": NRURP}[kind]()

def prefetcher(kind):
    """gem5's next-line ("tagged") and PC-stride prefetchers; None = no prefetcher."""
    if kind == "none":
        return None
    pf = TaggedPrefetcher() if kind == "tagged" else StridePrefetcher()
    if args.pf_degree:
        pf.degree = args.pf_degree
    return pf

def make_cache(size, assoc, lat, mshrs, tgts, repl="lru", pf="none", **kw):
    c = Cache(size=size, assoc=assoc, tag_latency=lat, data_latency=lat,
              response_latency=lat, mshrs=mshrs, tgts_per_mshr=tgts,
              replacement_policy=repl_policy(repl), **kw)
    p = prefetcher(pf)
    if p is not None:
        c.prefetcher = p
    return c

# --------------------------------------------------------------- system
system = System()
system.clk_domain = SrcClockDomain(clock=args.sys_clock, voltage_domain=VoltageDomain())
system.cpu_clk_domain = SrcClockDomain(clock=args.clock, voltage_domain=VoltageDomain())
system.cache_line_size = args.line
system.mem_mode = "timing"
system.mem_ranges = [AddrRange(args.mem_size)]

CPU = X86TimingSimpleCPU if args.cpu == "timing" else X86O3CPU
system.cpu = CPU(clk_domain=system.cpu_clk_domain)
if args.maxinsts:
    system.cpu.max_insts_any_thread = args.maxinsts

# TLBs: gem5's default is 64 entries each; the miss/fault penalties are the
# SE-mode extension added for this assignment (0 = stock behaviour).
for tlb, n in ((system.cpu.mmu.dtb, args.dtlb), (system.cpu.mmu.itb, args.itlb)):
    tlb.size = n
    tlb.miss_latency = args.tlb_miss_lat
    tlb.fault_latency = args.fault_lat

# L1 caches (se.py: 2-cycle, 4 MSHRs, 20 targets; I-cache read-only and
# writes back clean lines, as in configs/common/Caches.py).
system.cpu.icache = make_cache(args.l1i_size, args.l1i_assoc, args.l1_lat, args.l1_mshrs, 20,
                               is_read_only=True, writeback_clean=True)
system.cpu.dcache = make_cache(args.l1d_size, args.l1d_assoc, args.l1_lat, args.l1_mshrs, 20,
                               repl=args.l1d_repl, pf=args.l1d_pf)
system.cpu.icache.cpu_side = system.cpu.icache_port
system.cpu.dcache.cpu_side = system.cpu.dcache_port

# Optional victim buffer: a tiny fully associative, 1-cycle cache behind the
# L1D that is *mostly exclusive* of it -- it does not keep lines it passes
# up on a miss, but it allocates the lines the L1D writes back (with
# writeback_clean the L1D also hands down its evicted clean lines).  That is
# Jouppi's (1990) victim cache expressed with gem5's clusivity knobs.
system.membus = SystemXBar()
if args.victim:
    system.cpu.dcache.writeback_clean = True
    system.victim = Cache(size=f"{args.victim * args.line}B", assoc=args.victim,
                          tag_latency=1, data_latency=1, response_latency=1,
                          mshrs=8, tgts_per_mshr=8, clusivity="mostly_excl",
                          replacement_policy=LRURP())
    system.cpu.dcache.mem_side = system.victim.cpu_side
    dcache_out = system.victim
else:
    dcache_out = system.cpu.dcache

if args.no_l2:
    system.cpu.icache.mem_side = system.membus.cpu_side_ports
    dcache_out.mem_side = system.membus.cpu_side_ports
else:
    # se.py: L2XBar "tol2bus" between the L1s and a shared L2 named "l2"
    system.tol2bus = L2XBar(clk_domain=system.cpu_clk_domain)
    system.cpu.icache.mem_side = system.tol2bus.cpu_side_ports
    dcache_out.mem_side = system.tol2bus.cpu_side_ports
    system.l2 = make_cache(args.l2_size, args.l2_assoc, args.l2_lat, args.l2_mshrs, 12,
                           repl=args.l2_repl, pf=args.l2_pf, write_buffers=8,
                           clk_domain=system.cpu_clk_domain)
    system.l2.cpu_side = system.tol2bus.mem_side_ports
    system.l2.mem_side = system.membus.cpu_side_ports

system.mem_ctrl = MemCtrl()
system.mem_ctrl.dram = eval(args.mem_type)(range=system.mem_ranges[0])
system.mem_ctrl.port = system.membus.mem_side_ports
system.system_port = system.membus.cpu_side_ports

# x86 needs an interrupt controller with three ports wired to the bus.
system.cpu.createInterruptController()
system.cpu.interrupts[0].pio = system.membus.mem_side_ports
system.cpu.interrupts[0].int_requestor = system.membus.cpu_side_ports
system.cpu.interrupts[0].int_responder = system.membus.mem_side_ports

# ------------------------------------------------------------ workload
parts = args.cmd.split(":")
binary = parts[0]                      # as given (relative), exactly like se.py's argv[0]
process = Process(cmd=[binary] + parts[1:], executable=binary, cwd=os.getcwd(),
                  gid=os.getgid(), page_size=args.page_size)
system.workload = SEWorkload.init_compatible(os.path.abspath(binary))
system.cpu.workload = process
system.cpu.createThreads()

# ------------------------------------------------------------ simulate
root = Root(full_system=False, system=system)
m5.instantiate()
print(f"[memhier] cpu={args.cpu} L1D={args.l1d_size}/{args.l1d_assoc}w L1I={args.l1i_size}/{args.l1i_assoc}w "
      f"L2={'none' if args.no_l2 else args.l2_size + '/' + str(args.l2_assoc) + 'w'} line={args.line}B "
      f"pf={args.l1d_pf}/{args.l2_pf} repl={args.l1d_repl}/{args.l2_repl} victim={args.victim} "
      f"dtlb={args.dtlb} itlb={args.itlb} page={args.page_size} tlbmiss={args.tlb_miss_lat}c fault={args.fault_lat}c "
      f"cmd={args.cmd}")
exit_event = m5.simulate()
print(f"[memhier] exiting @ tick {m5.curTick()} because {exit_event.getCause()}")
