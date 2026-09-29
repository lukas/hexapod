#!/bin/bash
# One-time pod setup: extra python deps + background model downloads.
set -u
mkdir -p /data/jobs /data/logs /data/hf /data/results
cd /data
{
  echo "== $(date -u) setup start"
  nvidia-smi --query-gpu=name,memory.total,memory.used --format=csv
  python3 -c 'import torch, vllm, transformers; print("torch", torch.__version__, "vllm", vllm.__version__, "transformers", transformers.__version__)'
  pip install -q --no-cache-dir av opencv-python-headless scikit-learn pandas pyarrow hf_transfer qwen-vl-utils 2>&1 | tail -3
  python3 - <<'PY'
from huggingface_hub import snapshot_download
for m in ["Qwen/Qwen3-VL-8B-Instruct", "facebook/dinov2-giant", "Qwen/Qwen3-VL-32B-Instruct-FP8"]:
    p = snapshot_download(m, max_workers=16)
    print("downloaded", m, "->", p, flush=True)
PY
  echo "== $(date -u) setup done"
} > /data/logs/setup.log 2>&1 &
echo "setup running in background; log /data/logs/setup.log"
