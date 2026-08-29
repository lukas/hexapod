#!/usr/bin/env bash
# Run motor setup on the Uno Q (MCU UART bridge) or a laptop (USB URT).
#
#   ./run.sh                 # interactive menu
#   ./run.sh --status
#   ./run.sh --port mcu
#   ./run.sh --port /dev/ttyUSB0
#
# On the Uno Q, web_drive owns /dev/ttyHS1 — this script stops it for the
# session and restarts it afterward.
#
# (Moved from linux_control/urt2_setup/ 2026-08-29: the on-board
# urt2_setup bundle was a checked-in duplicate of this directory and was
# retired; motor_setup itself now deploys to the board.)
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
ROOT="$(cd "$HERE/.." && pwd)"
LC="$ROOT/linux_control"
REMOTE_HOME="${HOME}/hexapod_sts/linux_control"
UV_BIN="${UV_BIN:-${HOME}/.local/bin/uv}"
export PYTHONPATH="${LC}/vendor:${HERE}:${LC}:${ROOT}:${REMOTE_HOME}:${PYTHONPATH:-}"
export PYTHONUNBUFFERED=1
export HEXAPOD_BUS_PORT="${HEXAPOD_BUS_PORT:-mcu}"

WEB_WAS_RUNNING=0
restart_web() {
  if [ "$WEB_WAS_RUNNING" -eq 1 ]; then
    echo ">> restarting web_drive on MCU bridge ..."
    (
      cd "$LC"
      PYTHONUNBUFFERED=1 \
      PYTHONPATH="${LC}/vendor:${HERE}:${LC}:${ROOT}:${PYTHONPATH:-}" \
      nohup "$UV_BIN" run python web_drive.py --port mcu --http-port 8080 --https-port 8443 \
        >/tmp/hexapod_web.log 2>&1 </dev/null &
    ) || true
  fi
}
trap restart_web EXIT

if pgrep -f '[w]eb_drive.py' >/dev/null 2>&1; then
  WEB_WAS_RUNNING=1
  echo ">> stopping web_drive (needs exclusive bus) ..."
  pkill -f '[w]eb_drive.py' || true
  sleep 0.4
fi

exec "$UV_BIN" run python "${HERE}/urt2_motor_setup.py" "$@"
