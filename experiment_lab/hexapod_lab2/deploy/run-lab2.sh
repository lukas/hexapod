#!/bin/sh
# Robot Lab v2 loop launcher. launchd has no shell profile, so the Claude
# credential is resolved here: environment, then the operator's login shell,
# then Keychain. Nothing is echoed.
set -eu
export PATH="/opt/homebrew/bin:/usr/local/bin:$HOME/.local/bin:/usr/bin:/bin"
V="$HOME/Library/Application Support/Hexapod Lab/venv"
export HEXAPOD_LAB2_DATA_DIR="${HEXAPOD_LAB2_DATA_DIR:-$HOME/Library/Application Support/Hexapod Lab/v2}"
export HEXAPOD_LAB2_CLAUDE_BIN="${HEXAPOD_LAB2_CLAUDE_BIN:-$HOME/.local/bin/claude}"
if [ -z "${ANTHROPIC_API_KEY:-}" ]; then
  ANTHROPIC_API_KEY="$(/bin/zsh -lic 'printf %s "$ANTHROPIC_API_KEY"' 2>/dev/null || true)"
fi
if [ -z "${ANTHROPIC_API_KEY:-}" ]; then
  ANTHROPIC_API_KEY="$(/usr/bin/security find-generic-password -a operator -s 'Hexapod Claude API' -w 2>/dev/null || true)"
fi
export ANTHROPIC_API_KEY
exec "$V/bin/hexapod-lab2" loop
