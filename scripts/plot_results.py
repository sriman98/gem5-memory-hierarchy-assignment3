#!/usr/bin/env python3
"""plot_results.py -- charts for the Part 2 report, from results/summary.csv -> figures/*.png

Colors follow the workload (same hue for the same program in every chart) and come
from a colorblind-validated categorical palette; every panel has one y axis.
"""
import csv
import os
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

R = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FIG = os.path.join(R, "figures")
os.makedirs(FIG, exist_ok=True)

# validated categorical palette (slot order is the CVD-safety mechanism)
SLOT = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300", "#4a3aa7", "#e34948"]
WLCOL = {"matmul": SLOT[0], "stream": SLOT[1], "stride": SLOT[2], "chase": SLOT[3],
         "chase4m": SLOT[4], "pagewalk": SLOT[5], "matmulb": SLOT[6], "hello": SLOT[7]}
WLNAME = {"matmul": "matmul (naive)", "matmulb": "matmul (blocked)", "stream": "stream", "stride": "stride",
          "chase": "chase 1 MiB", "chase4m": "chase 4 MiB", "pagewalk": "pagewalk", "hello": "hello"}
WLSHORT = {"matmul": "matmul", "matmulb": "matmul-blk", "stream": "stream", "stride": "stride",
           "chase": "chase 1M", "chase4m": "chase 4M", "pagewalk": "pagewalk", "hello": "hello"}
INK, INK2, GRID = "#0b0b0b", "#52514e", "#dddcd8"
plt.rcParams.update({"font.size": 9, "axes.edgecolor": GRID, "axes.labelcolor": INK2, "xtick.color": INK2,
                     "ytick.color": INK2, "axes.titlesize": 10, "axes.titleweight": "bold", "axes.titlecolor": INK,
                     "legend.frameon": False, "figure.dpi": 150, "savefig.dpi": 150, "axes.grid": True,
                     "grid.color": GRID, "grid.linewidth": 0.8, "axes.axisbelow": True})

S = list(csv.DictReader(open(os.path.join(R, "results", "summary.csv"))))
for r in S:
    for k, v in r.items():
        if k not in ("name", "exp", "variant", "workload", "rc", "program_output"):
            try: r[k] = float(v)
            except ValueError: pass
BY = {r["name"]: r for r in S}
def get(exp, variant, wl):
    return BY.get(f"{exp}_{variant}_{wl}")
def series(exp, variants, wl, key):
    out = []
    for v in variants:
        r = get(exp, v, wl); out.append(r[key] if r else np.nan)
    return np.array(out, dtype=float)

def style(ax, title, xlabel, ylabel, logx=False, ylim0=True):
    ax.set_title(title, loc="left"); ax.set_xlabel(xlabel); ax.set_ylabel(ylabel)
    for s in ("top", "right"): ax.spines[s].set_visible(False)
    ax.grid(axis="x", visible=False)
    if logx: ax.set_xscale("log", base=2)
    if ylim0: ax.set_ylim(bottom=0)

def line_panels(fname, xs, xlabels, panels, wls, exp, variants, suptitle=None, logx=True, xlabel="", legend_ax=0, legend_loc="best"):
    """panels = [(title, key, ylabel, scale)] ; one line per workload per panel."""
    fig, axes = plt.subplots(1, len(panels), figsize=(6.6, 2.9 if len(panels) > 1 else 3.2))
    axes = np.atleast_1d(axes)
    for ax, (title, key, ylabel, scale) in zip(axes, panels):
        for wl in wls:
            y = series(exp, variants, wl, key) * scale
            ax.plot(xs, y, color=WLCOL[wl], lw=2, marker="o", ms=5.5, mec="white", mew=1.2, label=WLNAME[wl],
                    solid_joinstyle="round")
        style(ax, title, xlabel, ylabel, logx=logx)
        ax.set_xticks(xs); ax.set_xticklabels(xlabels, rotation=0)
        ax.minorticks_off()
    axes[legend_ax].legend(loc=legend_loc, fontsize=8)
    if suptitle: fig.suptitle(suptitle, x=0.01, ha="left", fontsize=10, fontweight="bold")
    fig.tight_layout()
    fig.savefig(os.path.join(FIG, fname)); plt.close(fig); print("wrote", fname)

