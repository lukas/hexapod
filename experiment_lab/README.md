# Hexapod Lab

Hexapod Lab is a local, authenticated experiment queue for a robot. It accepts bounded experiment specifications through REST or MCP, executes one at a time, records telemetry and video, and publishes a durable result page with downloadable evidence.

It defaults to a simulated robot so the complete workflow can be tested without moving hardware. Connecting real hardware is an explicit configuration step.

## What it provides

- FIFO queue with `queued`, `running`, `succeeded`, `failed`, and `cancelled` states
- Bearer-token API/MCP authentication and role-based `viewer`, `operator`, and `admin` access
- Browser results UI with a sign-in form and short-lived sessions using the same named tokens; HTTP Basic remains supported
- One evidence directory per experiment containing the submitted spec, JSONL telemetry, logs, MP4 video when configured, and a Markdown summary
- A prominent **What we learned** section with plain-language findings, followed by the detailed report and evidence
- A live **Robot right now** panel with motor health, camera view, and checks needed before another physical test
- REST artifact streaming and MCP artifact discovery/reading
- Registration of externally completed guarded runs plus streamed artifact upload
- Immutable calibration-report archive with optional exact pose-config snapshots
- A phone-first AprilTag walk-around that saves raw/annotated views and an advisory orientation proposal
- Immutable, effective-dated AprilTag history with exact replay snapshots for every recording
- A single-consumer worker so two experiments never command the robot concurrently
- A durable Codex completion outbox: every sealed result gets one evidence-analysis job and one independently leased queue-advance job
- Bounded adaptive follow-ups, with exact-spec deduplication and lineage/depth caps; physical proposals use the serialized guarded runner
- Duration limits, cancellation, an append-only event trail, and no shell interpolation of configured commands

## Quick start

Python 3.9+ and `uv` are supported. Install `ffmpeg` on the service `PATH`
before enabling camera capture; command mode refuses to run without a fresh
camera frame, and video-aware analysis uses `ffmpeg` to build contact sheets.

```sh
cp .env.example .env
# Replace every example credential in .env first.
uv sync --extra dev
set -a; source .env; set +a
uv run hexapod-lab
```

Open `http://127.0.0.1:8767/` and sign in with the `name` and `token` from a configured `role:name:token` entry. For example, `operator:robot-operator:a-long-random-secret` becomes username `robot-operator` and password `a-long-random-secret`.

The browser redirects to `/login` instead of opening a repeating HTTP Basic
popup. Invalid credentials display an inline error. Sessions use opaque,
HttpOnly, SameSite cookies (Secure on HTTPS), expire after eight hours, and are
cleared when the service restarts. The dashboard's **Sign out** button revokes
the session. Cookie-authenticated writes require a matching Origin; API/MCP
clients can continue using their existing Authorization headers.

Queue a simulated experiment:

```sh
curl -H 'Authorization: Bearer a-long-random-secret' \
  -H 'Content-Type: application/json' \
  -d '{"name":"Tripod gait baseline","description":"Straight, level floor","duration_seconds":5,"parameters":{"speed_mps":0.1}}' \
  http://127.0.0.1:8767/api/experiments
```

## Robot status and waiting plans

The top of **Robot right now** explains what control work is happening, or
**Why the robot is idle**, with a concrete reason and next step. Live controller
activity takes precedence over a progress report. Normal motor readings alone
do not mean that an experiment runner has started.

An operator or guarded agent runner reports work through
`POST /api/execution-progress`:

```json
{
  "state": "blocked",
  "summary": "Integrating the controller fixes",
  "detail": "The guarded runner is applying and testing the reviewed control changes before the bounded test.",
  "next_action": "Verify the installed controller, then inspect the live camera and telemetry.",
  "task_name": "Walking controller verification",
  "ttl_seconds": 900
}
```

States are `preparing`, `blocked`, `running`, and `idle`; an optional
`experiment_id` links the work to an existing plan. Reports are append-only,
attributed to the authenticated publisher, and expire after at most one hour.
Publish on each stage change and renew before expiry while work continues.
Expired reports are explicitly marked stale. Report an actual observed blocker,
who is working on it, and the next action; do not substitute a generic permission
request. `GET /api/execution-progress` is available to viewers.
Reporting progress does not start motors, grant approval, or change an
experiment's recorded execution state.

