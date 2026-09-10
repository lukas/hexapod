#!/bin/sh
# One-time setup: dedicated origin/main checkout with its own venv, launcher,
# LaunchAgent. Re-runnable. Does not start the loop.
set -eu
export PATH="/opt/homebrew/bin:/usr/local/bin:$HOME/.local/bin:/usr/bin:/bin"
HERE="$(cd "$(dirname "$0")" && pwd)"
LAB="$HOME/Library/Application Support/Hexapod Lab"
V2="$LAB/v2"
mkdir -p "$V2/runs" "$HOME/Library/LaunchAgents" "$HOME/Library/Logs"
if [ ! -d "$V2/checkout/.git" ]; then
  git clone -q https://github.com/lukas/hexapod.git "$V2/checkout"
fi
git -C "$V2/checkout" checkout -q main
git -C "$V2/checkout" pull -q --ff-only
(cd "$V2/checkout" && uv sync --frozen -q)
uv pip install -q --python "$LAB/venv/bin/python" --no-deps "$HERE/../.."
install -m 700 "$HERE/run-lab2.sh" "$LAB/run-lab2.sh"
install -m 600 "$HERE/com.lbiewald.hexapod-lab2.plist" "$HOME/Library/LaunchAgents/com.lbiewald.hexapod-lab2.plist"
echo "installed. start:  launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/com.lbiewald.hexapod-lab2.plist"
echo "           stop:   launchctl bootout gui/$(id -u)/com.lbiewald.hexapod-lab2"
echo "           pause:  touch '$V2/PAUSE'"
