#!/bin/sh
set -eu
umask 077

# Load only the two MCP credentials the project engineering role needs. The
# analysis and queue-review roles still receive a filtered child environment,
# and Codex excludes these values from model-generated shell commands.
LAB_TOKEN="$(/usr/bin/security find-generic-password -a operator -s 'Hexapod Lab API' -w)"
ORCHESTRATOR_TOKEN="$(/usr/bin/security find-generic-password -a operator -s 'Hexapod Orchestrator MCP' -w)"

# Agent backend for all three automation lanes: "codex" (the default and the
# historical behaviour) or "claude". Switch with
# `./switch-agent-provider.sh claude` and restart this service; the value
# lives in a one-line file so the launchd plist never has to change.
AGENT_PROVIDER="codex"
PROVIDER_FILE="/Users/lukas/Library/Application Support/Hexapod Lab/agent-provider"
if [ -f "$PROVIDER_FILE" ]; then
  AGENT_PROVIDER="$(tr -d '[:space:]' < "$PROVIDER_FILE")"
fi

# Claude Code expands ${VAR} into its MCP request headers itself, so these
# bearer values never reach the mcp config file or a child's argv. Both are
# optional: an unset Keychain item leaves the value empty, and the Lab drops
# empty variables when it builds the child environment.
BUILDVIZ_KEY=""
CLAUDE_API_KEY=""
if [ "$AGENT_PROVIDER" = "claude" ]; then
  BUILDVIZ_KEY="$(/usr/bin/security find-generic-password -a operator -s 'BuildViz API' -w 2>/dev/null || true)"
  # Only needed if Claude Code's own OAuth credentials in the login Keychain
  # are not reachable from a launchd background job.
  CLAUDE_API_KEY="$(/usr/bin/security find-generic-password -a operator -s 'Hexapod Claude API' -w 2>/dev/null || true)"
fi

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
  HEXAPOD_CODEX_ENGINEERING_WORKDIR="/Users/lukas/Library/Application Support/Hexapod Lab/engineering-checkout-v3" \
  HEXAPOD_CODEX_OFFLINE_ENGINEERING_WORKDIR="/Users/lukas/Library/Application Support/Hexapod Lab/engineering-offline-v1" \
  HEXAPOD_LAB_TOKEN="$LAB_TOKEN" \
  HEXAPOD_ORCHESTRATOR_TOKEN="$ORCHESTRATOR_TOKEN" \
  HEXAPOD_AGENT_PROVIDER="$AGENT_PROVIDER" \
  HEXAPOD_CLAUDE_BIN="/Users/lukas/.local/bin/claude" \
  HEXAPOD_CLAUDE_MODEL="claude-opus-5" \
  HEXAPOD_CLAUDE_EFFORT="high" \
  HEXAPOD_CLAUDE_MCP_CONFIG="/Users/lukas/Library/Application Support/Hexapod Lab/claude-mcp.json" \
  BUILDVIZ_API_KEY="$BUILDVIZ_KEY" \
  ANTHROPIC_API_KEY="$CLAUDE_API_KEY" \
  HEXAPOD_CODEX_MODEL="gpt-5.6-sol" \
  HEXAPOD_CODEX_REASONING_EFFORT="medium" \
  HEXAPOD_CODEX_EVIDENCE_SETTLE_SECONDS="60" \
  HEXAPOD_CODEX_EVIDENCE_DEADLINE_SECONDS="1800" \
  "/Users/lukas/Library/Application Support/Hexapod Lab/venv/bin/hexapod-codex-orchestrator"
