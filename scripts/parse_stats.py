#!/usr/bin/env python3
"""parse_stats.py [--csv out.csv] [name-prefix ...]
Aggregate every results/runs/<name>/stats.txt into results/summary.csv and print
a compact table.  Run names are <experiment>_<variant>_<workload>.

Derived metrics: latencies are converted from ticks to CPU cycles with the CPU
clock period found in config.ini; AMAT (average memory access time) of the L1D
is  hit latency + miss rate x average miss latency  (Hennessy & Patterson, 2019).
"""
import csv
import glob
import os
import re
import sys

R = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RUNS = os.path.join(R, "results", "runs")
OUT = os.path.join(R, "results", "summary.csv")
PROG_RE = re.compile(r"^(Hello, World!|matmul:|stream:|stride:|chase:|pagewalk:).*")

def read_stats(path):
    d = {}
    with open(path) as f:
        for line in f:
            parts = line.split()
            if len(parts) >= 2 and not line.startswith("-"):
                try:
                    d[parts[0]] = float(parts[1])
                except ValueError:
                    pass
    return d

def read_config(path):
    """Return {section: {key: value}} of config.ini."""
    cfg, sec = {}, None
    with open(path) as f:
        for line in f:
            line = line.strip()
            if line.startswith("[") and line.endswith("]"):
                sec = line[1:-1]; cfg[sec] = {}
            elif "=" in line and sec:
                k, v = line.split("=", 1); cfg[sec][k] = v
    return cfg

def parse_run(rundir):
    name = os.path.basename(rundir)
    sp = os.path.join(rundir, "stats.txt")
    if not os.path.exists(sp) or os.path.getsize(sp) == 0:
        return None
    s = read_stats(sp)
    cfg = read_config(os.path.join(rundir, "config.ini"))
    g = lambda k, dflt=0.0: s.get(k, dflt)
    # gem5's se.py names its controller system.mem_ctrls0, this repository's script system.mem_ctrl
    mc = "system.mem_ctrls" if "system.mem_ctrls.readReqs" in s else "system.mem_ctrl"
    clk = float(cfg.get("system.cpu_clk_domain", {}).get("clock", "500"))   # ticks per CPU cycle
    cyc = lambda ticks: ticks / clk
    parts = name.split("_")
    exp, wl, variant = parts[0], parts[-1], "_".join(parts[1:-1])
    prog = ""
    lp = os.path.join(rundir, "run.log")
    if os.path.exists(lp):
        for line in open(lp, errors="replace"):
            if PROG_RE.match(line):
                prog = line.strip(); break
    rc = ""
    cl = os.path.join(rundir, "cmdline.txt")
    if os.path.exists(cl):
        for line in open(cl):
            if line.startswith("rc="):
                rc = line.strip()[3:]
    dc, l2, ic = "system.cpu.dcache.", "system.l2.", "system.cpu.icache."
    cycles = g("system.cpu.numCycles")
    insts = g("simInsts")
    l1d_acc, l1d_miss = g(dc + "overallAccesses::total"), g(dc + "overallMisses::total")
    l1d_mr = l1d_miss / l1d_acc if l1d_acc else 0.0
    l1d_hit_lat = float(cfg.get("system.cpu.dcache", {}).get("tag_latency", "2"))
    l1d_mlat = cyc(g(dc + "overallAvgMissLatency::total"))
    l2_acc, l2_miss = g(l2 + "overallAccesses::total"), g(l2 + "overallMisses::total")
    dtlb_acc = g("system.cpu.mmu.dtb.rdAccesses") + g("system.cpu.mmu.dtb.wrAccesses")
    dtlb_miss = g("system.cpu.mmu.dtb.rdMisses") + g("system.cpu.mmu.dtb.wrMisses")
    penalty = g("system.cpu.mmu.dtb.penaltyCycles") + g("system.cpu.mmu.itb.penaltyCycles")
    pf_issued = g(dc + "prefetcher.pfIssued") + g(l2 + "prefetcher.pfIssued")
    pf_useful = g(dc + "prefetcher.pfUseful") + g(l2 + "prefetcher.pfUseful")
    row = {
        "name": name, "exp": exp, "variant": variant, "workload": wl, "rc": rc,
        "insts": int(insts), "cycles": int(cycles),
        "cpi": cycles / insts if insts else 0.0, "ipc": insts / cycles if cycles else 0.0,
        "sim_ms": 1000 * g("simSeconds"), "host_s": g("hostSeconds"),
        "l1d_acc": int(l1d_acc), "l1d_miss": int(l1d_miss), "l1d_mr": l1d_mr,
        "l1d_mshr_miss": int(g(dc + "overallMshrMisses::total")),
        "l1d_miss_lat_cyc": l1d_mlat, "l1d_hit_lat": l1d_hit_lat,
        "l1d_amat": l1d_hit_lat + l1d_mr * l1d_mlat,
        "l1d_mpki": 1000 * l1d_miss / insts if insts else 0.0,
        "l1d_repl": int(g(dc + "replacements")), "l1d_wb": int(g(dc + "writebacks::total")),
        "l1i_acc": int(g(ic + "overallAccesses::total")), "l1i_miss": int(g(ic + "overallMisses::total")),
        "l1i_mr": g(ic + "overallMissRate::total"),
        "l2_acc": int(l2_acc), "l2_miss": int(l2_miss), "l2_mr": l2_miss / l2_acc if l2_acc else 0.0,
        "l2_miss_lat_cyc": cyc(g(l2 + "overallAvgMissLatency::total")),
        "l2_mpki": 1000 * l2_miss / insts if insts else 0.0,
        "victim_hits": int(g("system.victim.overallHits::total")),
        "victim_miss": int(g("system.victim.overallMisses::total")),
        "dram_rd": int(g(mc + ".readReqs")), "dram_wr": int(g(mc + ".writeReqs")),
        "dram_bytes": int(g(mc + ".dram.bytesRead::total") + g(mc + ".dram.bytesWritten::total")),
        "dram_lat_cyc": cyc(g(mc + ".dram.avgMemAccLat")),
        "dtlb_acc": int(dtlb_acc), "dtlb_miss": int(dtlb_miss),
        "dtlb_mr": dtlb_miss / dtlb_acc if dtlb_acc else 0.0,
        "dtlb_mpki": 1000 * dtlb_miss / insts if insts else 0.0,
        "itlb_acc": int(g("system.cpu.mmu.itb.exAccesses")), "itlb_miss": int(g("system.cpu.mmu.itb.exMisses")),
        "page_faults": int(g("system.cpu.mmu.dtb.pageFaults") + g("system.cpu.mmu.itb.pageFaults")),
        "penalty_cyc": int(penalty), "penalty_frac": penalty / cycles if cycles else 0.0,
        "pf_issued": int(pf_issued), "pf_useful": int(pf_useful),
        "pf_accuracy": pf_useful / pf_issued if pf_issued else 0.0,
        "program_output": prog,
    }
    return row

