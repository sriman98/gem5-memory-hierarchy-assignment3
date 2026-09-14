#!/bin/bash
# run_experiments.sh <spec.tsv> [parallel-jobs]
# Each non-comment line of the spec file is:
#   name <TAB> gem5-options <TAB> script(memhier|stock) <TAB> config-arguments
# (gem5-options is the word NONE when there are none: xargs -0 would drop an empty field)
# Runs them through run_one.sh, N at a time (default 12).
R=$(cd "$(dirname "$0")/.." && pwd)
spec=$1; P=${2:-12}
grep -v '^#' "$spec" | grep -v '^[[:space:]]*$' |
  while IFS=$'\t' read -r name gopts script cargs; do
    printf '%s\0%s\0%s\0%s\0' "$name" "$gopts" "$script" "$cargs"
  done | xargs -0 -P "$P" -n 4 "$R/scripts/run_one.sh"
