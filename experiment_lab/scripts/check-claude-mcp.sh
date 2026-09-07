#!/bin/sh
# Prove the Claude engineering lane's MCP servers actually authenticate.
#
# Loads the same three bearer values the orchestrator passes and reports each
# server's connection status from Claude's own session-init event, rather than
# asking the model to describe it. Exits non-zero if any server failed, so it
# can gate a cutover.
set -eu

CONFIG="${1:-$(cd "$(dirname "$0")/.." && pwd)/deploy/claude-mcp.json}"
[ -f "$CONFIG" ] || { echo "no mcp config at $CONFIG" >&2; exit 1; }

get() { /usr/bin/security find-generic-password -a operator -s "$1" -w 2>/dev/null || true; }

BUILDVIZ_API_KEY="$(get 'BuildViz API')"
HEXAPOD_ORCHESTRATOR_TOKEN="$(get 'Hexapod Orchestrator MCP')"
HEXAPOD_LAB_TOKEN="$(get 'Hexapod Lab API')"
export BUILDVIZ_API_KEY HEXAPOD_ORCHESTRATOR_TOKEN HEXAPOD_LAB_TOKEN

for pair in "BUILDVIZ_API_KEY:BuildViz API" \
            "HEXAPOD_ORCHESTRATOR_TOKEN:Hexapod Orchestrator MCP" \
            "HEXAPOD_LAB_TOKEN:Hexapod Lab API"; do
  name="${pair%%:*}"
  eval "value=\$$name"
  [ -n "$value" ] || echo "warning: Keychain item '${pair#*:}' is empty or missing" >&2
done

claude -p --tools "" --strict-mcp-config --mcp-config "$CONFIG" \
  --setting-sources "" --permission-prompts none --no-session-persistence \
  --output-format stream-json --verbose 'ok' < /dev/null 2>/dev/null \
  | /usr/bin/env python3 -c '
import json, sys
servers = None
for line in sys.stdin:
    try:
        event = json.loads(line)
    except ValueError:
        continue
    if event.get("type") == "system" and event.get("subtype") == "init":
        servers = event.get("mcp_servers") or []
        break
if servers is None:
    print("no session-init event; claude did not start")
    raise SystemExit(2)
failed = [s for s in servers if s.get("status") != "connected"]
for s in servers:
    mark = "ok  " if s.get("status") == "connected" else "FAIL"
    print("  %s %s: %s" % (mark, s.get("name"), s.get("status")))
if not servers:
    print("  no MCP servers registered at all")
    raise SystemExit(2)
raise SystemExit(1 if failed else 0)
'