The dashboard refreshes robot observations every five seconds through the
viewer-authenticated `GET /api/robot-status` endpoint. It reads the controller's
passive `/api/robot` snapshot and the Mac hub's cached `/api/vision/state`.
`GET /api/robot-status/frame` serves the existing camera image. These reads do
not scan motors, start a camera, arm the robot, or launch experiments.

The sources default to `http://hexapod.local:8080/api/robot` and
`http://127.0.0.1:8898/api/vision/state`; override them with
`HEXAPOD_ROBOT_STATUS_URL` and `HEXAPOD_ROBOT_VISION_URL`. URLs must retain
these exact passive paths without query parameters. With the default robot
hostname, the service first asks the Mac hub's `/api/hub` metadata for the
physical robot's current local address. It reads that target directly regardless
of which simulator or robot view is selected in the hub. No robot IP is
hard-coded, and an unavailable or invalid discovery response falls back to the
configured hostname. Local status requests bypass HTTP proxies.
If direct access fails, the service can use the hub's existing passive
`/api/robot` proxy after confirming that its selected target is the physical
robot. It never changes the hub target. Simulator responses are rejected even
if the target changes during a request.

Normal motor health requires three distinct, recent physical-robot samples.
Missing, simulated, stale, or unreachable readings never count as healthy.
The tilt/IMU signal is reported separately and is required only for motions
whose controller actually consumes it. The panel separately reports previous
controller stops and camera position checks. A fresh safe camera view plus three
healthy motor samples is sufficient live supervision for routine guarded work.

`waiting_for_operator` is the persisted compatibility name for an
`external_guarded` saved plan; the UI displays **waiting for guarded runner**.
The built-in simulation worker does not execute it, and the website itself has
no launch button. The serialized engineering Codex runner or a human operator
may prepare, execute, and close it after the applicable live checks pass.
An external run can still appear waiting until its runner posts the result, so
the experiment status alone does not describe current robot activity.

## Plain-language findings

Every experiment page begins with **What we learned**. Completed-result
publishers should include `what_we_learned` in their REST or MCP result payload:
two to four short sentences stating what the evidence shows, why it matters,
and any important limitation. Explain specialist terms, distinguish physical
tests from simulation, and do not treat a successful runner exit as proof that
the robot achieved the experiment's aim.

For an existing completed experiment, an operator can post
`{"text":"The finding in simple language.","sources":["summary.md"]}` to
`/api/experiments/{id}/learnings`. Sources must name existing evidence files.
Updates append an attributed revision and event in the database; original run
artifacts and their manifest remain unchanged. The latest revision is returned
as `what_we_learned` in experiment responses. Exact repeats are idempotent.

Queued, running, and guarded-runner experiments explicitly say that findings
are not available yet. Built-in runs get a conservative workflow summary;
imported results without authored findings clearly say the write-up is missing.

The OpenAPI explorer is at `/docs`. Data is stored under `lab-data/experiments/<experiment-id>/` and queue metadata is in `lab-data/lab.sqlite3`.

Guarded runners that already own robot-specific safety can register a completed
result with `POST /api/results`, then stream each flat-named evidence file with
`PUT /api/experiments/<id>/artifacts/<filename>`. Existing artifacts are never
overwritten. The equivalent MCP metadata tool is `register_result`; large files
use the authenticated HTTP upload path and are subsequently discoverable from
both MCP and the website.

## MCP connection

The Streamable HTTP JSON-RPC endpoint is `http://127.0.0.1:8767/mcp` with an `Authorization: Bearer <token>` header. It exposes `list_experiments`, `get_experiment`, `queue_experiment`, `cancel_experiment`, `register_result`, `complete_external_experiment`, `seal_experiment_evidence`, `read_artifact`, `list_tag_layout_revisions`, `get_tag_layout`, `list_calibrations`, and `get_calibration`.

