#!/usr/bin/env bash
# Canonical local Mac launcher for the standalone vision service on :8766.
#
# This is the camera and pose estimator only. It has no way to arm or move the
# robot: --robot-url is read with GET /api/feedback for the joint overlay and
# nothing else. Restarting this service does not touch the robot bridge on
# :8898 -- that separation is the whole point of running it here.
#
# The hub on :8898 keeps serving /vision by proxying this port; start this
# first, then run hexapod_web_8898.sh with SIM_WEB_VISION_PROXY set.
set -euo pipefail

SELF="$(cd "$(dirname "$0")" && pwd)/$(basename "$0")"
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
LABEL="${HEXAPOD_VISION8766_LABEL:-com.lukas.hexapod-vision-8766}"
PORT="${VISION_PORT:-8766}"
BIND="${VISION_BIND:-127.0.0.1}"
LOG="${HEXAPOD_VISION8766_LOG:-/tmp/hexapod_vision_8766.log}"
CAMERA="${VISION_CAMERA:-0}"
CAMERA_CYCLE="${VISION_CAMERA_CYCLE:-0,1}"
CAPTURE_WIDTH="${VISION_CAPTURE_WIDTH:-1920}"
CAPTURE_HEIGHT="${VISION_CAPTURE_HEIGHT:-1440}"
CAPTURE_FPS="${VISION_CAPTURE_FPS:-30}"
TARGET_FPS="${VISION_TARGET_FPS:-10}"
UV_BIN="${UV:-$(command -v uv || true)}"

if [[ -z "$UV_BIN" ]]; then
  if [[ -x /opt/homebrew/bin/uv ]]; then
    UV_BIN=/opt/homebrew/bin/uv
  else
    echo "uv not found. Install uv or set UV=/path/to/uv." >&2
    exit 127
  fi
fi

usage() {
  cat <<EOF
Usage: sim_viewer/hexapod_vision_8766.sh <command>

Commands:
  start       Start the vision service on http://${BIND}:${PORT}
  stop        Stop the launchctl job and any stale service on that port
  restart     Stop, then start
  status      Show launchctl, port, health and agent usage
  logs        Tail ${LOG}
  foreground  Run in the foreground with uv run

Pages:
  http://${BIND}:${PORT}/vision   live camera and pose UI
  http://${BIND}:${PORT}/agent    vision agent log and token usage
  http://${BIND}:${PORT}/api/agent/usage   same numbers as JSON

Environment:
  HEXAPOD_HOST=http://<robot-ip-or-name>:8080   joint overlay source
  VISION_BIND=${BIND}                           bind address
  VISION_PORT=${PORT}                           local port
  VISION_CAMERA=${CAMERA}                       starting camera index
  VISION_CAMERA_CYCLE=${CAMERA_CYCLE}           selectable camera indexes
  VISION_CAPTURE_WIDTH=${CAPTURE_WIDTH}         capture width
  VISION_CAPTURE_HEIGHT=${CAPTURE_HEIGHT}       capture height
  VISION_CAPTURE_FPS=${CAPTURE_FPS}             capture rate
  VISION_TARGET_FPS=${TARGET_FPS}               processing rate
  HEXAPOD_DATA_DIR=...                          Robot Lab data directory
EOF
}

