# Reusable robot observation commands

Use `robot_observe.py` instead of reconstructing camera curls, three-sample
telemetry loops, and trial-summary scripts each turn. It uses HTTP GET only;
errors and exit never arm, move, lower, or disable torque. No deployment is needed.

From the repository root, configure the current robot and camera service URLs:

```sh
export HEXAPOD_HOST=http://hexapod.local:8080
# Set HEXAPOD_CAMERA_URL to the current camera service, including http:// and :8766.
# Discover/verify the camera host; do not reuse a historical private IP blindly.
uv run python -m linux_control.robot_observe --help
```

If mDNS fails, use `make -C hexapod_walker/prototype_sts3215 robot-resolve`
and pass the resolved address through `HEXAPOD_HOST`. URLs can also be supplied
as `--robot-url` and `--camera-url` **before** the subcommand. The camera service
must already be running; this helper does not open camera devices or start servers.

## Four commands

```sh
# Controller activity, armed state, and one concise fresh feedback summary.
uv run python -m linux_control.robot_observe status

# Two camera images, three fresh complete scans, all scan attempts, and demo status.
# Requires HEXAPOD_CAMERA_URL. Use a new output directory for each observation.
uv run python -m linux_control.robot_observe snapshot --out /tmp/h1-observation-01

# Passive, bounded telemetry recorder; writes each sample immediately, prints a final summary.
uv run python -m linux_control.robot_observe watch \
  --seconds 10 --interval 0.5 --out /tmp/h1-feedback-01.jsonl

# Summarize an existing recovery-nudge trial without contacting any service.
uv run python -m linux_control.robot_observe trial /path/to/trial-directory
```

For a longer passive recording, `watch` supports up to 1,800 seconds per call.
Run it in a managed background tool session when continued interaction is needed.
It is an evidence recorder, **not an active-motion watchdog**. It does not stop a
moving robot when telemetry fails. Keep the existing controller guards and the
active operator's abort path. Each HTTP read has a three-second timeout; the
overall recording can finish up to one pending read after its requested duration.

The same entry point is a shell helper:

```sh
source hexapod_walker/prototype_sts3215/linux_control/dev_loop.sh
hex_observe status
hex_observe snapshot --out /tmp/h1-observation-02
```

`hex_observe` uses the existing `hex_py` wrapper, which runs from
`prototype_sts3215/`; use absolute output paths to avoid working-directory ambiguity.
The unsourced equivalent is `bash linux_control/dev_loop.sh observe ...` from
`prototype_sts3215/`.

## Reading the evidence

`snapshot` saves `camera0.jpg`, `camera1.jpg`, and `observation.json`. Independent
camera/status/telemetry reads run concurrently. A failed camera still leaves the
other image and telemetry report available. Existing output directories/files
are refused rather than overwritten.

Three samples means **distinct timestamps**, all complete (18 joint records with
finite position/current/voltage/load/temperature and attitude fields), each within
two seconds of receipt. Up to half a second of forward clock skew is tolerated.
Cached duplicates do not count; an incomplete/stale scan resets the count. Attempts
are bounded at 12 and preserved for diagnosis. This checks data quality only:
high current or temperature is still faithfully reported, never labeled healthy.

`observations_complete: true` is not permission to move or proof of normal pose.
Inspect both images and electrical/thermal readings under the existing hardware
rules. Image request/receive times are saved, but a relay can return an old frame;
they do not establish sensor freshness. A JPEG download also does not prove video
recording is active. Inspect the camera service/recorder when those facts matter.

Exit status is 0 for complete observations or a parsed offline summary, 2 for
incomplete observations, read/argument failure, or an existing output destination.
Raw feedback retains `raw_deg` and `deg`; the offline summary labels these
`raw_deg` and `logical_deg`. It never infers contact, body lift, or successful
unloading from encoder progress. Missing optional `body-monitor.json` is allowed.

Before recovery work, read [the recovery lessons](../RECOVERY_LESSONS.md).