def main():
    argv = sys.argv[1:]
    out = OUT
    if "--csv" in argv:
        i = argv.index("--csv"); out = argv[i + 1]; del argv[i:i + 2]
    rows = []
    for d in sorted(glob.glob(os.path.join(RUNS, "*"))):
        if not os.path.isdir(d):
            continue
        if argv and not any(os.path.basename(d).startswith(p) for p in argv):
            continue
        r = parse_run(d)
        if r:
            rows.append(r)
    if not rows:
        sys.exit("no runs found")
    # a filtered listing (name prefixes given) is print-only unless --csv names a file,
    # so that it never overwrites the complete results/summary.csv
    if not argv or out != OUT:
        with open(out, "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
            w.writeheader(); w.writerows(rows)
    else:
        out = "(print only)"
    hdr = ["run", "insts", "cycles", "CPI", "L1D miss%", "L1D AMAT", "L2 miss%", "DRAM rd", "DTLB miss%", "faults"]
    print(f"{hdr[0]:<30}{hdr[1]:>10}{hdr[2]:>12}{hdr[3]:>7}{hdr[4]:>10}{hdr[5]:>9}{hdr[6]:>9}{hdr[7]:>9}{hdr[8]:>11}{hdr[9]:>7}")
    for r in rows:
        print(f"{r['name']:<30}{r['insts']:>10,}{r['cycles']:>12,}{r['cpi']:>7.2f}{100*r['l1d_mr']:>10.2f}"
              f"{r['l1d_amat']:>9.2f}{100*r['l2_mr']:>9.1f}{r['dram_rd']:>9,}{100*r['dtlb_mr']:>11.2f}{r['page_faults']:>7,}")
    print(f"\n{len(rows)} runs -> {out}", file=sys.stderr)

if __name__ == "__main__":
    main()
