# Hexapod Lab

Hexapod Lab is a local, authenticated experiment queue for a robot. It accepts bounded experiment specifications through REST or MCP, executes one at a time, records telemetry and video, and publishes a durable result page with downloadable evidence.

It defaults to a simulated robot so the complete workflow can be tested without moving hardware. Connecting real hardware is an explicit configuration step.

## What it provides

- FIFO queue with `queued`, `running`, `succeeded`, `failed`, and `cancelled` states
- Bearer-token API/MCP authentication and role-based `viewer`, `operator`, and `admin` access
- Browser results UI using HTTP Basic with the same named tokens
- One evidence directory per experiment containing the submitted spec, JSONL telemetry, logs, MP4 video when configured, and a Markdown summary
- REST artifact streaming and MCP artifact discovery/reading
- Registration of externally completed guarded runs plus streamed artifact upload
- Immutable calibration-report archive with optional exact pose-config snapshots
- A phone-first AprilTag walk-around that saves raw/annotated views and an advisory orientation proposal
- Immutable, effective-dated AprilTag history with exact replay snapshots for every recording
- A single-consumer worker so two experiments never command the robot concurrently
- Duration limits, cancellation, an append-only event trail, and no shell interpolation of configured commands

## Quick start

Python 3.9+ and `uv` are supported.

```sh
cp .env.example .env
# Replace every example credential in .env first.
uv sync --extra dev
set -a; source .env; set +a
uv run hexapod-lab
```

Open `http://127.0.0.1:8767/` and sign in with the `name` and `token` from a configured `role:name:token` entry. For example, `operator:robot-operator:a-long-random-secret` becomes username `robot-operator` and password `a-long-random-secret`.

Queue a simulated experiment:

```sh
curl -H 'Authorization: Bearer a-long-random-secret' \
  -H 'Content-Type: application/json' \
  -d '{"name":"Tripod gait baseline","description":"Straight, level floor","duration_seconds":5,"parameters":{"speed_mps":0.1}}' \
  http://127.0.0.1:8767/api/experiments
```

The OpenAPI explorer is at `/docs`. Data is stored under `lab-data/experiments/<experiment-id>/` and queue metadata is in `lab-data/lab.sqlite3`.

Guarded runners that already own robot-specific safety can register a completed
result with `POST /api/results`, then stream each flat-named evidence file with
`PUT /api/experiments/<id>/artifacts/<filename>`. Existing artifacts are never
overwritten. The equivalent MCP metadata tool is `register_result`; large files
use the authenticated HTTP upload path and are subsequently discoverable from
both MCP and the website.

## MCP connection

The Streamable HTTP JSON-RPC endpoint is `http://127.0.0.1:8767/mcp` with an `Authorization: Bearer <token>` header. It exposes `list_experiments`, `get_experiment`, `queue_experiment`, `cancel_experiment`, `register_result`, `read_artifact`, `list_tag_layout_revisions`, `get_tag_layout`, `list_calibrations`, and `get_calibration`.

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

The adapter must enforce robot-specific constraints: allowed gaits, workspace boundaries, maximum joint speed/torque, battery thresholds, hardware e-stop status, and a safe neutral pose. Do not enable `command` until those checks are tested locally. Software cancellation is not an emergency stop.

## Configuration

| Variable | Default | Meaning |
|---|---:|---|
| `HEXAPOD_API_KEYS` | none (startup fails) | Comma-separated `role:name:token` records |
| `HEXAPOD_DATA_DIR` | `./lab-data` | SQLite database and evidence root |
| `HEXAPOD_DRIVER` | `simulated` | `simulated` or `command` |
| `HEXAPOD_ROBOT_COMMAND` | empty | Real adapter argv |
| `HEXAPOD_CAMERA_INPUT` | empty | ffmpeg-compatible input |
| `HEXAPOD_MAX_DURATION_SECONDS` | `900` | Hard submission limit |
| `HEXAPOD_MAX_ARTIFACT_BYTES` | `2147483648` | Maximum streamed artifact size |
| `HEXAPOD_TAG_AUDIT_COMMAND` | empty | argv for the read-only `hexapod-audit-layout` tool |
| `HEXAPOD_TAG_LAYOUT` | empty | physical robot/floor tag inventory JSON |
| `HEXAPOD_TAG_POSE_TEMPLATE` | empty | tracker camera/calibration template snapshotted with every revision |
| `HEXAPOD_TAG_FLOOR_MAP` | empty | floor-anchor map used for overhead rectification |
| `HEXAPOD_TAG_PART_MAP` | empty | paired side-tag map used for consistency validation |
| `HEXAPOD_MAX_TAG_PHOTOS` | `36` | useful snapshots retained per phone scan |
| `HEXAPOD_MAX_TAG_PHOTO_BYTES` | `8388608` | maximum size of one phone snapshot |
| `HEXAPOD_AUTO_WORKER` | `true` | Set false for API-only processes |
| `HEXAPOD_BIND` / `HEXAPOD_PORT` | `127.0.0.1` / `8767` | Listener |

