#!/bin/zsh
# Result-dependent Terminal.app screenshots for the Part 2 report (raw captures -> report/shots/raw).
R=~/git/gem5-memory-hierarchy-assignment3; S=$R/tools/shot.sh; O=$R/report/shots/raw; cd $R
FONT=12 $S $O/fig_runs_dir.png 30 118 1 "ls results/runs | wc -l; ls results/runs | head -300 | column -c 116 | head -24; echo; ls results/runs/opt_combined_stream"
FONT=12 $S $O/fig_run_opt.png 16 118 1 "grep -v '^warn\|^info\|^\$' results/runs/opt_combined_stream/run.log | tail -8 | cut -c1-116; grep -E '^(system.cpu.numCycles|system.cpu.cpi)' results/runs/opt_combined_stream/stats.txt results/runs/base_default_stream/stats.txt | cut -c1-116"
FONT=12 $S $O/fig_tlb_stats.png 22 118 1 "grep -E '^(system.cpu.numCycles|system.cpu.cpi|system.cpu.mmu.dtb.(rdAccesses|wrAccesses|rdMisses|wrMisses|pageFaults|penaltyCycles)|system.cpu.mmu.itb.(exAccesses|exMisses|pageFaults))' results/runs/tlb_64e_pagewalk/stats.txt | cut -c1-116; echo; grep -A4 '^\[system.cpu.mmu.dtb\]' results/runs/tlb_64e_pagewalk/config.ini | grep -E '^\[|size|latency'"
FONT=11 $S $O/fig_table_tlb.png 40 132 1 "python3 scripts/parse_stats.py tlb_ tlblat 2>/dev/null | cut -c1-130"
FONT=11 $S $O/fig_table_page.png 36 132 1 "python3 scripts/parse_stats.py page 2>/dev/null | cut -c1-130"
FONT=11 $S $O/fig_table_opt.png 28 132 1 "python3 scripts/parse_stats.py base opt o3 2>/dev/null | cut -c1-130"
FONT=11 $S $O/fig_table_l1d.png 58 132 1 "python3 scripts/parse_stats.py l1dsize l1dassoc line 2>/dev/null | cut -c1-130"
FONT=11 $S $O/fig_table_l2.png 40 132 1 "python3 scripts/parse_stats.py l2size l2assoc wset 2>/dev/null | cut -c1-130"
FONT=11 $S $O/fig_table_pf.png 44 132 1 "python3 scripts/parse_stats.py pf 2>/dev/null | cut -c1-130"
FONT=11 $S $O/fig_table_repl_victim.png 50 132 1 "python3 scripts/parse_stats.py repl victim 2>/dev/null | cut -c1-130"
FONT=11 $S $O/fig_table_l1lat.png 32 132 1 "python3 scripts/parse_stats.py l1lat 2>/dev/null | cut -c1-130"
