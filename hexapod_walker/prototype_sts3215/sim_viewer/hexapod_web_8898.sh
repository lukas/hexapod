#!/usr/bin/env bash
# Canonical local Mac launcher for the hexapod web hub on HTTP :8898 and
# gamepad-ready HTTPS :8443.
#
# This runs on Lukas's Mac, not on the Uno Q. It serves the shared web UI
# locally and proxies the robot target to the board's :8080 web service.
set -euo pipefail

SELF="$(cd "$(dirname "$0")" && pwd)/$(basename "$0")"
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
LABEL="${HEXAPOD_WEB8898_LABEL:-com.lukas.hexapod-web-8898}"
LEGACY_LABEL="${HEXAPOD_WEB8898_LEGACY_LABEL:-com.lukas.hexapod-sim-web-8898}"
PORT="${SIM_WEB_PORT:-8898}"
HTTPS_PORT="${SIM_WEB_HTTPS_PORT:-8443}"
BIND="${SIM_WEB_BIND:-127.0.0.1}"
TARGET="${SIM_WEB_TARGET:-robot}"
PHASE="${SIM_WEB_PHASE:-1}"
LOG="${HEXAPOD_WEB8898_LOG:-/tmp/hexapod_web_8898.log}"
POLICY_DIR="${POLICY_DIR:-$ROOT/rl_move/sim/policies}"
TLS_CERT="${SIM_WEB_TLS_CERT_FILE:-}"
TLS_KEY="${SIM_WEB_TLS_KEY_FILE:-}"
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
Usage: sim_viewer/hexapod_web_8898.sh <command>

Commands:
  start       Start the local hub on HTTPS :${HTTPS_PORT} + HTTP :${PORT}
  stop        Stop the launchctl job and any stale hub on those ports
  restart     Stop, then start
  status      Show launchctl, ports, and HTTP/HTTPS health
  logs        Tail ${LOG}
  foreground  Run in the foreground with uv run

Environment:
  HEXAPOD_HOST=http://<robot-ip-or-name>:8080   robot target (default: resolve hexapod.local)
  SIM_WEB_BIND=${BIND}                          bind address
  SIM_WEB_PORT=${PORT}                          local port
  SIM_WEB_HTTPS_PORT=${HTTPS_PORT}              secure gamepad port
  SIM_WEB_TARGET=${TARGET}                      sim, robot, or both
  POLICY_DIR=${POLICY_DIR}                      policy cache
  SIM_WEB_TLS_CERT_FILE=/path/to/cert.pem       optional trusted cert
  SIM_WEB_TLS_KEY_FILE=/path/to/key.pem         optional trusted key

The same process serves https://localhost:${HTTPS_PORT}/vision. Camera
capture is off until Start camera is pressed on that page.
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
  local port="${1:-$PORT}"
  lsof -tiTCP:"$port" -sTCP:LISTEN 2>/dev/null | head -n 1 || true
}

listener_command() {
  local pid="$1"
  [[ -n "$pid" ]] || return 0
  ps -p "$pid" -o command= 2>/dev/null || true
}

wait_ready() {
  local url="http://${BIND}:${PORT}/api/sim/state"
  local ping="http://${BIND}:${PORT}/api/ping"
  # /api/ping follows the selected target and may wait on an offline robot;
  # /api/sim/state is local and proves this process is ready on each socket.
  local secure="https://${BIND}:${HTTPS_PORT}/api/sim/state"
  local i
  for i in {1..80}; do
    if curl -fsS -m 2 "$url" >/dev/null 2>&1 \
        && curl -kfsS -m 2 "$secure" >/dev/null 2>&1; then
      echo "ready: https://localhost:${HTTPS_PORT}/rl (gamepad)"
      echo "also:  http://localhost:${PORT}/rl"
      curl -fsS -m 3 "$ping" || true
      echo
      return 0
    fi
    sleep 0.25
  done
  echo "local web hub did not become ready. Recent log:" >&2
  tail -80 "$LOG" >&2 2>/dev/null || true
  return 1
}

stop_port_if_ours() {
  local port="${1:-$PORT}" pid cmd
  pid="$(listener_pid "$port")"
  [[ -n "$pid" ]] || return 0
  cmd="$(listener_command "$pid")"
  if [[ "$cmd" == *"rl_move.sim.web_server"* ]]; then
    /bin/kill "$pid" 2>/dev/null || true
  else
    echo "port ${port} is in use by another process:" >&2
    echo "  $cmd" >&2
    return 1
  fi
}

serve() {
  local bind="$1" port="$2" https_port="$3" policy_dir="$4" url="$5"
  local target="$6" phase="$7" log="$8" tls_cert="$9" tls_key="${10}"
  cd "$ROOT"
  exec >>"$log" 2>&1
  echo "[$(date -u '+%Y-%m-%dT%H:%M:%SZ')] starting hexapod web hub on HTTP ${bind}:${port}, HTTPS ${bind}:${https_port}"
  echo "robot target: ${url}"
  local args=(
    run python -m rl_move.sim.web_server
    --bind "$bind"
    --http-port "$port"
    --https-port "$https_port"
    --policy-dir "$policy_dir"
    --robot-url "$url"
    --target "$target"
  )
  if [[ -n "$tls_cert" || -n "$tls_key" ]]; then
    if [[ -z "$tls_cert" || -z "$tls_key" ]]; then
      echo "SIM_WEB_TLS_CERT_FILE and SIM_WEB_TLS_KEY_FILE must be set together" >&2
      return 2
    fi
    args+=(--tls-cert "$tls_cert" --tls-key "$tls_key")
  fi
  if [[ "$phase" != "0" ]]; then
    args+=(--phase-obs)
  else
    args+=(--no-phase-obs)
  fi
  exec "$UV_BIN" "${args[@]}"
}

