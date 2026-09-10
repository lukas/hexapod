# Robot Lab v2

One small loop that keeps the robot busy and keeps the bills small:

    health read (≤10 s) → run a protocol → record → plan (≤2 min) → repeat

It replaced the original Robot Lab orchestrator on 2026-09-10. That system
had grown to ~12,000 lines of orchestration plus 17,000 lines of tests, and
each experiment was costing $25–50 and 40+ minutes for about 156 s of
motion, almost all of it pre-run ceremony. The operator's rules, verbatim:
safety checks max 10 seconds, it's a cheap robot, if we see issues we'll stop
it; other checks max 1 minute; planning 2 minutes.

**Do not add pre-run checks, audits, checklists or verification steps here.**
The robot's own in-loop trips (current, temperature, load, tilt, servo loss,
tracking error) are the safety system and they cost nothing. If you believe a
check is needed, it belongs in those trips or it does not belong.

## What runs where

| Piece | Location |
| --- | --- |
| Code | `experiment_lab/hexapod_lab2/` (this package; installed into the lab venv) |
| Data | `~/Library/Application Support/Hexapod Lab/v2/` — `lab2.sqlite3`, `runs/<id>/`, `build/`, `PAUSE` |
| Runner checkout | `…/v2/checkout` — a dedicated clone of `origin/main` with its own `.venv`. Never the operator's working tree. |
| Loop service | LaunchAgent `com.lbiewald.hexapod-lab2`, launcher `…/Hexapod Lab/run-lab2.sh`, log `~/Library/Logs/hexapod-lab2.log` |
| Dashboard | `/v2` on the existing Robot Lab site (`https://robot-lab.cwd1f0-new-cluster.coreweave.app/v2`), same sign-in and tunnel |
| CLI | `~/Library/Application Support/Hexapod Lab/venv/bin/hexapod-lab2` |

The old lab's web service stays up for history. Its job runner
(`com.lbiewald.hexapod-codex-orchestrator`) was booted out so two
controllers never share the servo bus; its plist is still in
`~/Library/LaunchAgents` and would return on reboot.

## The loop

`loop.py` is the whole design; read it top to bottom.

1. `PAUSE` file present → sleep, check again.
2. Stop if: 3 failed runs in a row, robot unreachable twice in a row,
   planner returned nothing twice in a row with an empty queue, or more than
   `$40` spent in 24 h. The reason is written to the events table and shown on
   the dashboard. The service has `KeepAlive=false`: it does not resurrect
   itself. Fix the cause, then `launchctl kickstart`.
3. Start the builder for one `needs_code` plan if none is running.
4. Take the oldest runnable plan. Health read: one `/api/feedback`, hard
   10 s wall, needs 18 live servos, every servo under 60 °C, tilt under 25°.
   Fail → the plan goes back to the queue, nothing is launched.
5. `git pull --ff-only` the runner checkout, then run
   `python -m sysid.run_hw --protocol … --go --capture-vision --capture-frames
   --vision-url … --vision-frame-url … [--force]`, 15 min hard timeout.
6. Copy the runner's dataset into `runs/<id>/`, record exit code and
   `runner_summary.json` verbatim.
7. One planner call (`claude -p --restricted`, structured JSON, `$2` cap,
   2 min wall): writes the "Found" paragraph for that run and queues up to
   three plans, each tagged `existing` (a protocol file on disk) or
   `needs_code` (a build spec).

Planner calls have been costing $0.14–0.20 and taking 1–2 minutes. Builds
have been costing $1–2 and 5–10 minutes.

### Things learned the hard way

- The runner's default frame URL (`<state dir>/frame.jpg`) is not served by
  the pose service on `:8766`; without a fetchable frame no frame ever counts
  as advancing and admission fails before motion. Pass
  `--vision-frame-url http://127.0.0.1:8766/snapshot/1.jpg` (the default here).
- Every trajectory protocol — all the `*_belly_rest_*` and radial-shear
  single-leg replays, not just whole-body stands — trips the runner's
  `--force` gate (`kind: traj` / `rel_traj` segments). The loop passes
  `--force` for those automatically. `HEXAPOD_LAB2_ALLOW_FORCE=0` turns that
  off, at which point almost nothing runs unattended.
- The Keychain item `Hexapod Claude API` reported "Credit balance is too low"
  on 2026-09-10; the `ANTHROPIC_API_KEY` in the operator's login shell works.
  `run-lab2.sh` tries the environment, then the login shell, then Keychain.
- `hexapod-tracker` is a git submodule; a fresh clone needs
  `--recurse-submodules` or `uv sync` fails. `install.sh` handles it.
- A `sqlite3` connection is not shareable across threads. The builder thread
  opens its own `Store`; the web router opens one per request.

## Builder

A `needs_code` plan gets one tool-using Claude run (`--permission-mode
bypassPermissions --add-dir <worktree>`, `$15` cap, 30 min wall) in a
detached worktree of `origin/main`. It is told to reuse an existing protocol
or `sysid/generate_leg_variant.py --leg N`, validate with a dry run (never
`--go`), commit only under `sysid/`, and push to `main`. On success the plan
flips to `existing` and runs on the next iteration. One build at a time; the
robot loop keeps running meanwhile.

## Other robots and hand-run experiments

The database is not only for the loop. An ad-hoc experiment on another robot
is a plan (title, why), a run with a folder of artifacts, and a paragraph.