def grouped_bars(fname, groups, cats, values, colors, ylabel, title, catlabels=None, fmt="{:.2f}", figsize=(6.6, 3.0),
                 label_bars=True, panels=None):
    """groups on the x axis (e.g. workloads), one bar per category (e.g. configuration) inside each group.
    values[c][g] ; panels: optional list of (title, values, ylabel, fmt) for several panels sharing groups/cats."""
    if panels is None:
        panels = [(title, values, ylabel, fmt)]
    fig, axes = plt.subplots(1, len(panels), figsize=(figsize[0], figsize[1]))
    axes = np.atleast_1d(axes)
    n, m = len(groups), len(cats)
    width = min(0.8 / m, 0.22)
    x = np.arange(n)
    for ax, (ttl, vals, yl, f) in zip(axes, panels):
        for ci, c in enumerate(cats):
            off = (ci - (m - 1) / 2) * width
            v = np.array([vals[c][g] for g in groups], dtype=float)
            bars = ax.bar(x + off, v, width * 0.9, color=colors[ci], label=(catlabels or {}).get(c, c), zorder=3)
            if label_bars and n * m <= 24:
                for b, val in zip(bars, v):
                    if not np.isnan(val):
                        ax.text(b.get_x() + b.get_width() / 2, b.get_height(), f.format(val), ha="center", va="bottom",
                                fontsize=6.5, color=INK2)
        ax.set_xticks(x); ax.set_xticklabels([WLSHORT.get(g, g) for g in groups], fontsize=8)
        style(ax, ttl, "", yl)
        ax.margins(y=0.12)
    fig.legend(*axes[0].get_legend_handles_labels(), loc="lower center", bbox_to_anchor=(0.5, 0.0), ncol=min(m, 4), fontsize=7.5, frameon=False)
    fig.tight_layout(rect=(0, 0.1 if m <= 4 else 0.16, 1, 1))
    fig.savefig(os.path.join(FIG, fname)); plt.close(fig); print("wrote", fname)

# ---------------------------------------------------------------- charts
def kib(s):
    n = int(s[:-3]); return n * (1024 if s.endswith("MiB") else 1)

def chart_wset():
    v = ["16KiB", "32KiB", "64KiB", "128KiB", "256KiB", "512KiB", "1024KiB", "2048KiB", "4096KiB", "8192KiB"]
    xs = [kib(x) for x in v]; xl = ["16K", "32K", "64K", "128K", "256K", "512K", "1M", "2M", "4M", "8M"]
    fig, axes = plt.subplots(1, 2, figsize=(6.6, 2.9))
    for ax, (title, key, yl, sc) in zip(axes, [("L1D miss rate", "l1d_mr", "misses / access (%)", 100),
                                              ("Cycles per instruction", "cpi", "CPI", 1)]):
        y = series("wset", v, "chase", key) * sc
        ax.plot(xs, y, color=WLCOL["chase"], lw=2, marker="o", ms=5.5, mec="white", mew=1.2)
        style(ax, title, "footprint of the pointer chase", yl, logx=True)
        top = ax.get_ylim()[1]
        for cap, lab in [(64, "L1D 64 KiB"), (2048, "L2 2 MiB")]:
            ax.axvline(cap, color=INK2, lw=0.8, ls=(0, (3, 3))); ax.text(cap * 1.1, top * 0.98, lab, fontsize=7, color=INK2, rotation=90, va="top", ha="left")
        ax.set_xticks(xs); ax.set_xticklabels(xl, fontsize=7); ax.minorticks_off()
    fig.tight_layout(); fig.savefig(os.path.join(FIG, "chart_wset.png")); plt.close(fig); print("wrote chart_wset.png")

