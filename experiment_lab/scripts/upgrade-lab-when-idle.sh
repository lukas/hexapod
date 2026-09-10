#!/bin/bash
# Wait for the live Claude engineering job to finish, then install the new
# lab code and restart both services. Restarting the orchestrator now would
# SIGTERM a 40-minute-old subagent working the hip-yield problem.
set -u
DB="/Users/lukas/Library/Application Support/Hexapod Lab/data/lab.sqlite3"
VENV="/Users/lukas/Library/Application Support/Hexapod Lab/venv"
LOG=/tmp/lab_upgrade_watch.log
# A single experiment can hold the lane for over an hour, and waiting is
# always safer than cutting one: a restart at 00:37 tonight killed a run
# mid-stand-up. Default generously and let the caller override.
DEADLINE=$(( $(date +%s) + ${UPGRADE_WHEN_IDLE_TIMEOUT:-21600} ))

say() { printf '%s %s\n' "$(date -u +%FT%TZ)" "$*" | tee -a "$LOG"; }

say "watching for the running engineering job to finish"
while :; do
  running=$(sqlite3 "file:$DB?immutable=1" \
    "select count(*) from codex_engineering_jobs where status='running';" 2>/dev/null)
  [ -z "$running" ] && running=1          # unreadable == assume busy
  if [ "$running" = "0" ]; then
    say "no engineering job running; upgrading"
    break
  fi
  if [ "$(date +%s)" -ge "$DEADLINE" ]; then
    say "deadline reached with a job still running; NOT upgrading"
    exit 1
  fi
  sleep 30
done

say "installing hexapod_lab from the repo"
if /opt/homebrew/bin/uv pip install --python "$VENV/bin/python" --no-deps \
     /Users/lukas/hexapod/experiment_lab >>"$LOG" 2>&1; then
  say "install ok"
else
  say "INSTALL FAILED — services left on the old code"
  exit 1
fi

grep -c QUEUE_STOP_ASSESS_SECONDS \
  "$VENV/lib/python3.12/site-packages/hexapod_lab/db.py" >>"$LOG" 2>&1

for svc in com.lbiewald.hexapod-lab com.lbiewald.hexapod-codex-orchestrator; do
  say "restarting $svc"
  launchctl kickstart -k "gui/$(id -u)/$svc" >>"$LOG" 2>&1 \
    && say "  ok" || say "  FAILED"
done

sleep 10
say "lab health: $(curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:8767/healthz)"
say "done"