Generate tokens with `openssl rand -hex 32`. Credentials are hashed in memory for comparison and never written to the database or evidence. Environment variables remain visible to privileged local processes, so use an OS secret store in production.

## Existing remote relay

[`deploy/camera-relay.yaml`](deploy/camera-relay.yaml) describes the existing camera service and reverse tunnel on port 8766. Hexapod Lab intentionally uses 8767 so it can run alongside that service. Remote exposure needs a separate authenticated tunnel or a deliberate additional route in the relay; keep TLS and application authentication enabled.

The deployed stable lab URL is `https://robot-lab.cwd1f0-new-cluster.coreweave.app`. Caddy terminates TLS and forwards this hostname without adding another authentication layer; Hexapod Lab itself enforces Basic authentication for the website and bearer authentication for API/MCP clients. The local service and dual-port SSH tunnel run as macOS LaunchAgents, and the operator token is stored in Keychain under `Hexapod Lab API`. The background-safe runtime and evidence live under `~/Library/Application Support/Hexapod Lab/` because macOS restricts LaunchAgent access to `Documents`.

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
or stuck Robot Lab experiment, or three consecutive service-check failures;
alerts are deduplicated in `data/blocker-alert-state.json`, and recovery is
reported once. Historical Robot Lab failures are baselined on first launch.
The recipient is stored in Keychain as account `recipient`, service
`Hexapod Blocker Alerts`; the phone number is never committed. The runner is
`scripts/run-blocker-monitor.sh`, and the LaunchAgent definition is
`deploy/com.lbiewald.hexapod-blocker-alerts.plist`.

The laptop's Codex configuration registers this endpoint as `robot_lab`. Its `bearer_token_env_var` is `HEXAPOD_LAB_TOKEN`; a login LaunchAgent reads the value from Keychain and places it in the user's launchd environment. Restart the Codex/ChatGPT desktop app after initial setup so newly launched tasks inherit it.

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
`waiting_for_operator` and are never claimed by the built-in worker. An
operator can cancel them with the normal cancellation endpoint.

After an independent safety-guarded runner finishes, attach its
`CompletedResultIn` payload with
`POST /api/experiments/{experiment_id}/result`. The queued name, description,
duration, and parameters must match exactly. The transition preserves the
experiment ID; exact retries are idempotent, while a changed payload or an
attempt to complete a built-in/terminal record is rejected. The MCP equivalents
are `queue_experiment` with `execution_mode=external_guarded` and
`complete_external_experiment`.

- Run only one worker against a SQLite file. Read/API replicas must set `HEXAPOD_AUTO_WORKER=false`.
- Back up `lab.sqlite3` and `experiments/` together.
- A crash can leave a run marked `running`; the service does not guess whether moving hardware is safe to resume. Inspect the robot before reconciliation.
- Videos may contain people or private spaces. Apply suitable access and retention rules.

Run tests with `uv run --extra dev pytest`.

### Submit a reviewed guarded plan

The walking benchmark generator writes a JSON document with `queue_payloads`.
Validate it locally, then submit it with the configured bearer credential:

```sh
uv run python -m hexapod_lab.guarded_queue /path/to/plan.json
uv run python -m hexapod_lab.guarded_queue /path/to/plan.json --submit --receipts /path/to/receipts.json
```

The client reads `HEXAPOD_LAB_TOKEN`; it never stores the credential. It refuses
servers whose OpenAPI schema does not advertise `external_guarded`, verifies new
jobs enter `waiting_for_operator`, reuses matching plan IDs, and rejects changed
specifications under an existing ID. This client does not execute robot commands.
After an interrupted submission, inspect the receipts and rerun the identical
plan; do not rename IDs merely to bypass a mismatch. Serialize submissions from
different clients: plan-ID deduplication is client-side, not a server transaction.