normalize_url() {
  local url="$1"
  if [[ "$url" != http://* && "$url" != https://* ]]; then
    url="http://$url"
  fi
  printf '%s\n' "$url"
}

robot_url() {
  if [[ -n "${HEXAPOD_HOST:-}" ]]; then
    normalize_url "$HEXAPOD_HOST"
    return
  fi
  if [[ -n "${ROBOT_URL:-}" ]]; then
    normalize_url "$ROBOT_URL"
    return
  fi

  local ip="" cache="${HEXAPOD_IP_CACHE:-$HOME/.hexapod/last_ip}"
  if [[ -s "$cache" ]]; then
    ip="$(head -n 1 "$cache")"
    if [[ -n "$ip" ]]; then
      printf 'http://%s:8080\n' "$ip"
      return
    fi
  fi
  ip="$(bash "$ROOT/linux_control/dev_loop.sh" resolve 2>/dev/null || true)"
  if [[ -n "$ip" ]]; then
    printf 'http://%s:8080\n' "$ip"
  else
    printf 'http://hexapod.local:8080\n'
  fi
}

listener_pid() {
  lsof -tiTCP:"${1:-$PORT}" -sTCP:LISTEN 2>/dev/null | head -n 1 || true
}

listener_command() {
  local pid="$1"
  [[ -n "$pid" ]] || return 0
  ps -p "$pid" -o command= 2>/dev/null || true
}

wait_ready() {
  local health="http://${BIND}:${PORT}/healthz"
  local i
  for i in {1..80}; do
    if curl -fsS -m 2 "$health" >/dev/null 2>&1; then
      echo "ready: http://${BIND}:${PORT}/vision"
      echo "agent: http://${BIND}:${PORT}/agent"
      return 0
    fi
    sleep 0.25
  done
  echo "vision service did not become ready. Recent log:" >&2
  tail -80 "$LOG" >&2 2>/dev/null || true
  return 1
}

stop_port_if_ours() {
  local pid cmd
  pid="$(listener_pid "$PORT")"
  [[ -n "$pid" ]] || return 0
  cmd="$(listener_command "$pid")"
  if [[ "$cmd" == *"linux_control/vision_service.py"* ]]; then
    /bin/kill "$pid" 2>/dev/null || true
  else
    echo "port ${PORT} is in use by another process:" >&2
    echo "  $cmd" >&2
    return 1
  fi
}

serve() {
  local bind="$1" port="$2" url="$3" log="$4" camera="$5" cycle="$6"
  local cap_w="$7" cap_h="$8" cap_fps="$9" target_fps="${10}"
  cd "$ROOT"
  exec >>"$log" 2>&1
  echo "[$(date -u '+%Y-%m-%dT%H:%M:%SZ')] starting vision service on ${bind}:${port}"
  echo "joint overlay source: ${url} (read-only)"
  exec "$UV_BIN" run python linux_control/vision_service.py \
    --bind "$bind" \
    --port "$port" \
    --robot-url "$url" \
    --vision-camera "$camera" \
    --vision-camera-cycle "$cycle" \
    --vision-capture-width "$cap_w" \
    --vision-capture-height "$cap_h" \
    --vision-capture-fps "$cap_fps" \
    --vision-target-fps "$target_fps"
}

start() {
  local url pid cmd
  url="$(robot_url)"
  pid="$(listener_pid "$PORT")"
  if [[ -n "$pid" ]]; then
    cmd="$(listener_command "$pid")"
    if [[ "$cmd" != *"linux_control/vision_service.py"* ]]; then
      echo "port ${PORT} is in use by another process:" >&2
      echo "  $cmd" >&2
      return 1
    fi
    if curl -fsS -m 2 "http://${BIND}:${PORT}/healthz" >/dev/null 2>&1; then
      echo "already listening on :${PORT}:"
      echo "$cmd"
      wait_ready
      return
    fi
    echo "existing vision service is unhealthy; restarting it"
    launchctl remove "$LABEL" >/dev/null 2>&1 || true
    stop_port_if_ours
  fi

  launchctl remove "$LABEL" >/dev/null 2>&1 || true
  echo "starting $LABEL with uv run..."
  launchctl submit -l "$LABEL" -- /bin/bash "$SELF" serve \
    "$BIND" "$PORT" "$url" "$LOG" "$CAMERA" "$CAMERA_CYCLE" \
    "$CAPTURE_WIDTH" "$CAPTURE_HEIGHT" "$CAPTURE_FPS" "$TARGET_FPS"
  wait_ready
}

stop() {
  launchctl remove "$LABEL" >/dev/null 2>&1 || true
  stop_port_if_ours || return
  echo "stopped $LABEL"
}

status() {
  echo "label: $LABEL"
  launchctl print "gui/$(id -u)/$LABEL" 2>/dev/null | sed -n '1,40p' || true
  local pid
  pid="$(listener_pid "$PORT")"
  if [[ -z "$pid" ]]; then
    echo "port ${PORT}: not listening"
    return
  fi
  echo
  echo "port ${PORT}:"
  lsof -nP -iTCP:"$PORT" -sTCP:LISTEN || true
  echo
  curl -fsS -m 3 "http://${BIND}:${PORT}/healthz" || true
  echo
  curl -fsS -m 3 "http://${BIND}:${PORT}/api/vision/health" || true
  echo
  curl -fsS -m 3 "http://${BIND}:${PORT}/api/agent/usage" || true
  echo
  echo "vision url: http://${BIND}:${PORT}/vision"
  echo "agent url:  http://${BIND}:${PORT}/agent"
}

logs() {
  tail -n "${N:-120}" -f "$LOG"
}

foreground() {
  local url
  url="$(robot_url)"
  cd "$ROOT"
  exec "$UV_BIN" run python linux_control/vision_service.py \
    --bind "$BIND" \
    --port "$PORT" \
    --robot-url "$url" \
    --vision-camera "$CAMERA" \
    --vision-camera-cycle "$CAMERA_CYCLE" \
    --vision-capture-width "$CAPTURE_WIDTH" \
    --vision-capture-height "$CAPTURE_HEIGHT" \
    --vision-capture-fps "$CAPTURE_FPS" \
    --vision-target-fps "$TARGET_FPS"
}

cmd="${1:-status}"
shift || true
case "$cmd" in
  start) start "$@" ;;
  stop) stop "$@" ;;
  restart) stop "$@" || true; start "$@" ;;
  status) status "$@" ;;
  logs) logs "$@" ;;
  foreground) foreground "$@" ;;
  serve) serve "$@" ;;
  help|-h|--help) usage ;;
  *)
    echo "unknown command: $cmd" >&2
    usage >&2
    exit 2
    ;;
esac