Text and small binary artifacts can be returned directly; artifacts larger than 1 MiB are discovered through MCP and streamed through their authenticated REST URL. Video stays out of model context and is watched on the result page or streamed from the API.

```json
{
  "url": "http://127.0.0.1:8767/mcp",
  "headers": {"Authorization": "Bearer a-long-random-secret"}
}
```

## Connecting the real robot

```dotenv
HEXAPOD_DRIVER=command
HEXAPOD_ROBOT_COMMAND=/absolute/path/to/robot-runner --mode experiment
HEXAPOD_CAMERA_INPUT=/dev/video0
```

The robot command is parsed as an argument vector and run without a shell. It receives the experiment JSON on stdin plus `HEXAPOD_EXPERIMENT_ID` and `HEXAPOD_RUN_DIR` in its environment. It must return nonzero on unsafe or failed execution and should write one JSON telemetry object per stdout line. Stderr becomes `robot.stderr.log`. Camera capture uses `ffmpeg` and writes `video.mp4` plus `camera.log`.

Command mode cannot start until `ffmpeg` reports a fresh encoded camera frame;
camera exit or stale encoder progress terminates the robot command. Robot and
camera processes each run under an independent deadline wrapper. The runner
also holds a process-wide lock so a second Lab instance cannot claim work at the
same time. An interrupted service or unreconciled process group sets a durable
inspection latch across restarts. After live camera/telemetry inspection—or
hands-on correction when required—the guarded runner or an operator uses
**Resume experiment runner** or `POST /api/runner-safety/resume` with
`X-Hexapod-Lab: 1`, a nonblank reason, and `robot_inspected: true`.

The adapter must enforce robot-specific constraints: allowed gaits, workspace boundaries, maximum joint speed/torque, battery thresholds, hardware e-stop status, and a safe neutral pose. Do not enable `command` until those checks are tested locally. Software cancellation is not an emergency stop.

## Configuration

| Variable | Default | Meaning |
|---|---:|---|
| `HEXAPOD_API_KEYS` | none (startup fails) | Comma-separated `role:name:token` records |
| `HEXAPOD_DATA_DIR` | `./lab-data` | SQLite database and evidence root |
| `HEXAPOD_DRIVER` | `simulated` | `simulated` or `command` |
| `HEXAPOD_ROBOT_COMMAND` | empty | Real adapter argv |
| `HEXAPOD_CAMERA_INPUT` | empty | ffmpeg-compatible input |
| `HEXAPOD_CAMERA_READY_TIMEOUT_SECONDS` | `10` | Maximum wait for the first encoded frame |
| `HEXAPOD_CAMERA_STALE_SECONDS` | `5` | Maximum encoder-progress age during a physical run |
| `HEXAPOD_MAX_DURATION_SECONDS` | `900` | Hard submission limit |
| `HEXAPOD_MAX_ARTIFACT_BYTES` | `2147483648` | Maximum streamed artifact size |
| `HEXAPOD_MAX_EXPERIMENT_ARTIFACTS` | `256` | Maximum finalized artifacts per experiment |
| `HEXAPOD_MAX_EXPERIMENT_ARTIFACT_BYTES` | `4294967296` | Maximum finalized evidence bytes per experiment |
| `HEXAPOD_ROBOT_COMMAND_SHUTDOWN_SECONDS` | `30` | Independent robot/camera wrapper shutdown allowance |
| `HEXAPOD_TAG_AUDIT_COMMAND` | empty | argv for the read-only `hexapod-audit-layout` tool |
| `HEXAPOD_TAG_LAYOUT` | empty | physical robot/floor tag inventory JSON |
| `HEXAPOD_TAG_POSE_TEMPLATE` | empty | tracker camera/calibration template snapshotted with every revision |
| `HEXAPOD_TAG_FLOOR_MAP` | empty | floor-anchor map used for overhead rectification |
| `HEXAPOD_TAG_PART_MAP` | empty | paired side-tag map used for consistency validation |
| `HEXAPOD_MAX_TAG_PHOTOS` | `36` | useful snapshots retained per phone scan |
| `HEXAPOD_MAX_TAG_PHOTO_BYTES` | `8388608` | maximum size of one phone snapshot |
| `HEXAPOD_AUTO_WORKER` | `true` | Set false for API-only processes |
| `HEXAPOD_BIND` / `HEXAPOD_PORT` | `127.0.0.1` / `8767` | Listener |

