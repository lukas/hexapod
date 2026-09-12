#!/bin/bash
# Start a vLLM OpenAI server in the background.  Usage: bash 10_vllm_serve.sh <32b|8b>
set -u
which=${1:-32b}
case "$which" in
  32b) MODEL=Qwen/Qwen3-VL-32B-Instruct-FP8; NAME=qwen3vl-32b; PORT=8000; UTIL=0.50 ;;
  8b)  MODEL=Qwen/Qwen3-VL-8B-Instruct;      NAME=qwen3vl-8b;  PORT=8001; UTIL=0.22 ;;
  *) echo "unknown $which"; exit 1 ;;
esac
mkdir -p /data/logs
nohup python3 -m vllm.entrypoints.openai.api_server \
  --model "$MODEL" --served-model-name "$NAME" --port "$PORT" --host 127.0.0.1 \
  --gpu-memory-utilization "$UTIL" --max-model-len 40960 --max-num-seqs 16 \
  --limit-mm-per-prompt '{"image":64,"video":1}' --allowed-local-media-path /data \
  --trust-remote-code \
  > /data/logs/vllm_$which.log 2>&1 &
echo "vllm $which pid $! log /data/logs/vllm_$which.log"
