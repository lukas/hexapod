#!/bin/bash
# Run a python script detached: bash run_bg.sh <name> <script> [args...]
set -u
name=$1; shift
mkdir -p /data/logs /data/results
nohup python3 "$@" > /data/logs/$name.log 2>&1 &
echo "$name pid $! log /data/logs/$name.log"
