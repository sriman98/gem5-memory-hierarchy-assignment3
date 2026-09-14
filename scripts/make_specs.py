#!/usr/bin/env python3
"""make_specs.py <experiment|all> -- write the run matrices (results/specs/<exp>.tsv).

Each line: name <TAB> gem5-options <TAB> script <TAB> config-arguments.
Run names are  <experiment>_<variant>_<workload>  (variants never contain '_').
"""
import os
import sys

R = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SPECS = os.path.join(R, "results", "specs")

# workload -> memhier --cmd argument (binary:args)
WL = {
    "hello":    "bin/hello",
    "matmul":   "bin/matmul:96:0",            # naive i-j-k, 3 x 72 KiB
    "matmulb":  "bin/matmul:96:16",           # 16x16 blocked (software optimization)
    "stream":   "bin/stream:524288:2",        # 4 MiB sequential, 1 write + 2 read passes
    "stride":   "bin/stride:32768:8:200000",  # 8 lines, 32 KiB apart -> one L1D set
    "chase":    "bin/chase:1024:500000",      # 1 MiB random pointer chase
    "chase4m":  "bin/chase:4096:500000",      # 4 MiB: L2-missing, 1,024 pages
    "pagewalk": "bin/pagewalk:512:500000",    # 512 pages, 32 KiB of lines: TLB only
}
CORE = ["matmul", "matmulb", "stream", "stride", "chase", "chase4m", "pagewalk"]

def stock_cargs(wl):
    """gem5's own se.py with its default caches: the assignment's baseline."""
    b, *a = WL[wl].split(":")
    s = f"--cpu-type=TimingSimpleCPU --caches --l2cache --mem-size=1GiB -c {b}"
    if a:
        s += " -o '" + " ".join(a) + "'"
    return s

VM = "--l1d-assoc 16"                    # see the virtual-memory note below
OPT = ("--l1d-size 64KiB --l1d-assoc 8 --l1d-pf tagged "     # 8 ways: no conflicts; next-line L1D prefetch
       "--l2-size 4MiB --l2-assoc 16 --l2-pf stride")        # L2 holds the 4 MiB working sets; stride prefetch

rows = []
def add(exp, variant, wl, opts=""):
    rows.append((f"{exp}_{variant}_{wl}", "NONE", "memhier", f"{opts} --cmd {WL[wl]}".strip()))