def chart_l1dsize():
    v = ["8KiB", "16KiB", "32KiB", "64KiB", "128KiB", "256KiB"]
    line_panels("chart_l1dsize.png", [kib(x) for x in v], ["8K", "16K", "32K", "64K", "128K", "256K"],
                [("L1D miss rate", "l1d_mr", "misses / access (%)", 100), ("Cycles per instruction", "cpi", "CPI", 1)],
                ["matmul", "matmulb", "stream", "stride", "chase"], "l1dsize", v, xlabel="L1D size (2-way)")

def chart_l1dassoc():
    v = ["1way", "2way", "4way", "8way", "16way"]
    line_panels("chart_l1dassoc.png", [1, 2, 4, 8, 16], ["1", "2", "4", "8", "16"],
                [("L1D miss rate", "l1d_mr", "misses / access (%)", 100), ("Cycles per instruction", "cpi", "CPI", 1)],
                ["matmul", "stream", "stride", "chase"], "l1dassoc", v, xlabel="L1D associativity (ways, 64 KiB)")

def chart_line():
    v = ["16B", "32B", "64B", "128B", "256B"]
    line_panels("chart_line.png", [16, 32, 64, 128, 256], ["16", "32", "64", "128", "256"],
                [("L1D miss rate", "l1d_mr", "misses / access (%)", 100), ("DRAM read requests", "dram_rd", "requests (thousands)", 1e-3),
                 ("CPI", "cpi", "CPI", 1)],
                ["matmul", "stream", "stride", "chase"], "line", v, xlabel="cache line size (bytes)")

def chart_l2size():
    v = ["256KiB", "512KiB", "1MiB", "2MiB", "4MiB", "8MiB"]
    line_panels("chart_l2size.png", [kib(x) for x in v], ["256K", "512K", "1M", "2M", "4M", "8M"],
                [("L2 miss rate", "l2_mr", "misses / L2 access (%)", 100), ("Cycles per instruction", "cpi", "CPI", 1)],
                ["matmul", "stream", "chase", "chase4m"], "l2size", v, xlabel="L2 size (8-way)")

def chart_pf():
    cats = ["none-none", "tagged-none", "stride-none", "none-tagged", "none-stride", "stride-stride"]
    labels = {"none-none": "no prefetcher", "tagged-none": "L1D next-line", "stride-none": "L1D stride",
              "none-tagged": "L2 next-line", "none-stride": "L2 stride", "stride-stride": "L1D + L2 stride"}
    groups = ["matmul", "stream", "stride", "chase", "chase4m"]
    cpi = {c: {g: (get("pf", c, g) or {}).get("cpi", np.nan) for g in groups} for c in cats}
    mr = {c: {g: 100 * (get("pf", c, g) or {}).get("l1d_mr", np.nan) for g in groups} for c in cats}
    grouped_bars("chart_pf.png", groups, cats, None, SLOT[:6], "", "", catlabels=labels, figsize=(6.6, 3.1), label_bars=False,
                 panels=[("Cycles per instruction", cpi, "CPI", "{:.2f}"), ("L1D miss rate", mr, "misses / access (%)", "{:.1f}")])

def chart_repl():
    cats = ["lru", "random", "treeplru", "fifo", "rrip", "nru"]
    labels = {"lru": "LRU", "random": "Random", "treeplru": "Tree-PLRU", "fifo": "FIFO", "rrip": "RRIP", "nru": "NRU"}
    groups = ["matmul", "stride", "chase", "chase4m"]
    l1 = {c: {g: 100 * (get("repl", c, g) or {}).get("l1d_mr", np.nan) for g in groups} for c in cats}
    l2 = {c: {g: 100 * (get("repl", c, g) or {}).get("l2_mr", np.nan) for g in groups} for c in cats}
    grouped_bars("chart_repl.png", groups, cats, None, SLOT[:6], "", "", catlabels=labels, figsize=(6.6, 3.1), label_bars=False,
                 panels=[("L1D miss rate", l1, "misses / access (%)", "{:.1f}"), ("L2 miss rate", l2, "misses / L2 access (%)", "{:.1f}")])

