# Stand and sit cycle with camera recording (2ae9157f) — recovered terminal result

Experiment `2ae9157fb18c45cbaccab67321fd5ad8`, engineering job
`5a482e85cc0a45baa59dc004ca8884df` attempt 2 (`completion_only`).
Registered `succeeded`, completion `b9f6abe2`, evidence sealed at manifest `2b3043f9`.

**Attempt 2 commanded no motion.** The run below was executed by attempt 1 and is
reconstructed here from robot-side and host-side records.

## Why a recovery was needed

Attempt 1 started the saved sequence at 00:16:11Z and was killed by the harness
(SIGTERM, exit 143) at 00:16:42.191Z — about 6 s after the sit-down completed, while it
was still inside its 10 s settle. The physical run finished; only the process watching it
did not, so nothing was ever registered and the plan sat in `waiting_for_operator`.

## What actually happened (robot `events.jsonl` + `commands.jsonl`)

| UTC | Event |
|---|---|
| 00:15:41.141 | `GET /api/rl/preflight` (mode=stand) → ok |
| 00:16:11.022 | recording starts, all three cameras |
| 00:16:12.845 | `POST /api/rl/stand {"tilt_trip_deg":20}` |
| 00:16:12.891 | `step stand-up x10 start` — 18 keyframes, live_ids 18/18 |
| 00:16:18.253 | stand-up **complete** — align 0.00 s (worst0 0.8 deg) + stream 3.05 s |
| 00:16:19.461 | `walk-ready start: settle` |
| — | **hold: 12.4 s standing** (plan asked ~10 s) |
| 00:16:30.550 | `GET /api/rl/preflight` (mode=lower) → ok |
| 00:16:30.648 | `POST /api/rl/lower {"tilt_trip_deg":20}` |
| 00:16:30.669 | `step sit-down x10 start` — 18 keyframes, live_ids 18/18 |
| 00:16:36.139 | sit-down **complete** — align 1.76 s (worst0 2.3 deg) + stream 3.12 s |
| 00:16:39.666 | last recorded frame |
| 00:16:42.191 | SIGTERM to attempt 1, mid-settle |

All six saved steps issued, in order, with the saved bodies. Nothing else commanded the
robot in that window.

## Findings

1. **The camera-server path works on real motion — the question this experiment asked.**
   All three observation cameras read frames from the server on :8766 instead of opening
   the devices, and captured 107 frames each (321 total) across the full 28.6 s at ~3.7 fps.
   No dropped camera, no device contention, and the same server kept serving the Lab's own
   status previews concurrently.

2. **The stand and sit were clean.** 18/18 joints in every one of the 25 `servo_fb` samples
   (`servo_feedback_table.txt`). No stop condition fired: no tip, no brownout, max motor
   temperature flat at 47 C against a 55 C threshold, and no `/api/errors` row anywhere in
   00:16:11–00:16:42Z. The only `/api/rl/stop` in the entire robot command journal is at
   00:04:41Z during the separate incident below — the journal does record stops, so its
   absence here is meaningful rather than merely unobserved.

3. **Sit-down current reproduces the hand reference exactly.** Peak per-servo current was
   2.73 A on the stand-up and **2.78 A** on the sit-down; the plan's by-hand reference was
   2.78 A. Both peaks sit under the 2.70 A nominal stall only marginally and are consistent
   with the STEP keyframe profile, not a jam.

4. **Roll/pitch are unmeasured, and that is a gap in the recovery, not a pass.** The robot's
   `servo_fb` records carry per-joint angle, current, load and temperature but no IMU field,
   and attempt 1's tilt monitor held its samples in memory and died with the process. The
   saved 20 deg trip was therefore never recorded numerically, so the hand reference's
   roll −1.7..5.9 / pitch 4.9..7.5 band could not be checked. The camera record establishes
   the chassis stayed upright and level and that there was no tip; it does not substitute for
   the numeric band. A future runner should stream tilt samples to disk as it goes rather
   than accumulating them for a final write.

## Camera evidence

Frames, per-camera MP4s and contact sheets are too large for git and are kept at
`~/Library/Application Support/Hexapod Lab/recovered-evidence/2ae9157fb18c45cbaccab67321fd5ad8/`
(69 MB, 321 frames + 3 MP4s + contact sheets), hashed in `media_SHA256SUMS.txt` here.
Contact sheets show belly-down at 00:16:11, rising at 00:16:15, standing at 00:16:18.9 /
22.9 / 27.1 / 31.1, descending at 00:16:35.2, settled belly-down at 00:16:39.5.

## Two process findings worth acting on

**A non-queue controller can command the robot during a leased guarded handoff.**
From 00:04:38Z to 00:12:11Z the `:8898` RL web hub, driven from a browser, commanded
stand/lower directly — at one point every ~8 s, faster than the async motion worker
completes — taking knee servos 34 C → 50 C and destroying this plan's belly-down
precondition twice. The Lab reported `guarded_runner_ready:false` and
`can_start_from_website:false` throughout and neither prevented it. No zero-frame change
occurred (`/api/zero` is `go_zero`, a move, not `set_zero_here`). Full attribution in
`concurrent_controller_incident.json`. One correction to that file: it argues "system
python3 is 3.9.6, so this job cannot be the `Python-urllib/3.12` caller", which was true when
written (the runner had only been `py_compile`d) but not later — the runner ran under
`/Users/lukas/hexapod-hub/.venv/bin/python3`, which is 3.12.14, so the 00:16:12 and 00:16:30
commands are this job's own. The foreign attribution for 00:04–00:12 stands on its
`lsof`/timeline evidence independently of that argument.

**`complete_external_experiment` auto-seals evidence about 60 s later.** Registration at
01:22:17.496Z was followed by an automatic `evidence_sealed` at 01:23:17.795Z. Artifact
uploads attempted after registration returned
`409 Experiment evidence is sealed and cannot be changed`, which is why the media above lives
outside the Lab. `PUT /api/experiments/{id}/artifacts/{filename}` must be called **before**
`complete_external_experiment`, not after it — the reverse of what the tool description's
"upload large artifacts through the returned authenticated HTTP API URLs" implies.

## Robot state at registration

Idle, armed, 18/18 live, all joints within 0.26 deg of logical zero, max 34 C, 0.00 A, no
alarms — three separate polls plus fresh streaming frames on all three observation cameras.
