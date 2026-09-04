#!/bin/sh
set -eu

LAB_TOKEN="$(/usr/bin/security find-generic-password -a operator -s 'Hexapod Lab API' -w)"
ASSISTANTS_TOKEN="$(/usr/bin/security find-generic-password -a assistants -s 'Hexapod Lab API' -w)"
MOBILE_TOKEN="$(/usr/bin/security find-generic-password -a viewer -s 'Hexapod Research Mobile' -w)"
export HEXAPOD_API_KEYS="operator:operator:${LAB_TOKEN},operator:assistants:${ASSISTANTS_TOKEN},viewer:iphone:${MOBILE_TOKEN}"
export HEXAPOD_DATA_DIR="/Users/lukas/Library/Application Support/Hexapod Lab/data"
export HEXAPOD_BIND="127.0.0.1"
export HEXAPOD_PORT="8767"
export HEXAPOD_PUBLIC_BASE_URL="https://robot-lab.cwd1f0-new-cluster.coreweave.app"
export HEXAPOD_DRIVER="simulated"
# This setting is parsed as an argv; keep the executable path shell-quoted
# inside the value because the Application Support path contains spaces.
export HEXAPOD_TAG_AUDIT_COMMAND="'/Users/lukas/Library/Application Support/Hexapod Lab/venv/bin/hexapod-audit-layout'"
export HEXAPOD_TAG_LAYOUT="/Users/lukas/Library/Application Support/Hexapod Lab/tag-scan-config/hexapod-1-apriltag-layout.json"
export HEXAPOD_TAG_POSE_TEMPLATE="/Users/lukas/Library/Application Support/Hexapod Lab/tag-scan-config/apriltag_pose_config_20260831.json"
export HEXAPOD_TAG_FLOOR_MAP="/Users/lukas/Library/Application Support/Hexapod Lab/tag-scan-config/floor_tag_map.json"
export HEXAPOD_TAG_PART_MAP="/Users/lukas/Library/Application Support/Hexapod Lab/tag-scan-config/hexapod_tag_map.json"

exec "/Users/lukas/Library/Application Support/Hexapod Lab/venv/bin/hexapod-lab"
