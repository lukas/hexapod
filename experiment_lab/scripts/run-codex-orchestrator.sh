#!/bin/sh
set -eu
umask 077

# Load only the two MCP credentials the project engineering role needs. The
# analysis and queue-review roles still receive a filtered child environment,
# and Codex excludes these values from model-generated shell commands.
LAB_TOKEN="$(/usr/bin/security find-generic-password -a operator -s 'Hexapod Lab API' -w)"
ORCHESTRATOR_TOKEN="$(/usr/bin/security find-generic-password -a operator -s 'Hexapod Orchestrator MCP' -w)"

# Replace the inherited launchd environment at exec time so unrelated secrets
# never become ambient inputs to any role.
# Background launchd jobs can block on macOS privacy checks while opening a
# Documents checkout, including through a linked-worktree `.git` pointer. Use
# the self-contained clean integration clone in Application Support for the
# action-capable engineering lane; it still has normal network, BuildViz,
# robot, git, and filesystem access.
exec /usr/bin/env -i \
  HOME="/Users/lukas" \
  USER="lukas" \
  LOGNAME="lukas" \
  SHELL="/bin/zsh" \
  LANG="en_US.UTF-8" \
  PATH="/Applications/ChatGPT.app/Contents/Resources:/opt/homebrew/bin:/usr/local/bin:/Users/lukas/.local/bin:/usr/bin:/bin:/usr/sbin:/sbin" \
  CODEX_HOME="/Users/lukas/.codex" \
  HEXAPOD_DATA_DIR="/Users/lukas/Library/Application Support/Hexapod Lab/data" \
  HEXAPOD_CODEX_AUTOMATION="true" \
  HEXAPOD_CODEX_BIN="/Applications/ChatGPT.app/Contents/Resources/codex" \
  HEXAPOD_CODEX_WORKDIR="/Users/lukas/Library/Application Support/Hexapod Lab/codex-workspace" \
  HEXAPOD_CODEX_ENGINEERING="true" \
  HEXAPOD_CODEX_ENGINEERING_WORKDIR="/Users/lukas/Library/Application Support/Hexapod Lab/engineering-checkout-v1" \
  HEXAPOD_LAB_TOKEN="$LAB_TOKEN" \
  HEXAPOD_ORCHESTRATOR_TOKEN="$ORCHESTRATOR_TOKEN" \
  HEXAPOD_CODEX_MODEL="gpt-5.6-sol" \
  HEXAPOD_CODEX_REASONING_EFFORT="medium" \
  HEXAPOD_CODEX_EVIDENCE_SETTLE_SECONDS="60" \
  HEXAPOD_CODEX_EVIDENCE_DEADLINE_SECONDS="1800" \
  "/Users/lukas/Library/Application Support/Hexapod Lab/venv/bin/hexapod-codex-orchestrator"
