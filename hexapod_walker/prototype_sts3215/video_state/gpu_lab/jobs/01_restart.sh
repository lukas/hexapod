#!/bin/bash
# After a container restart: reinstall pip extras (container FS is ephemeral; /data is not) and bring both servers back.
set -u
mkdir -p /data/logs
{
  echo "== $(date -u) restart"
  pip install -q --no-cache-dir av opencv-python-headless scikit-learn pandas pyarrow qwen-vl-utils 2>&1 | tail -2
  bash /data/jobs/10_vllm_serve.sh 32b
  bash /data/jobs/10_vllm_serve.sh 8b
} >> /data/logs/restart.log 2>&1
tail -n 3 /data/logs/restart.log
