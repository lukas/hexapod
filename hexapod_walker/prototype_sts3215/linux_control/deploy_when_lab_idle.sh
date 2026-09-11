#!/bin/bash
# Deploy to the robot only while Robot Lab v2 has no run in flight.
#
# `robot-deploy` restarts hexapod-web.service. Doing that under a running
# experiment kills it mid-motion: on 2026-09-10 a deploy at 00:37:47Z cut
# experiment 51f54beb's cycle 2 POST with connection refused, and the same
# deploy silently reverted the guard fix the lab had just shipped from its
# own branch. Wait for the lab to go quiet instead. (Robot Lab v2 deploys
# its own robot-side changes between runs; this is for hand deploys.)
set -u
V2="/Users/lukas/Library/Application Support/Hexapod Lab/v2"
DB="$V2/lab2.sqlite3"
PROTO="$(cd "$(dirname "$0")/.." && pwd)"
LOG="${DEPLOY_WHEN_IDLE_LOG:-/tmp/deploy_when_lab_idle.log}"
DEADLINE=$(( $(date +%s) + ${DEPLOY_WHEN_IDLE_TIMEOUT:-10800} ))

# Operator-facing log: use the operator's clock, not UTC.
say() { printf '%s %s\n' "$(date '+%F %-I:%M:%S %p %Z')" "$*" | tee -a "$LOG"; }

say "waiting for Robot Lab v2 to go idle"
while :; do
  busy=$(sqlite3 "file:$DB?immutable=1" \
    "select count(*) from runs where status='running';" 2>/dev/null)
  [ -z "$busy" ] && busy=1                 # unreadable == assume busy
  [ -e "$V2/ROBOT_HELD" ] && busy=1        # the lab's engineer owns the robot
  moving=$(curl -sk --max-time 8 https://192.168.4.39:8443/api/rl/state 2>/dev/null \
    | python3 -c 'import json,sys
try: d=json.load(sys.stdin)
except Exception: print(1); raise SystemExit
p=d.get("pose") or {}
print(1 if ((p.get("demo") or {}).get("running") or p.get("mode") not in (None,"idle")) else 0)' 2>/dev/null)
  [ -z "$moving" ] && moving=1
  if [ "$busy" = "0" ] && [ "$moving" = "0" ]; then
    say "lab idle and robot not moving; deploying"
    break
  fi
  if [ "$(date +%s)" -ge "$DEADLINE" ]; then
    say "timeout reached (busy=$busy moving=$moving); NOT deploying"
    exit 1
  fi
  sleep 30
done

if make -C "$PROTO" robot-deploy >>"$LOG" 2>&1; then
  say "deploy ok"
else
  say "DEPLOY FAILED — see $LOG"
  exit 1
fi

say "verifying both guards on the robot"
ssh -o ConnectTimeout=8 arduino@192.168.4.39 \
  "printf 'safe_zero GUARD_CONFIRM_READS=%s standup IMPLAUSIBLE_FAULT_READS=%s\n' \
     \"\$(grep -c GUARD_CONFIRM_READS /home/arduino/hexapod_sts/linux_control/safe_zero.py)\" \
     \"\$(grep -c IMPLAUSIBLE_FAULT_READS /home/arduino/hexapod_sts/linux_control/api/standup.py)\"" \
  >>"$LOG" 2>&1
tail -1 "$LOG"
say "done"
