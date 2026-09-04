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

The Streamable HTTP JSON-RPC endpoint is `http://127.0.0.1:8767/mcp` with an `Authorization: Bearer <token>` header. It exposes `list_experiments`, `get_experiment`, `queue_experiment`, `cancel_experiment`, `register_result`, and `read_artifact`.

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
| `HEXAPOD_AUTO_WORKER` | `true` | Set false for API-only processes |
| `HEXAPOD_BIND` / `HEXAPOD_PORT` | `127.0.0.1` / `8767` | Listener |

Generate tokens with `openssl rand -hex 32`. Credentials are hashed in memory for comparison and never written to the database or evidence. Environment variables remain visible to privileged local processes, so use an OS secret store in production.

## Existing remote relay

[`deploy/camera-relay.yaml`](deploy/camera-relay.yaml) describes the existing camera service and reverse tunnel on port 8766. Hexapod Lab intentionally uses 8767 so it can run alongside that service. Remote exposure needs a separate authenticated tunnel or a deliberate additional route in the relay; keep TLS and application authentication enabled.

The deployed stable lab URL is `https://robot-lab.cwd1f0-new-cluster.coreweave.app`. Caddy terminates TLS and forwards this hostname without adding another authentication layer; Hexapod Lab itself enforces Basic authentication for the website and bearer authentication for API/MCP clients. The local service and dual-port SSH tunnel run as macOS LaunchAgents, and the operator token is stored in Keychain under `Hexapod Lab API`. The background-safe runtime and evidence live under `~/Library/Application Support/Hexapod Lab/` because macOS restricts LaunchAgent access to `Documents`.

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

- Run only one worker against a SQLite file. Read/API replicas must set `HEXAPOD_AUTO_WORKER=false`.
- Back up `lab.sqlite3` and `experiments/` together.
- A crash can leave a run marked `running`; the service does not guess whether moving hardware is safe to resume. Inspect the robot before reconciliation.
- Videos may contain people or private spaces. Apply suitable access and retention rules.

Run tests with `uv run --extra dev pytest`.