### Codex follow-through

The web service never launches Codex itself. Completion transitions instead
write two idempotent rows to the SQLite outbox in the same transaction: an
`analysis` job and a separate `advance` job that waits for that analysis. Each
eligible job is a separate Codex invocation. An obsolete advance job may instead
be durably marked superseded when an authorized runner resumes a later queue state. A
dedicated `hexapod-codex-orchestrator` process leases those rows, captures each
Codex run under `data/codex-runs/<job>/<attempt>/`, and recovers expired leases
after a restart. `GET /api/codex-jobs` and each enriched experiment response
show the receipts.

Every completed attempt also gets an audit transcript. Codex stdout and stderr
are initially captured in private hidden files, then deterministically redacted
and converted into both a complete machine-readable `events.jsonl` stream and a
human-readable `transcript.md` containing the submitted prompt and user-visible
model messages. Robot Lab records the transcript manifest SHA-256 in an
append-only database receipt; downloads recheck that digest and every archived
file. Each experiment's `codex_jobs[].transcript_attempts` contains authenticated
links for every attempt, including failed retries, and the experiment page shows
the same links. The Markdown transcript is viewer-readable. The fuller JSONL
event stream requires an operator, admin, or automation credential. Both use
`private, no-store` responses.

Tool-enabled engineering attempts use a narrower viewer transcript: it includes
the model's user-visible messages but omits the input project context, reasoning,
and tool events. Those remain available in the operator-only redacted JSONL.
The deadline wrapper enforces a kernel file-size ceiling even if the supervisor
dies; transcript rendering also has byte and line ceilings and records an
explicit `capture.truncated` event when a ceiling is reached.

These files intentionally remain under `data/codex-runs`, not the experiment's
artifact directory. A later LLM analysis is provenance about already-sealed
evidence and must never mutate or silently extend that evidence manifest.

The serialized `engineering` lane reconciles each succeeded
analysis into one deduplicated engineering job. It runs in the configured real
project checkout with the Mac's normal Codex configuration, MCP servers,
credentials, network, and tools, so it can update code, run simulation and RL
workflows, publish BuildViz, deploy, and use guarded Robot Lab/HTTP robot paths.
It first inspects the oldest saved plan and live robot state, and owns moving one
plan forward per job. Camera plus three distinct fresh healthy motor samples
counts as supervision when it establishes a normal pose/state. The runner clears
stale routine/framework latches and retries a complete bounded step up to twice;
it reports an operator action only when observations are unavailable or show a
persistent condition that actually needs hands-on correction.
The worker may commit and push its own tested fixes, preserving unrelated work.
An unfinished guarded plan continues as the same engineering job with its prior
receipt and remaining attempt budget. Once motion has begun, any continuation
finishes result registration and evidence sealing without replaying the motion.
A handoff succeeds only when its exact experiment is terminal and sealed;
reported blockers and exhausted attempts retain their actual status.
An unresolved blocked handoff stays saved but yields queue priority to the next
runnable plan; a later audited resume reactivates that same job and budget.
Operators can set an integer `parameters.queue_priority` (default `0`) when
queueing an urgent plan. Higher values run first, retaining creation order for
ties; this never interrupts an active job or cancels older plans.
Routine runs reuse prior validation for unchanged code and policies. Physical
actions retain bounded motion, current health checks, and actual fault stops.
Every attempt retains the transcript, structured receipt, before/after commit,
branch/upstream and git status, and a binary patch from the starting commit
through the resulting tree, including committed fixes. Registered-track RL `kick`/`feedback`
requests can also be written to a durable validated outbox; its dispatcher is
disabled unless the host explicitly installs a trusted bridge.

BuildViz is fully available to this lane. It uses the shared local hub on port
5183, leaves the dev server on 5173 alone, and mirrors new default versions to
the cloud hub according to the root project instructions. A cloud outage does
not block a successful local publish.