On the Mac:

    hexapod-lab2 import ~/trials/shuffle-1 --robot hexapod2 \
        --title "Tripod shuffle, carpet" \
        --why "Does the new gait keep the body level?" \
        --found "Level for 40 s, then leg 3 slipped and it tipped left."

From any other device (needs `curl` and the operator bearer token, the
Keychain item `Hexapod Lab API`):

    export HEXAPOD_LAB_TOKEN='…'
    deploy/lab2-send.sh -r hexapod2 -t "title" -w "why" -f "what we found" ~/trials/shuffle-1/

Or the raw API: `POST /v2/api/import` with JSON `{title, why, found, robot,
status}` returns a run id; then `PUT /v2/api/runs/<id>/files/<name>` with the
file as the body, once per file. Uploads stream to disk. Files are served at
`/v2/runs/<id>/<name>` and linked from the dashboard, which has a robot
switcher (`/v2/?robot=hexapod2`). Nothing is parsed. The `found` paragraph is
filed as a learning tagged `[robot]`, so hexapod 1's planner reads it.
Imported plans never enter the hexapod 1 queue.

## Operating it

    hexapod-lab2 status                       # queue, recent runs, spend, last stop
    hexapod-lab2 run <protocol> [--why …]     # one run now, no planner
    hexapod-lab2 add <protocol> "title" "why" # queue an existing protocol
    hexapod-lab2 plan                         # one planner call
    hexapod-lab2 pause | resume               # PAUSE file
    launchctl kickstart -k gui/$(id -u)/com.lbiewald.hexapod-lab2   # (re)start the loop
    launchctl bootout gui/$(id -u)/com.lbiewald.hexapod-lab2        # stop it

Dashboard times are the operator's local clock. Stored times are UTC.

## Deploying a change

    uv pip install --python "$HOME/Library/Application Support/Hexapod Lab/venv/bin/python" --no-deps ~/hexapod/experiment_lab
    launchctl kickstart -k gui/$(id -u)/com.lbiewald.hexapod-lab    # dashboard picks it up
    launchctl kickstart -k gui/$(id -u)/com.lbiewald.hexapod-lab2   # loop picks it up (between runs)

First-time setup is `deploy/install.sh` (clone, submodules, `uv sync`,
launcher, plist). Tests: `.venv/bin/python -m pytest tests_lab2` — 18 tests,
a fraction of a second, decision logic only.

## Settings

Every knob is an environment variable read once in `config.py`
(`HEXAPOD_LAB2_*`): data dir, checkout, robot URL, vision URLs, Claude
binary and models, the budgets (health 10 s, post-run 60 s, planner 120 s,
builder 1800 s, run timeout 900 s), per-call dollar caps, the daily cap, the
stop thresholds, and `ALLOW_FORCE`. Defaults are the operator's rules; change
them in the launcher, not in code.

## Eyes, engineer, and replies (added 2026-09-10 evening)

**Eyes.** The loop records the wide camera (`snapshot/0.jpg`) at 1 Hz for
every run and recovery into `runs/<id>/wide/`, assembles `wide.mp4`, and
sends twelve frames (eight spread, the last four dense) to a vision model
with the protocol and trip line as context. The description is stored as
`seen` in the run summary, shown on the card, and fed to the planner. About
$0.03 per run. The runner's own frame dump is the floor-tag camera and is
kept for tag tracking only.

**Engineer.** The planner may return `kind: needs_fix` when runs fail for a
reason that lives in code. One tool-using Claude gets a worktree, the
diagnosis, the failed run's stills, 30 minutes and $15, and pushes a branch
`lab2/fix-<id>`. The loop merges it only if the diff is confined to
`hexapod_walker/prototype_sts3215/`, avoids `firmware/` and
`experiment_lab/`, and is under 200 changed lines; otherwise the branch is
left for a human and the operator is texted. On merge: the runner checkout
syncs, robot-side changes set `DEPLOY_NEEDED` and are pushed with
`deploy_ssh.sh` between runs (never during one; robot named explicitly),
the engineer's `verify_protocol` is queued, and its `followups` become new
`needs_fix` plans. Fixes run ahead of builds in the single code slot.

Robot access (operator decision 2026-09-10 evening): a `needs_fix` plan
with `needs_robot: true` hands the robot to the engineer exclusively. It
waits for the gap between runs, writes `ROBOT_HELD`, and the loop runs
nothing until the job ends. While holding it the engineer may move the robot
(`--go`, `/api/zero`, `/api/standup`), ssh in, deploy with `deploy_ssh.sh`,
and flash bridge firmware (`firmware/flash_feetech_bridge.sh`). When it
finishes the loop checks the robot is healthy and at rest, runs the recovery
ladder if not, and texts if that fails. Without `needs_robot` the engineer
may not touch the robot at all. The only thing it can never edit is the lab
itself (`experiment_lab/`). Guardrails are money and clock, the branch and
merge gate, and the robot's own in-loop trips; nothing else.

**Replies.** A stop pauses instead of exiting and texts the reason with
`reply: resume | pause | raise cap [dollars] | status`. Reading replies needs
Full Disk Access for the loop's python
(`~/.local/share/uv/python/cpython-3.12.*/bin/python3.12`); without it the
loop logs "text commands unavailable" once and the CLI does the same jobs.
The cap is `CAP_USD` in the data dir, `hexapod-lab2 cap N`.
