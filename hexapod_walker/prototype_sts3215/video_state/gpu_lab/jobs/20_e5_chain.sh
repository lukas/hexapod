#!/bin/bash
# E5 chain: repo CNN at 2x res on crops, then DINOv2-base fine-tune, both splits. Detached; logs in /data/logs/e5_*.log
mkdir -p /data/logs
nohup bash -c '
python3 /data/jobs/e5_finetune.py --model cnn  --epochs 15 --bs 128 > /data/logs/e5_cnn.log 2>&1
python3 /data/jobs/e5_finetune.py --model vitb --epochs 6  --bs 64  > /data/logs/e5_vitb.log 2>&1
echo E5_CHAIN_DONE >> /data/logs/e5_vitb.log
' > /dev/null 2>&1 &
echo "e5 chain pid $!"