Evidence must be sealed before either job runs. Built-in runs and phone scans
seal automatically. An external guarded runner should stage large artifacts
while the plan is still waiting, attach its terminal result to the same ID,
upload any remaining files, then call
`POST /api/experiments/<id>/evidence-seal` (or the MCP
`seal_experiment_evidence` tool). Sealing freezes uploads and records the final
manifest SHA-256. For older clients that cannot explicitly seal, the supervisor
seals after the evidence directory has been quiet for
`HEXAPOD_CODEX_EVIDENCE_SETTLE_SECONDS` (60 seconds by default).
Active hidden upload leases prevent that automatic seal. If required evidence
is still missing or cannot be verified after
`HEXAPOD_CODEX_EVIDENCE_DEADLINE_SECONDS`, both jobs fail closed and the queue
is paused so one broken upload cannot silently freeze all later work.

The analyzer receives a verified copy containing only manifest-listed evidence
while running from a separate empty directory. It has no Robot Lab token,
network/search tool, shell, project rules, plugins, or other tools. Its structured
result can append a plain-language learning and propose up to three bounded
follow-ups. Robot Lab validates those recommendations, deduplicates exact specs,
and caps recursion at four generations and twenty accepted descendants per root.
Adaptive follow-ups become `external_guarded` saved plans. Robot Lab classifies
their immutable source context into two independent engineering resources: the
hardware worker drains robot-capable queue handoffs, while the offline/code
worker uses a separate checkout for analysis, replay, simulation, and code work.
Explicit `simulation_only: true` work never contacts or deploys to the robot.
The built-in simulated driver emits demo telemetry and is not an executor for
requested replay or MuJoCo work. Physical inspection findings do not reject
these offline follow-ups.

The small advance lane remains a token-free advisory/reconciliation lane. When
engineering is enabled, it records a non-pausing handoff of the oldest saved plan
to the dedicated hardware runner instead of manufacturing a manual blocker.
If engineering is deliberately disabled, it remains read-only and explains that
deployment choice. The blocker monitor texts only on real `blocked` or `dead`
receipts.

Only a physical analysis with `safety_disposition: stop` latches the whole
advancement queue. `needs_inspection` parks the scoped plan, and simulation-only
analysis cannot stop the hardware lane. The hardware runner may inspect the live
camera, three fresh motor samples, and evidence, then resume the queue itself
with an audited reason when they establish a normal state. A human can use the
same dashboard control when hands-on correction was actually necessary. The REST equivalent is
`POST /api/codex-queue/resume` with `X-Hexapod-Lab: 1`, a nonblank reason, and
`robot_inspected: true`; MCP exposes `get_robot_status`, `get_queue_controls`,
`resume_codex_queue`, `resume_runner_safety`, and `report_execution_progress`.

