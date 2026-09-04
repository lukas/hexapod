#!/bin/sh
set -eu

LAB_TOKEN="$(/usr/bin/security find-generic-password -a operator -s 'Hexapod Lab API' -w)"
MOBILE_TOKEN="$(/usr/bin/security find-generic-password -a viewer -s 'Hexapod Research Mobile' -w)"
export HEXAPOD_API_KEYS="operator:operator:${LAB_TOKEN},viewer:iphone:${MOBILE_TOKEN}"
export HEXAPOD_DATA_DIR="/Users/lukas/Library/Application Support/Hexapod Lab/data"
export HEXAPOD_BIND="127.0.0.1"
export HEXAPOD_PORT="8767"
export HEXAPOD_PUBLIC_BASE_URL="https://robot-lab.cwd1f0-new-cluster.coreweave.app"
export HEXAPOD_DRIVER="simulated"

exec "/Users/lukas/Library/Application Support/Hexapod Lab/venv/bin/hexapod-lab"
