#!/bin/sh
# Choose which coding-agent CLI the Hexapod Lab orchestrator drives.
#
#   ./switch-agent-provider.sh claude            # switch, restart by hand
#   ./switch-agent-provider.sh codex --restart   # switch back and restart now
#
# The orchestrator reads this file at launch, so the change takes effect on
# the next service start. Restarting is deliberately opt-in: the engineering
# lane can be mid-run against the physical robot.
set -eu

SUPPORT="${HEXAPOD_LAB_SUPPORT:-/Users/lukas/Library/Application Support/Hexapod Lab}"
SERVICE="com.lbiewald.hexapod-codex-orchestrator"

provider="${1:-}"
restart="${2:-}"
case "$provider" in
  codex|claude) ;;
  *)
    echo "usage: $(basename "$0") codex|claude [--restart]" >&2
    exit 2
    ;;
esac

if [ "$provider" = "claude" ]; then
  if ! command -v claude >/dev/null 2>&1; then
    echo "claude CLI not found on PATH; install it before switching" >&2
    exit 1
  fi
  if [ ! -f "$SUPPORT/claude-mcp.json" ]; then
    echo "missing $SUPPORT/claude-mcp.json; copy it from deploy/claude-mcp.json" >&2
    exit 1
  fi
fi

umask 077
printf '%s\n' "$provider" > "$SUPPORT/agent-provider"
echo "Agent provider set to $provider."

if [ "$restart" = "--restart" ]; then
  launchctl kickstart -k "gui/$(id -u)/$SERVICE"
  echo "Restarted $SERVICE."
else
  echo "Restart the orchestrator to pick it up:"
  echo "  launchctl kickstart -k gui/$(id -u)/$SERVICE"
fi