| Variable | Default | Meaning |
|---|---:|---|
| `HEXAPOD_CODEX_AUTOMATION` | `false` | Enable the separate Codex supervisor |
| `HEXAPOD_CODEX_BIN` | ChatGPT app bundled CLI | Exact `codex` executable |
| `HEXAPOD_CODEX_WORKDIR` | current directory | Reviewed snapshot used only for deterministic proposal/hash validation |
| `HEXAPOD_CODEX_MODEL` | `gpt-5.6-sol` | Model for both lanes |
| `HEXAPOD_CODEX_REASONING_EFFORT` | `medium` | Reasoning effort for all Codex lanes |
| `HEXAPOD_CODEX_ANALYSIS_TIMEOUT_SECONDS` | `2700` | Analyzer timeout |
| `HEXAPOD_CODEX_ADVANCE_TIMEOUT_SECONDS` | `5400` | Advancer timeout |
| `HEXAPOD_CODEX_EVIDENCE_SETTLE_SECONDS` | `60` | Legacy external-upload quiet period |
| `HEXAPOD_CODEX_EVIDENCE_DEADLINE_SECONDS` | `1800` | Fail-closed deadline for incomplete terminal evidence |
| `HEXAPOD_CODEX_MAX_EVIDENCE_SNAPSHOT_BYTES` | `536870912` | Maximum sealed evidence copied into one analysis snapshot |
| `HEXAPOD_CODEX_MAX_ATTEMPTS` | `5` | Retry ceiling for recoverable jobs |
| `HEXAPOD_CODEX_MAX_FOLLOWUPS_PER_ANALYSIS` | `3` | Adaptive proposals accepted from one analysis |
| `HEXAPOD_CODEX_MAX_FOLLOWUP_DEPTH` | `4` | Maximum adaptive lineage depth |
| `HEXAPOD_CODEX_MAX_FOLLOWUPS_PER_ROOT` | `20` | Maximum accepted descendants per root |
| `HEXAPOD_CODEX_TRANSCRIPT_MAX_CAPTURE_BYTES` | `67108864` | Kernel per-file ceiling and archived event-stream byte limit |
| `HEXAPOD_CODEX_TRANSCRIPT_MAX_EVENT_LINES` | `100000` | Maximum archived JSON events before an explicit truncation marker |
| `HEXAPOD_CODEX_TRANSCRIPT_MAX_HUMAN_BYTES` | `2097152` | Maximum rendered Markdown transcript size |
| `HEXAPOD_CODEX_ENGINEERING` | `false` | Enable project engineering workers |
| `HEXAPOD_CODEX_ENGINEERING_WORKDIR` | empty | Real git checkout reserved for hardware queue handoffs |
| `HEXAPOD_CODEX_OFFLINE_ENGINEERING_WORKDIR` | empty | Separate checkout for parallel offline analysis/code work; without it, hardware stays dedicated and offline jobs remain queued |
| `HEXAPOD_CODEX_ENGINEERING_TIMEOUT_SECONDS` | `7200` | Engineering attempt timeout |
| `HEXAPOD_CODEX_ENGINEERING_CONTEXT_MAX_BYTES` | `262144` | Maximum checked-in mission/workflow context injected per attempt |
| `HEXAPOD_CODEX_ENGINEERING_MAX_PATCH_BYTES` | `16777216` | Maximum durable binary patch receipt |
| `HEXAPOD_CODEX_ENGINEERING_MAX_ATTEMPTS` | `3` | Engineering retry ceiling |

The production supervisor has its own LaunchAgent and wrapper under `deploy/`
and `scripts/`. The analysis and fallback advance roles remain token-free and receive an
allowlisted environment. With both engineering workdirs configured, the
hardware role exclusively claims robot-capable queue handoffs and the offline
role claims analysis and explicit non-motion work concurrently in a different
checkout. Both retain normal project/network tooling; only the hardware role
may deploy or issue robot motion/control commands. The wrapper reads only the Robot Lab and RL-orchestrator
tokens from Keychain; Codex can use them for MCP authentication but filters them
out of model-generated shell environments. The deployed checkout must be
accessible to the background LaunchAgent.

The selected experiment record, bounded redacted excerpts of manifest-listed
text evidence, and selected manifest-listed images/contact sheets are sent to
OpenAI for analysis. Secret-like structured fields, authorization headers,
credentialed URLs, and private-key blocks are deterministically redacted before
the prompt is persisted or submitted. Keep unrelated private material out of
experiment evidence; visual attachments cannot be reliably text-redacted.

Generate tokens with `openssl rand -hex 32`. Credentials are hashed in memory for comparison and never written to the database or evidence. Environment variables remain visible to privileged local processes, so use an OS secret store in production. The Lab makes its data root owner-only (`0700`) and SQLite files owner-readable/writable (`0600`).

## Existing remote relay

[`deploy/camera-relay.yaml`](deploy/camera-relay.yaml) describes the existing camera service and reverse tunnel on port 8766. Hexapod Lab intentionally uses 8767 so it can run alongside that service. Remote exposure needs a separate authenticated tunnel or a deliberate additional route in the relay; keep TLS and application authentication enabled.

