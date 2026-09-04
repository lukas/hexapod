#!/bin/sh
set -eu

export HEXAPOD_ALERT_RECIPIENT="$(/usr/bin/security find-generic-password -a recipient -s 'Hexapod Blocker Alerts' -w)"
export HEXAPOD_ORCHESTRATOR_TOKEN="$(/usr/bin/security find-generic-password -a operator -s 'Hexapod Orchestrator MCP' -w)"
export HEXAPOD_LAB_VIEWER_TOKEN="$(/usr/bin/security find-generic-password -a viewer -s 'Hexapod Research Mobile' -w)"
export HEXAPOD_DATA_DIR="/Users/lukas/Library/Application Support/Hexapod Lab/data"

exec "/Users/lukas/Library/Application Support/Hexapod Lab/venv/bin/hexapod-blocker-monitor"