def chart_victim():
    cats = ["dm", "dm+v4", "dm+v8", "dm+v16", "2way", "2way+v8", "8way"]
    labels = {"dm": "direct-mapped", "dm+v4": "DM + 4-line victim", "dm+v8": "DM + 8-line victim", "dm+v16": "DM + 16-line victim",
              "2way": "2-way", "2way+v8": "2-way + 8-line victim", "8way": "8-way"}
    groups = ["stride", "matmul", "chase"]
    cpi = {c: {g: (get("victim", c, g) or {}).get("cpi", np.nan) for g in groups} for c in cats}
    mr = {c: {g: 100 * (get("victim", c, g) or {}).get("l1d_mr", np.nan) for g in groups} for c in cats}
    grouped_bars("chart_victim.png", groups, cats, None, SLOT[:7], "", "", catlabels=labels, figsize=(6.6, 3.2), label_bars=False,
                 panels=[("Cycles per instruction", cpi, "CPI", "{:.2f}"), ("L1D miss rate", mr, "misses / access (%)", "{:.1f}")])

def chart_l1lat():
    v = ["32KiB-2c", "64KiB-2c", "64KiB-3c", "128KiB-3c", "128KiB-4c", "256KiB-4c", "256KiB-5c"]
    xl = ["32K\n2 cyc", "64K\n2 cyc", "64K\n3 cyc", "128K\n3 cyc", "128K\n4 cyc", "256K\n4 cyc", "256K\n5 cyc"]
    fig, axes = plt.subplots(1, 2, figsize=(6.6, 3.0))
    for ax, (title, key, yl, sc) in zip(axes, [("Cycles per instruction", "cpi", "CPI", 1), ("L1D average memory access time", "l1d_amat", "AMAT (cycles)", 1)]):
        for wl in ["matmul", "matmulb", "chase", "stream"]:
            ax.plot(range(len(v)), series("l1lat", v, wl, key) * sc, color=WLCOL[wl], lw=2, marker="o", ms=5.5, mec="white", mew=1.2, label=WLNAME[wl])
        style(ax, title, "L1D size and hit latency", yl); ax.set_xticks(range(len(v))); ax.set_xticklabels(xl, fontsize=7)
    axes[0].legend(fontsize=8); fig.tight_layout(); fig.savefig(os.path.join(FIG, "chart_l1lat.png")); plt.close(fig); print("wrote chart_l1lat.png")

def chart_tlb():
    v = ["8e", "16e", "32e", "64e", "128e", "256e", "512e", "1024e"]
    line_panels("chart_tlb.png", [8, 16, 32, 64, 128, 256, 512, 1024], ["8", "16", "32", "64", "128", "256", "512", "1K"],
                [("Data TLB miss rate", "dtlb_mr", "misses / access (%)", 100), ("Cycles per instruction", "cpi", "CPI", 1)],
                ["pagewalk", "chase4m", "stream", "matmul"], "tlb", v, xlabel="data TLB entries (4 KiB pages, 30-cycle walk)", legend_ax=1, legend_loc="center right")

def chart_tlblat():
    v = ["0c", "10c", "30c", "60c", "100c"]
    line_panels("chart_tlblat.png", [0, 10, 30, 60, 100], ["0", "10", "30", "60", "100"],
                [("Cycles per instruction", "cpi", "CPI", 1), ("Share of cycles spent in TLB misses", "penalty_frac", "% of cycles", 100)],
                ["pagewalk", "chase4m", "stream"], "tlblat", v, logx=False, xlabel="TLB miss penalty (cycles, 64-entry DTLB)")