The deployed stable lab URL is `https://robot-lab.cwd1f0-new-cluster.coreweave.app`. Caddy terminates TLS and forwards this hostname without adding another authentication layer; Hexapod Lab itself provides browser sign-in at `/login` and bearer authentication for API/MCP clients. The local service and dual-port SSH tunnel run as macOS LaunchAgents, and the operator token is stored in Keychain under `Hexapod Lab API`. The background-safe runtime and evidence live under `~/Library/Application Support/Hexapod Lab/` because macOS restricts LaunchAgent access to `Documents`.

## Phone AprilTag walk-around

Open `/tag-scan` on the stable HTTPS Lab URL. Tap **Start rear camera**, begin
with the whole robot and at least four floor anchors in one overhead view, then
walk a slow low circle. The browser uploads throttled JPEG snapshots; the Lab
keeps only views that add a tag, an orientation, or a second confirming view.
If browser camera access is unavailable, the same page exposes a native
**Take one photo instead** fallback.

The scan is deliberately observation-only. Finalizing creates an ordinary
completed Robot Lab result containing the retained phone photos, annotated
photos, `tag-orientation-audit.json`, `tag-orientation-proposal.json`, and a
candidate `proposed-hexapod-1-apriltag-layout.json`. It does not change the
canonical tracker checkout, a servo zero, or any motor state. Moving a tag to
a different leg, joint, or face still requires a human mount-assignment review.

Every scan starts from an immutable snapshot. An operator can review a complete
proposal on its result page and activate it from approval time. Activation
appends a new effective-dated revision; it never edits an earlier one. The
read-only timeline is at `/tag-layout-history`.

Every Lab recording and imported result is pinned once to a revision. Its
evidence directory contains `vision-context.json` and exact snapshots of the
physical layout, tracker pose config, floor map, and part map. Manifest v2
includes that context, so later video analysis can use the recorded files
instead of silently opening today's configuration. External result producers
must send the original timezone-aware `recorded_at`; import/registration time
is never substituted for camera time.

The phone credential may use these narrowly scoped scan endpoints even when it
has the `viewer` role; it still cannot queue experiments, upload arbitrary
artifacts, or apply a proposal. Scan writes require the same-origin
`X-Hexapod-Scan: 1` header and have independent photo count/size limits.

The Lab invokes the camera-only detector from the separately owned
`hexapod-tracker` package. For the macOS LaunchAgent deployment, install both
local projects into the Lab environment and copy the four tracker configs to
the background-readable Application Support directory:

```sh
uv pip install --python "/Users/lukas/Library/Application Support/Hexapod Lab/venv/bin/python" \
  ./hexapod_walker/prototype_sts3215/hexapod-tracker ./experiment_lab
install -d "/Users/lukas/Library/Application Support/Hexapod Lab/tag-scan-config"
install -m 0644 \
  hexapod_walker/prototype_sts3215/hexapod-tracker/configs/hexapod-1-apriltag-layout.json \
  hexapod_walker/prototype_sts3215/hexapod-tracker/configs/apriltag_pose_config_20260831.json \
  hexapod_walker/prototype_sts3215/hexapod-tracker/configs/floor_tag_map.json \
  hexapod_walker/prototype_sts3215/hexapod-tracker/configs/hexapod_tag_map.json \
  "/Users/lukas/Library/Application Support/Hexapod Lab/tag-scan-config/"
```

## Calibration archive

Vision tools publish completed calibration evidence with operator credentials to
`POST /api/calibrations` or its compatibility alias
`POST /api/calibrations/import`. The request may be a raw tracker report or an
envelope containing `report`, optional `pose_config`, optional timezone-aware
`observed_at`/`recorded_at`, and optional `robot_id`. `GET /api/calibrations`
lists immutable records newest-first and `GET /api/calibrations/<id>` returns the
exact canonical report and optional pose configuration.

For compatibility, envelopes may use `calibration` for `report`, and `config`
or `configuration` for `pose_config`; additional envelope fields are retained as
source metadata. A flat raw report may also carry a top-level `pose_config`
sidecar. Credential-like source metadata is rejected rather than archived.

