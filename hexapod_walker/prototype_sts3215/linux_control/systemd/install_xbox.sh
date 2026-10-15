#!/usr/bin/env bash
# Run on the Uno Q after deploying the HTTP gamepad client and lease support.
# Opt-in: installing the web service alone does not enable gamepad control.
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"

cd "$HERE/.."
/home/arduino/.local/bin/uv run python - <<'PY'
import json
import urllib.request

with urllib.request.urlopen("http://127.0.0.1:8080/api/ping", timeout=3) as response:
    info = json.load(response)
if info.get("scripted_gamepad_lease", {}).get("version") != 1:
    raise SystemExit("Deploy and restart hexapod-web with gamepad lease support before installing Xbox control.")
PY

sudo systemctl enable --now bluetooth.service
sudo install -m 644 "$HERE/hexapod-xbox.service" /etc/systemd/system/hexapod-xbox.service
sudo systemctl daemon-reload
sudo systemctl enable hexapod-xbox.service
sudo systemctl restart hexapod-xbox.service
sudo systemctl --no-pager --full status hexapod-xbox.service
echo 'Xbox control enabled on boot. Pair the controller once with bluetoothctl; see README.md.'
