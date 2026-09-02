#!/usr/bin/env bash
# Deploy linux_control to the Uno Q over SSH (key auth) — the no-USB
# twin of deploy_adb.sh (same file list; keep the two in sync). Used
# when the board is only reachable over the network.
#
#   ./deploy_ssh.sh              # push + restart web UI
#   ./deploy_ssh.sh --stop       # stop the web server on the board
set -euo pipefail

SRC="$(cd "$(dirname "$0")" && pwd)"
RAW_HOST="${HEXAPOD_SSH:-arduino@hexapod.local}"
REMOTE="/home/arduino/hexapod_sts"
HEXAPOD_MDNS_NAME="${HEXAPOD_MDNS_NAME:-hexapod.local}"
HEXAPOD_CACHE_DIR="${HEXAPOD_CACHE_DIR:-$HOME/.hexapod}"
HEXAPOD_IP_CACHE="${HEXAPOD_IP_CACHE:-$HEXAPOD_CACHE_DIR/last_ip}"
HTTP_URL_RAW="${HEXAPOD_HOST:-http://hexapod.local:8080}"
HTTPS_PORT="${HEXAPOD_HTTPS_PORT:-8443}"
REMOTE_UV="/home/arduino/.local/bin/uv"
HOST="$RAW_HOST"
HTTP_URL="$HTTP_URL_RAW"
SSH=()

cache_ip() {
  local ip="$1"
  [ -n "$ip" ] || return 1
  mkdir -p "$HEXAPOD_CACHE_DIR"
  printf '%s\n' "$ip" > "$HEXAPOD_IP_CACHE"
}

cached_ip() {
  [ -s "$HEXAPOD_IP_CACHE" ] || return 1
  head -n 1 "$HEXAPOD_IP_CACHE"
}

uses_mdns() {
  case "$1" in
    *"$HEXAPOD_MDNS_NAME"*) return 0 ;;
    *) return 1 ;;
  esac
}

with_ip() {
  local value="$1" ip="$2"
  printf '%s\n' "${value//$HEXAPOD_MDNS_NAME/$ip}"
}

resolve_active_ip() {
  local name="${1:-$HEXAPOD_MDNS_NAME}"
  uv run python - "$name" <<'PY'
import re
import socket
import subprocess
import sys
import time

name = sys.argv[1].rstrip(".")

try:
    socket.setdefaulttimeout(1.5)
    print(socket.gethostbyname(name))
    raise SystemExit(0)
except Exception:
    pass

try:
    proc = subprocess.Popen(
        ["dns-sd", "-G", "v4", name],
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        text=True,
    )
except Exception:
    raise SystemExit(1)

ip = None
deadline = time.time() + 3.0
try:
    while time.time() < deadline:
        line = proc.stdout.readline() if proc.stdout else ""
        if not line:
            time.sleep(0.05)
            continue
        match = re.search(r"\b(\d{1,3}(?:\.\d{1,3}){3})\b", line)
        if match and match.group(1) != "0.0.0.0":
            ip = match.group(1)
            break
finally:
    proc.terminate()
    try:
        proc.wait(timeout=0.5)
    except Exception:
        proc.kill()

if not ip:
    raise SystemExit(1)
print(ip)
PY
}

build_ssh() {
  SSH=(ssh -o BatchMode=yes -o ConnectTimeout=10 \
    -o StrictHostKeyChecking=accept-new \
    -o HostKeyAlias="${HEXAPOD_SSH_HOSTKEY_ALIAS:-hexapod.local}" \
    "$HOST")
}

select_robot_address() {
  local ip=""
  if uses_mdns "$RAW_HOST" || uses_mdns "$HTTP_URL_RAW"; then
    if ip="$(cached_ip)"; then
      HOST="$(with_ip "$RAW_HOST" "$ip")"
      HTTP_URL="$(with_ip "$HTTP_URL_RAW" "$ip")"
      echo ">> using cached robot IP $ip ($HEXAPOD_IP_CACHE)"
      build_ssh
      if "${SSH[@]}" true >/dev/null 2>&1; then
        return 0
      fi
      echo ">> cached robot IP did not answer SSH; refreshing mDNS" >&2
    fi
    if ip="$(resolve_active_ip "$HEXAPOD_MDNS_NAME" 2>/dev/null)"; then
      cache_ip "$ip" || true
      HOST="$(with_ip "$RAW_HOST" "$ip")"
      HTTP_URL="$(with_ip "$HTTP_URL_RAW" "$ip")"
      echo ">> using resolved robot IP $ip"
      build_ssh
      return 0
    fi
  fi
  HOST="$RAW_HOST"
  HTTP_URL="$HTTP_URL_RAW"
  build_ssh
}

select_robot_address

wait_http() {
  local body i
  for i in {1..20}; do
    if body="$(curl -fsS -m 1 "$HTTP_URL/api/ping" 2>/dev/null)"; then
      echo "$body"
      return 0
    fi
    sleep 0.25
  done
  curl -s -m 3 "$HTTP_URL/api/ping" || true
}

