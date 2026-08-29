#!/usr/bin/env bash
# Deploy STS3215 linux_control to the Uno Q over USB adb and start the web UI.
#
#   ./deploy_adb.sh              # push + start (dry-run if no URT-2 yet)
#   ./deploy_adb.sh --bus        # require a real Feetech bus adapter
#   ./deploy_adb.sh --stop       # stop the web server on the board
#
# Then on the Mac:
#   adb forward tcp:8080 tcp:8080
#   adb forward tcp:8443 tcp:8443
#   open http://127.0.0.1:8080
#   # Xbox on the Mac → https://127.0.0.1:8443  (accept cert warning)
set -euo pipefail

SRC="$(cd "$(dirname "$0")" && pwd)"
REMOTE="/home/arduino/hexapod_sts"
REMOTE_UV="/home/arduino/.local/bin/uv"
MODE="start"
NEED_BUS=0
for a in "$@"; do
  case "$a" in
    --stop) MODE="stop" ;;
    --bus) NEED_BUS=1 ;;
  esac
done

# Serialize deploys across workspaces (lock ~/.hexapod/deploy.lock,
# history ~/.hexapod/deploy.log — see deploy_lock.sh).
source "$SRC/deploy_lock.sh"
deploy_lock_acquire "adb $MODE"

echo ">> waiting for Uno Q over adb ..."
adb wait-for-device
adb shell 'echo connected as $(whoami) on $(hostname)'

if [ "$MODE" = "stop" ]; then
  adb shell 'pkill -f "[w]eb_drive.py" || true'
  echo ">> stopped"
  exit 0
fi

# Stage the EXACT remote layout locally (shared manifest — same tree as
# deploy_ssh.sh), then push it in one recursive adb push.
echo ">> staging deploy tree (deploy_manifest.sh)"
source "$SRC/deploy_manifest.sh"
STAGE="$(mktemp -d /tmp/hexapod_deploy.XXXXXX)"
trap 'rm -rf "$STAGE"; deploy_lock_release' EXIT
stage_deploy_tree "$STAGE" "$SRC"

echo ">> pushing code + vendored SDK → $REMOTE"
# rm -rf clears the retired urt2_setup bundles (push does not delete
# stale remote files).
adb shell "mkdir -p '$REMOTE' && \
  rm -rf '$REMOTE/urt2_setup' '$REMOTE/linux_control/urt2_setup'"
adb push "$STAGE/." "$REMOTE/"

BUS_ARGS=""
DRY=""
if [ "$NEED_BUS" -eq 0 ]; then
  # Prefer MCU UART bridge (FE-URT on D0/D1); else USB URT; else dry-run.
  if adb shell 'test -e /dev/ttyHS1' >/dev/null 2>&1; then
    echo ">> using MCU Feetech bridge (/dev/ttyHS1)"
    BUS_ARGS="--port mcu"
  elif adb shell 'ls /dev/ttyUSB* /dev/ttyCH343USB* 2>/dev/null | head -1' | grep -q .; then
    echo ">> using USB Feetech adapter"
  else
    echo ">> no bus yet — starting with --dry-run"
    echo "   (flash feetech_bridge + wire URT UART→D0/D1, or plug USB URT)"
    DRY="--dry-run"
  fi
else
  BUS_ARGS="--port mcu"
fi

paint_deploy_screen() {
  adb shell "cd '$REMOTE/linux_control' && \
    PYTHONPATH='$REMOTE/linux_control/vendor:$REMOTE/motor_setup:$REMOTE/linux_control:$REMOTE' \
    '$REMOTE_UV' run python deploy_status_display.py \
      --title DEPLOYING \
      --line 'code updated' \
      --line 'web restarting' \
      --line 'please wait' \
      --footer 'screen will resume'" >/dev/null 2>&1 || true
}

echo ">> ensuring uv on Uno Q"
adb shell "set -e; if [ ! -x '$REMOTE_UV' ]; then curl -LsSf https://astral.sh/uv/install.sh | sh; fi; '$REMOTE_UV' --version"

echo ">> restarting web_drive.py"
# Prefer the boot-enabled systemd unit when present.
if adb shell 'systemctl is-enabled hexapod-web.service >/dev/null 2>&1'; then
  adb shell 'echo arduino | sudo -S systemctl stop hexapod-web.service' >/dev/null || true
  adb shell "echo arduino | sudo -S cp '$REMOTE/linux_control/systemd/hexapod-web.service' /etc/systemd/system/hexapod-web.service && echo arduino | sudo -S systemctl daemon-reload" >/dev/null
  paint_deploy_screen
  adb shell 'echo arduino | sudo -S systemctl start hexapod-web.service' >/dev/null
  sleep 5
  adb shell 'systemctl --no-pager -l status hexapod-web.service | head -20 || true'
else
  adb shell "pkill -f '[w]eb_drive.py' || true" >/dev/null || true
  paint_deploy_screen
  # Detach cleanly — a bare `adb shell '... &'` can hang until the child exits.
  adb shell "sh -c 'cd \"$REMOTE/linux_control\" && \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=\"$REMOTE/linux_control/vendor:$REMOTE/motor_setup:$REMOTE/linux_control:$REMOTE\" \
    nohup \"$REMOTE_UV\" run python web_drive.py $DRY $BUS_ARGS --http-port 8080 --https-port 8443 \
    >/tmp/hexapod_web.log 2>&1 </dev/null & echo started_pid=\$!'"
  sleep 1.5
  adb shell 'tail -n 30 /tmp/hexapod_web.log || true'
fi

adb forward --remove-all >/dev/null 2>&1 || true
adb forward tcp:8080 tcp:8080
adb forward tcp:8443 tcp:8443
curl -fsS -m 3 -X POST http://127.0.0.1:8080/api/tft/ready \
  >/dev/null 2>&1 || true

echo ">> log / listen:"
adb shell 'journalctl -u hexapod-web -n 20 --no-pager 2>/dev/null || tail -n 30 /tmp/hexapod_web.log || true'
adb shell 'ss -tln 2>/dev/null | grep -E ":8080|:8443" || netstat -tln 2>/dev/null | grep -E ":8080|:8443" || true'
echo
echo ">> open on this Mac:"
echo "     http://127.0.0.1:8080"
echo "     https://127.0.0.1:8443   (Xbox / Gamepad API — accept cert warning)"
echo ">> live log:  adb shell 'tail -f /tmp/hexapod_web.log'"