def build(exp):
    rows.clear()
    if exp == "stock":                        # 1. gem5 default caches, stock script
        for wl in ["hello"] + CORE:
            rows.append((f"stock_default_{wl}", "NONE", "stock", stock_cargs(wl)))
    elif exp == "base":                       # my script, no options: must match stock
        for wl in ["hello"] + CORE:
            add("base", "default", wl)
    elif exp == "l1dsize":
        for s in ["8KiB", "16KiB", "32KiB", "64KiB", "128KiB", "256KiB"]:
            for wl in ["matmul", "matmulb", "stream", "stride", "chase"]:
                add("l1dsize", s, wl, f"--l1d-size {s}")
    elif exp == "l1dassoc":
        for a in [1, 2, 4, 8, 16]:
            for wl in ["matmul", "stream", "stride", "chase"]:
                add("l1dassoc", f"{a}way", wl, f"--l1d-assoc {a}")
    elif exp == "line":
        for b in [16, 32, 64, 128, 256]:
            for wl in ["matmul", "stream", "stride", "chase"]:
                add("line", f"{b}B", wl, f"--line {b}")
    elif exp == "l2size":
        for s in ["256KiB", "512KiB", "1MiB", "2MiB", "4MiB", "8MiB"]:
            for wl in ["matmul", "stream", "chase", "chase4m"]:
                add("l2size", s, wl, f"--l2-size {s}")
    elif exp == "l2assoc":
        for a in [1, 2, 4, 8, 16]:
            for wl in ["matmul", "chase4m"]:
                add("l2assoc", f"{a}way", wl, f"--l2-assoc {a}")
    elif exp == "wset":                       # working-set sweep of the pointer chase
        for kib in [16, 32, 64, 128, 256, 512, 1024, 2048, 4096, 8192]:
            rows.append((f"wset_{kib}KiB_chase", "NONE", "memhier", f"--cmd bin/chase:{kib}:500000"))
    elif exp == "pf":                         # prefetchers (L1D / L2)
        for l1, l2 in [("none", "none"), ("tagged", "none"), ("stride", "none"),
                       ("none", "tagged"), ("none", "stride"), ("stride", "stride")]:
            for wl in ["matmul", "stream", "stride", "chase", "chase4m"]:
                add("pf", f"{l1}-{l2}", wl, f"--l1d-pf {l1} --l2-pf {l2}")
        for d in [1, 2, 4, 8]:
            for wl in ["stream", "matmul"]:
                add("pfdeg", f"stride{d}", wl, f"--l2-pf stride --pf-degree {d}")
    elif exp == "repl":
        for r in ["lru", "random", "treeplru", "fifo", "rrip", "nru"]:
            for wl in ["matmul", "stride", "chase", "chase4m"]:
                add("repl", r, wl, f"--l1d-repl {r} --l2-repl {r}")
    elif exp == "victim":                     # direct-mapped L1D +/- victim buffer vs. more ways
        for v, opts in [("dm", "--l1d-assoc 1"), ("dm+v4", "--l1d-assoc 1 --victim 4"),
                        ("dm+v8", "--l1d-assoc 1 --victim 8"), ("dm+v16", "--l1d-assoc 1 --victim 16"),
                        ("2way", "--l1d-assoc 2"), ("2way+v8", "--l1d-assoc 2 --victim 8"),
                        ("8way", "--l1d-assoc 8")]:
            for wl in ["stride", "matmul", "chase"]:
                add("victim", v, wl, opts)
    elif exp == "l1lat":                      # size vs. hit latency trade-off
        for s, lat in [("32KiB", 2), ("64KiB", 2), ("64KiB", 3), ("128KiB", 3),
                       ("128KiB", 4), ("256KiB", 4), ("256KiB", 5)]:
            for wl in ["matmul", "matmulb", "chase", "stream"]:
                add("l1lat", f"{s}-{lat}c", wl, f"--l1d-size {s} --l1-lat {lat}")
    # Virtual-memory experiments use a 16-way 64 KiB L1D: its way size (4 KiB) equals the
    # base page, so the set index comes from the page offset only and the physically indexed
    # cache behaves identically whatever the page size or frame placement (isolates translation).
    elif exp == "tlb":                        # TLB reach, with a 30-cycle walk penalty
        for n in [8, 16, 32, 64, 128, 256, 512, 1024]:
            for wl in ["pagewalk", "chase4m", "stream", "matmul"]:
                add("tlb", f"{n}e", wl, f"{VM} --dtlb {n} --tlb-miss-lat 30")
    elif exp == "tlblat":                     # how much a walk costs
        for lat in [0, 10, 30, 60, 100]:
            for wl in ["pagewalk", "chase4m", "stream"]:
                add("tlblat", f"{lat}c", wl, f"{VM} --tlb-miss-lat {lat}")
    elif exp == "page":                       # page size, 64-entry TLB, 30-cycle walk, 2000-cycle fault
        for ps in ["4KiB", "16KiB", "64KiB", "256KiB", "2MiB"]:
            for wl in ["pagewalk", "chase4m", "stream", "matmul"]:
                add("page", ps, wl, f"{VM} --page-size {ps} --tlb-miss-lat 30 --fault-lat 2000")
        for ps in ["4KiB", "16KiB", "64KiB", "256KiB", "2MiB"]:   # same without the fault cost
            for wl in ["pagewalk", "chase4m"]:
                add("pagenf", ps, wl, f"{VM} --page-size {ps} --tlb-miss-lat 30")
    elif exp == "o3":                         # out-of-order core: memory-level parallelism
        for v, opts in [("default", ""), ("l1d32k8w", "--l1d-size 32KiB --l1d-assoc 8"),
                        ("pf", "--l1d-pf stride --l2-pf stride")]:
            for wl in ["matmul", "stream", "stride", "chase"]:
                add("o3", v, wl, f"--cpu o3 {opts}".strip())
    elif exp == "opt":                        # the combined "optimized" configuration (chosen from the sweeps)
        for wl in CORE:
            add("opt", "combined", wl, OPT)
            add("opt", "line128", wl, OPT + " --line 128")
    else:
        sys.exit(f"unknown experiment {exp}")
    os.makedirs(SPECS, exist_ok=True)
    p = os.path.join(SPECS, f"{exp}.tsv")
    with open(p, "w") as f:
        f.write(f"# {exp}: name\\tgem5-options\\tscript\\tconfig-arguments\n")
        for r in rows:
            f.write("\t".join(r) + "\n")
    print(f"{p}: {len(rows)} runs")

ALL = ["stock", "base", "l1dsize", "l1dassoc", "line", "l2size", "l2assoc", "wset", "pf",
       "repl", "victim", "l1lat", "tlb", "tlblat", "page", "o3", "opt"]
if __name__ == "__main__":
    what = sys.argv[1:] or ["all"]
    for w in (ALL if what == ["all"] else what):
        build(w)