Importing is archival only: Robot Lab never applies the report, activates a tag
layout, changes a live configuration, sends a motor command, or changes a servo
zero. Records always report `status: archived`, `current: false`, and
`replay_ready: false`; `replay_status` explains whether pose evidence or a
historical tag layout was unavailable, or whether both were archived but not
activated. A resolved layout snapshot includes the revision identity and all
four configuration hashes. Archiving does not establish the pose config's role,
pin it to an experiment, execute replay, or make it eligible for automatic
selection. Publishers may send an `Idempotency-Key` header; exact retries return
the original record and reuse with different content is rejected.

## Blocker text alerts

`hexapod-blocker-monitor` is an independent Mac LaunchAgent that polls the
private CoreWeave `/api/blockers` feed and the local Robot Lab experiment API.
It sends a Messages text only for a newly filed operator blocker, a new failed
or stuck Robot Lab experiment, a succeeded Codex analysis that declares a
physical safety stop, a Codex job that remains eligible beyond its expected
deadline, or three consecutive service-check failures. Queued advance jobs are
not called stuck while the durable Codex queue is intentionally paused;
alerts are deduplicated in `data/blocker-alert-state.json`, and recovery is
reported once. Historical Robot Lab failures are baselined on first launch.
The recipient is stored in Keychain as account `recipient`, service
`Hexapod Blocker Alerts`; the phone number is never committed. The runner is
`scripts/run-blocker-monitor.sh`, and the LaunchAgent definition is
`deploy/com.lbiewald.hexapod-blocker-alerts.plist`.

Interactive MCP clients may register this endpoint as `robot_lab`, but do not
publish an operator credential through the global launchd environment. Inject a
narrowly scoped token into only the client process that needs it, or use a local
credential helper. The background completion supervisor itself uses no MCP
credential.

## Read-only mobile gateway

`/api/mobile/openapi.json` publishes a deliberately read-only OpenAPI schema
for a ChatGPT action or another mobile client. It combines Robot Lab experiment
evidence with the RL orchestrator's public LLM documents. Every data endpoint
requires the existing viewer/operator bearer token; the schema itself is public
so clients can import it.

The mobile surface cannot queue or cancel experiments, upload results, move the
robot, kick the orchestrator, or submit feedback. Import:

`https://robot-lab.cwd1f0-new-cluster.coreweave.app/api/mobile/openapi.json`

## Operations

### Externally guarded hardware queue

Ordinary `POST /api/experiments` requests default to `execution_mode=builtin`
and enter the built-in worker's `queued` lane. Physical hardware plans should
instead set `execution_mode` to `external_guarded`. They remain visibly
`waiting_for_operator` in the storage/API compatibility field (shown as
**waiting for guarded runner** in the UI) and are never claimed by the built-in
simulation worker. The serialized Codex engineering runner or a human operator
can advance them; an operator can cancel them with the normal endpoint.

After an independent safety-guarded runner finishes, attach its
`CompletedResultIn` payload with
`POST /api/experiments/{experiment_id}/result`. The queued name, description,
duration, and parameters must match exactly. The transition preserves the
experiment ID; exact retries are idempotent, while a changed payload or an
attempt to complete a built-in/terminal record is rejected. The MCP equivalents
are `queue_experiment` with `execution_mode=external_guarded` and
`complete_external_experiment`. Stage evidence before completion when possible,
then seal the final manifest as described above so analysis cannot race an
upload.

- The process-wide runner lock enforces one built-in worker per data root. Read/API replicas should still set `HEXAPOD_AUTO_WORKER=false`.
- Back up `lab.sqlite3` and `experiments/` together. For a live service, use SQLite's online backup API; otherwise stop writers and copy `lab.sqlite3`, any `-wal`/`-shm` companions, and evidence as one snapshot. Verify `integrity_check` and `foreign_key_check` before migration.
- A crash can leave a run marked `running`; recovery stops any recoverable process group, terminalizes the row as failed, and latches the runner. The guarded runner inspects camera plus fresh telemetry and may explicitly resume when normal; hands-on intervention is only needed for an unresolved physical condition. Another service restart alone does not clear the latch.
- Videos may contain people or private spaces. Apply suitable access and retention rules.

Run tests with `uv run --extra dev pytest`.
