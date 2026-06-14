#!/bin/bash
# Benchmark script for expr lab3
cd "$(dirname "$0")"

NS=(20 40 60 70 75 80 85 90 95 100)
TS=(1 2 3 4 5 8 10)

echo "N,T,answer,time_ms"
for N in "${NS[@]}"; do
    for T in "${TS[@]}"; do
        printf "%d\n%d\n" "$T" "$N" > input.txt
        ./expr
        ANS=$(sed -n '3p' output.txt)
        TM=$(cat time.txt)
        echo "$N,$T,$ANS,$TM"
    done
done