https_url_for_http() {
  local url="$1" rest host
  rest="${url#http://}"
  rest="${rest#https://}"
  host="${rest%%/*}"
  host="${host%%:*}"
  printf 'https://%s:%s\n' "$host" "$HTTPS_PORT"
}

wait_https() {
  local https_url body i
  https_url="$(https_url_for_http "$HTTP_URL")"
  for i in {1..20}; do
    if body="$(curl -k -fsS -m 1 "$https_url/api/ping" 2>/dev/null)"; then
      echo "$body"
      echo ">> joystick HTTPS: $https_url/rl"
      return 0
    fi
    sleep 0.25
  done
  echo "!! HTTPS joystick URL did not answer: $https_url/rl" >&2
  curl -k -s -m 3 "$https_url/api/ping" || true
  return 1
}

clear_deploy_screen() {
  curl -fsS -m 3 -X POST "$HTTP_URL/api/tft/ready" >/dev/null 2>&1 || true
}

ensure_remote_uv() {
  "${SSH[@]}" "set -e; \
    if [ ! -x '$REMOTE_UV' ]; then \
      curl -LsSf https://astral.sh/uv/install.sh | sh; \
    fi; \
    '$REMOTE_UV' --version"
}

# Serialize deploys across workspaces (lock ~/.hexapod/deploy.lock,
# history ~/.hexapod/deploy.log — see deploy_lock.sh).
source "$SRC/deploy_lock.sh"
deploy_lock_acquire "ssh ${1:-push+restart}"

if [ "${1:-}" = "--stop" ]; then
  "${SSH[@]}" 'pkill -f "[w]eb_drive.py" || true'
  echo ">> stopped"
  exit 0
fi

# Stage the EXACT remote layout locally (shared manifest — same tree as
# deploy_adb.sh), then ship it as ONE tar over one ssh connection (the
# old per-file scp made ~40 round trips and a deploy took ~4 minutes;
# this takes seconds).
echo ">> staging deploy tree (deploy_manifest.sh)"
source "$SRC/deploy_manifest.sh"
STAGE="$(mktemp -d /tmp/hexapod_deploy.XXXXXX)"
trap 'rm -rf "$STAGE"; deploy_lock_release' EXIT
stage_deploy_tree "$STAGE" "$SRC"

echo ">> pushing code + vendored SDK -> $HOST:$REMOTE (single tar|ssh)"
# COPYFILE_DISABLE: keep macOS bsdtar from tucking ._* AppleDouble files
# into the stream (GNU tar on the board would extract them as junk).
# The rm -rf clears the retired urt2_setup bundles (tar extracts over an
# existing tree without deleting stale files).
COPYFILE_DISABLE=1 tar --no-xattrs -C "$STAGE" -czf - . \
  | "${SSH[@]}" "mkdir -p '$REMOTE' && \
      rm -rf '$REMOTE/urt2_setup' '$REMOTE/linux_control/urt2_setup' && \
      tar -xzf - -C '$REMOTE'"

echo ">> ensuring uv on Uno Q"
ensure_remote_uv

paint_deploy_screen() {
  "${SSH[@]}" "cd '$REMOTE/linux_control' && \
    PYTHONPATH='$REMOTE/linux_control/vendor:$REMOTE/motor_setup:$REMOTE/linux_control:$REMOTE' \
    '$REMOTE_UV' run python deploy_status_display.py \
      --title DEPLOYING \
      --line 'code updated' \
      --line 'web restarting' \
      --line 'please wait' \
      --footer 'screen will resume'" >/dev/null 2>&1 || true
}

echo ">> restarting web_drive.py"
if "${SSH[@]}" 'systemctl is-enabled hexapod-web.service >/dev/null 2>&1'; then
  "${SSH[@]}" 'echo arduino | sudo -S systemctl stop hexapod-web.service' \
    >/dev/null || true
  "${SSH[@]}" "echo arduino | sudo -S cp '$REMOTE/linux_control/systemd/hexapod-web.service' /etc/systemd/system/hexapod-web.service && \
    echo arduino | sudo -S systemctl daemon-reload" >/dev/null
  paint_deploy_screen
  "${SSH[@]}" 'echo arduino | sudo -S systemctl start hexapod-web.service' \
    >/dev/null
  "${SSH[@]}" 'systemctl --no-pager -l status hexapod-web.service \
    | head -5 || true'
else
  "${SSH[@]}" "pkill -f '[w]eb_drive.py' || true" || true
  paint_deploy_screen
  "${SSH[@]}" "sh -c 'cd \"$REMOTE/linux_control\" && \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=\"$REMOTE/linux_control/vendor:$REMOTE/motor_setup:$REMOTE/linux_control:$REMOTE\" \
    nohup \"$REMOTE_UV\" run python web_drive.py --port mcu --http-port 8080 \
    --https-port 8443 > \"$REMOTE/web_drive.log\" 2>&1 < /dev/null &'"
fi

echo ">> verify over HTTP ($HTTP_URL)"
wait_http
echo ">> verify over HTTPS ($(https_url_for_http "$HTTP_URL"))"
wait_https
clear_deploy_screen
echo
echo ">> done"
