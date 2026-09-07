#!/usr/bin/env python3
"""Install the Codex/Claude backend switch into the running Lab deployment.

The launchd service reads its whole environment from `run-codex-orchestrator.sh`
under Application Support, and that installed copy legitimately drifts from the
one in this repo (its own engineering checkout, its own reasoning effort). So
this adds the provider block to whatever is installed instead of overwriting
it, and refuses to run twice.

    python3 scripts/install-agent-switch.py [--support DIR] [--dry-run]

Installing changes nothing on its own: the block defaults to `codex`, and the
service keeps using Codex until `switch-agent-provider.sh claude` runs.
"""

from __future__ import annotations

import argparse
from datetime import datetime
from pathlib import Path
import shutil
import sys


DEFAULT_SUPPORT = Path.home() / "Library/Application Support/Hexapod Lab"
ANCHOR = "# Replace the inherited launchd environment at exec time so unrelated secrets"
TOKEN_LINE = '  HEXAPOD_ORCHESTRATOR_TOKEN="$ORCHESTRATOR_TOKEN" \\\n'

PRELUDE = '''# Agent backend for all three automation lanes: "codex" (the default and the
# historical behaviour) or "claude". Switch with
# `./switch-agent-provider.sh claude` and restart this service; the value
# lives in a one-line file so the launchd plist never has to change.
AGENT_PROVIDER="codex"
PROVIDER_FILE="{support}/agent-provider"
if [ -f "$PROVIDER_FILE" ]; then
  AGENT_PROVIDER="$(tr -d '[:space:]' < "$PROVIDER_FILE")"
fi

# Claude Code expands ${{VAR}} into its MCP request headers itself, so these
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

'''

ENV_LINES = '''  HEXAPOD_AGENT_PROVIDER="$AGENT_PROVIDER" \\
  HEXAPOD_CLAUDE_BIN="{claude_bin}" \\
  HEXAPOD_CLAUDE_MODEL="claude-opus-5" \\
  HEXAPOD_CLAUDE_EFFORT="high" \\
  HEXAPOD_CLAUDE_MCP_CONFIG="{support}/claude-mcp.json" \\
  BUILDVIZ_API_KEY="$BUILDVIZ_KEY" \\
  ANTHROPIC_API_KEY="$CLAUDE_API_KEY" \\
'''


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--support", type=Path, default=DEFAULT_SUPPORT)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    repo = Path(__file__).resolve().parent.parent
    support = args.support
    launcher = support / "run-codex-orchestrator.sh"
    if not launcher.is_file():
        print(f"no launcher at {launcher}", file=sys.stderr)
        return 1

    claude_bin = shutil.which("claude")
    if not claude_bin:
        print("claude CLI not found on PATH", file=sys.stderr)
        return 1

    text = launcher.read_text()
    if "HEXAPOD_AGENT_PROVIDER" in text:
        print(f"launcher already has the provider block: {launcher}")
    else:
        if ANCHOR not in text or TOKEN_LINE not in text:
            print(
                "launcher does not match the expected layout; add the block by "
                "hand using scripts/run-codex-orchestrator.sh as the reference",
                file=sys.stderr,
            )
            return 1
        prelude = PRELUDE.format(support=support)
        env_lines = ENV_LINES.format(support=support, claude_bin=claude_bin)
        text = text.replace(ANCHOR, prelude + ANCHOR, 1)
        text = text.replace(TOKEN_LINE, TOKEN_LINE + env_lines, 1)
        stamp = datetime.now().strftime("%Y%m%dT%H%M%S")
        backup = launcher.with_name(f"{launcher.name}.before-agent-switch-{stamp}")
        if args.dry_run:
            print(f"[dry-run] would back up to {backup.name} and patch {launcher}")
        else:
            shutil.copy2(launcher, backup)
            launcher.write_text(text)
            print(f"patched {launcher} (backup: {backup.name})")

    for source, mode in (
        (repo / "deploy/claude-mcp.json", 0o600),
        (repo / "scripts/switch-agent-provider.sh", 0o700),
    ):
        destination = support / source.name
        if args.dry_run:
            print(f"[dry-run] would install {destination}")
            continue
        shutil.copyfile(source, destination)
        destination.chmod(mode)
        print(f"installed {destination}")

    print(
        "\nStill on Codex. Switch with:\n"
        f'  "{support}/switch-agent-provider.sh" claude --restart'
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