start() {
  local url pid https_pid cmd
  url="$(robot_url)"
  pid="$(listener_pid "$PORT")"
  https_pid="$(listener_pid "$HTTPS_PORT")"
  if [[ -n "$https_pid" && "$https_pid" != "$pid" ]]; then
    cmd="$(listener_command "$https_pid")"
    echo "HTTPS port ${HTTPS_PORT} is already in use:" >&2
    echo "  $cmd" >&2
    return 1
  fi
  if [[ -n "$pid" ]]; then
    cmd="$(listener_command "$pid")"
    if [[ "$cmd" != *"rl_move.sim.web_server"* ]]; then
      echo "port ${PORT} is in use by another process:" >&2
      echo "  $cmd" >&2
      return 1
    fi
    if [[ "$https_pid" == "$pid" ]] \
        && curl -kfsS -m 2 "https://${BIND}:${HTTPS_PORT}/api/sim/state" >/dev/null 2>&1; then
      echo "already listening on HTTP :${PORT} and HTTPS :${HTTPS_PORT}:"
      echo "$cmd"
      wait_ready
      return
    fi
    echo "existing hub has no healthy HTTPS listener; restarting it"
    launchctl remove "$LABEL" >/dev/null 2>&1 || true
    stop_port_if_ours "$PORT"
  fi

  launchctl remove "$LEGACY_LABEL" >/dev/null 2>&1 || true
  launchctl remove "$LABEL" >/dev/null 2>&1 || true
  echo "starting $LABEL with uv run..."
  launchctl submit -l "$LABEL" -- /bin/bash "$SELF" serve \
    "$BIND" "$PORT" "$HTTPS_PORT" "$POLICY_DIR" "$url" "$TARGET" "$PHASE" "$LOG" \
    "$TLS_CERT" "$TLS_KEY"
  wait_ready
}

stop() {
  launchctl remove "$LEGACY_LABEL" >/dev/null 2>&1 || true
  launchctl remove "$LABEL" >/dev/null 2>&1 || true
  stop_port_if_ours "$PORT" || return
  stop_port_if_ours "$HTTPS_PORT" || return
  echo "stopped $LABEL"
}

status() {
  echo "label: $LABEL"
  launchctl print "gui/$(id -u)/$LABEL" 2>/dev/null | sed -n '1,70p' || true
  local pid
  pid="$(listener_pid "$PORT")"
  if [[ -n "$pid" ]]; then
    echo
    echo "port ${PORT}:"
    lsof -nP -iTCP:"$PORT" -sTCP:LISTEN || true
    echo
    curl -fsS -m 2 "http://localhost:${PORT}/api/sim/state" >/dev/null \
      && echo "sim: ready" || true
    curl -fsS -m 3 "http://localhost:${PORT}/api/ping" || true
    echo
    echo "url: http://localhost:${PORT}/rl"
    curl -fsS -m 2 "http://localhost:${PORT}/api/vision/health" >/dev/null \
      && echo "vision: ready (camera off until requested)" || true
    echo "vision url: http://localhost:${PORT}/vision"
  else
    echo "port ${PORT}: not listening"
  fi
  echo
  pid="$(listener_pid "$HTTPS_PORT")"
  if [[ -n "$pid" ]]; then
    echo "HTTPS port ${HTTPS_PORT}:"
    lsof -nP -iTCP:"$HTTPS_PORT" -sTCP:LISTEN || true
    curl -kfsS -m 3 "https://localhost:${HTTPS_PORT}/api/sim/state" \
      >/dev/null && echo "secure sim: ready" || true
    echo
    echo "gamepad url: https://localhost:${HTTPS_PORT}/rl"
    echo "secure vision url: https://localhost:${HTTPS_PORT}/vision"
  else
    echo "HTTPS port ${HTTPS_PORT}: not listening"
  fi
}

logs() {
  tail -n "${N:-120}" -f "$LOG"
}

foreground() {
  local url
  url="$(robot_url)"
  cd "$ROOT"
  local args=(
    run python -m rl_move.sim.web_server
    --bind "$BIND"
    --http-port "$PORT"
    --https-port "$HTTPS_PORT"
    --policy-dir "$POLICY_DIR"
    --robot-url "$url"
    --target "$TARGET"
  )
  if [[ -n "$TLS_CERT" || -n "$TLS_KEY" ]]; then
    if [[ -z "$TLS_CERT" || -z "$TLS_KEY" ]]; then
      echo "SIM_WEB_TLS_CERT_FILE and SIM_WEB_TLS_KEY_FILE must be set together" >&2
      return 2
    fi
    args+=(--tls-cert "$TLS_CERT" --tls-key "$TLS_KEY")
  fi
  if [[ "$PHASE" != "0" ]]; then
    args+=(--phase-obs)
  else
    args+=(--no-phase-obs)
  fi
  exec "$UV_BIN" "${args[@]}"
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
