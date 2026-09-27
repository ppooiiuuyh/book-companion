#!/usr/bin/env bash
# 사용: run_tesseract.sh <lang> <psm> <outdir>   예) run_tesseract.sh kor 4 outputs/tesseract_kor_psm4
set -e; lang=$1; psm=$2; out=$3; mkdir -p "$out"; : > "$out/times.txt"
for img in pages/*.jpeg; do p=$(basename "$img" .jpeg); s=$(date +%s.%N)
  tesseract "$img" "$out/$p" -l "$lang" --psm "$psm" >/dev/null 2>&1
  e=$(date +%s.%N); echo "$p $(echo "$e-$s" | bc)" >> "$out/times.txt"; done