def chart_page():
    v = ["4KiB", "16KiB", "64KiB", "256KiB", "2MiB"]
    wls = ["pagewalk", "chase4m", "stream", "matmul"]
    fig, axes = plt.subplots(1, 3, figsize=(6.6, 2.9))
    for ax, (title, key, yl, sc, logy) in zip(axes, [("Data TLB misses", "dtlb_miss", "misses (log scale)", 1, True),
                                                    ("First-touch page faults", "page_faults", "faults (log scale)", 1, True),
                                                    ("CPI", "cpi", "CPI", 1, False)]):
        for wl in wls:
            y = series("page", v, wl, key) * sc
            if logy: y = np.where(y <= 0, 0.5, y)
            ax.plot(range(len(v)), y, color=WLCOL[wl], lw=2, marker="o", ms=5.5, mec="white", mew=1.2, label=WLNAME[wl])
        style(ax, title, "page size", yl, ylim0=not logy)
        if logy: ax.set_yscale("log")
        ax.set_xticks(range(len(v))); ax.set_xticklabels(["4K", "16K", "64K", "256K", "2M"], fontsize=7.5)
    axes[2].legend(fontsize=7.5); fig.tight_layout(); fig.savefig(os.path.join(FIG, "chart_page.png")); plt.close(fig); print("wrote chart_page.png")

def chart_opt():
    groups = ["matmul", "matmulb", "stream", "stride", "chase", "chase4m", "pagewalk"]
    cats = ["base", "opt"]
    vals = {"base": {g: (get("base", "default", g) or {}).get("cpi", np.nan) for g in groups},
            "opt": {g: (get("opt", "combined", g) or {}).get("cpi", np.nan) for g in groups}}
    fig, ax = plt.subplots(figsize=(6.6, 3.0))
    x = np.arange(len(groups)); w = 0.36
    for i, (c, col, lab) in enumerate([("base", "#9ec5f4", "gem5 default caches"), ("opt", SLOT[0], "optimized configuration")]):
        v = np.array([vals[c][g] for g in groups]); ax.bar(x + (i - 0.5) * w, v, w * 0.92, color=col, label=lab, zorder=3)
    for i, g in enumerate(groups):
        b, o = vals["base"][g], vals["opt"][g]
        if not (np.isnan(b) or np.isnan(o)):
            ax.text(x[i], max(b, o) * 1.03, f"{b / o:.2f}×", ha="center", fontsize=7.5, color=INK)
    ax.set_xticks(x); ax.set_xticklabels([WLSHORT[g] for g in groups], fontsize=8)
    style(ax, "CPI: gem5 default caches versus the optimized configuration (labels: speedup)", "", "CPI")
    ax.margins(y=0.15); ax.legend(fontsize=8); fig.tight_layout(); fig.savefig(os.path.join(FIG, "chart_opt.png")); plt.close(fig); print("wrote chart_opt.png")

def chart_o3():
    groups = ["matmul", "stream", "stride", "chase"]
    cats = [("base", "default", "in-order, default caches"), ("opt", "combined", "in-order, optimized"),
            ("o3", "default", "out-of-order, default caches"), ("o3", "pf", "out-of-order, L1D+L2 stride prefetch")]
    fig, ax = plt.subplots(figsize=(6.6, 3.0))
    x = np.arange(len(groups)); w = 0.2
    for i, (e, v, lab) in enumerate(cats):
        vals = np.array([(get(e, v, g) or {}).get("cpi", np.nan) for g in groups], dtype=float)
        ax.bar(x + (i - 1.5) * w, vals, w * 0.9, color=SLOT[i], label=lab, zorder=3)
        for xi, val in zip(x + (i - 1.5) * w, vals):
            if not np.isnan(val): ax.text(xi, val, f"{val:.2f}", ha="center", va="bottom", fontsize=6.5, color=INK2)
    ax.set_xticks(x); ax.set_xticklabels([WLSHORT[g] for g in groups])
    style(ax, "Cycles per instruction on the in-order and out-of-order cores", "", "CPI"); ax.margins(y=0.25)
    ax.legend(fontsize=7.5, ncol=2, loc="upper left"); fig.tight_layout(); fig.savefig(os.path.join(FIG, "chart_o3.png")); plt.close(fig); print("wrote chart_o3.png")

if __name__ == "__main__":
    which = sys.argv[1:] 
    for name, fn in list(globals().items()):
        if name.startswith("chart_") and callable(fn) and (not which or name in which):
            try: fn()
            except Exception as e: print("FAILED", name, repr(e))
