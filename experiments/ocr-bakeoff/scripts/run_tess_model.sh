#!/usr/bin/env bash
# run_tess_model.sh <model_dir> <psm> <outname> <reps>
md=$1; psm=$2; out=outputs/$3; reps=${4:-1}; mkdir -p $out; : > $out/times.txt
for p in p005 p009 p016 p023 p041; do
  for r in $(seq 1 $reps); do s=$(date +%s.%N)
    OMP_THREAD_LIMIT=1 tesseract pages/$p.jpeg $out/$p --tessdata-dir $md -l kor --psm $psm >/dev/null 2>&1
    e=$(date +%s.%N); echo "$p $r $(echo "$e-$s"|bc)" >> $out/times.txt; done; done
