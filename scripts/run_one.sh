#!/bin/bash
# run_one.sh <name> "<gem5 options>" <script> "<config arguments>"
#   script = memhier -> configs/memhier_config.py (this repository)
#            stock   -> gem5's configs/deprecated/example/se.py (the baseline)
# Runs one simulation into results/runs/<name>/ (stats.txt, config.ini, run.log,
# cmdline.txt) and appends a line to results/runs/_done.log when it finishes.
set -u
R=$(cd "$(dirname "$0")/.." && pwd)
GEM5_ROOT=${GEM5_ROOT:-$HOME/git/gem5}
G=${GEM5:-$GEM5_ROOT/build/X86/gem5.opt}
name=$1; gopts=$2; script=$3; cargs=$4
[ "$gopts" = "NONE" ] && gopts=""      # NONE = no extra gem5 options (xargs -0 drops empty fields)
case "$script" in
  stock) S=$GEM5_ROOT/configs/deprecated/example/se.py ;;
  *)     S=$R/configs/memhier_config.py ;;
esac
out=$R/results/runs/$name
mkdir -p "$out"
cd "$R"
echo "$G --outdir=$out $gopts $S $cargs" > "$out/cmdline.txt"
start=$(date +%s)
# eval so that quoted argument groups such as  -o '96 0'  (se.py) survive
eval "$G --outdir=$out $gopts $S $cargs" > "$out/run.log" 2>&1
rc=$?
echo "rc=$rc" >> "$out/cmdline.txt"
echo "$name rc=$rc $(( $(date +%s) - start ))s" >> "$R/results/runs/_done.log"
exit 0
