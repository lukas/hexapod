# Agent conventions — hexapod

## Two parallel walking goals

[RL_GOALS.md](hexapod_walker/prototype_sts3215/RL_GOALS.md) is canonical for
purpose and priorities (Lukas, 2026-09-08): (1) smooth joystick walking on the
physical robot by any effective means, to advance physical builds now;
(2) the same physical outcome with walking learned entirely through RL and
no demonstrations anywhere in its training lineage. BC/AMP/teacher-assisted
methods belong to the first goal even when assistance is later removed.
Both goals must also be shown working in simulation: provide an interactive
joystick demo, a viewable video and a reproducible launch path for each,
following `RL_GOALS.md`. Report sim and hardware readiness independently.
Run both goals in parallel. Method/simulation gates do not establish physical
goal completion; do not require every method or one monolithic policy to
succeed before delivering useful walking. Preserve budgets, evidence and
hardware observation/ownership rules below.

## MCP and Git: standing authorization

Lukas authorizes routine MCP calls and Git commands needed to complete the
active project task. Run them without another permission question. This includes
status, reports, logs, fetch, branch/worktree setup, staging, commits, merge
conflict resolution, and normal pushes that deliver the requested work.
Pass this authorization to delegated agents. Do not turn an existing
authorization into a fresh approval gate merely because a tool uses MCP,
accesses the network, or writes Git metadata.

Use the project's `.codex/config.toml` approval defaults. A real tool or
organization restriction must still be respected; report its concrete reason
instead of asking for routine authorization again. The robot observation and
emergency-handling requirements below still apply to physical actions.

## Losing work to a narrow fetch refspec

Some checkouts under `~/Library/Application Support/Hexapod Lab` have a
**narrow** `remote.origin.fetch` listing individual `codex/*` branches and
never `main`. There `origin/main` silently freezes: pushes look like
non-fast-forwards, `git pull` cannot help, and `git rebase origin/main`
reports "up to date" against a stale ref. A finished vision-service feature
(1595 lines, tests passing) sat unpushed this way while the session concluded
GitHub was broken and went looking for SSH keys.

- Enumerate **clones** before worktrees. `engineering-checkout-v1` and `-v2`
  are separate clones; `-v3`, `engineering-offline-v1`, `codex-workspace` and
  the `observer-runtime-*` trees are worktrees of them. A worktree has a
  `.git` *file*; a clone has a `.git` *directory*. Missing that distinction is
  how the feature got overlooked.
- Check reachability with `git ls-remote`, not `git branch -r --contains` —
  the latter reports everything as unpushed in exactly the narrow-refspec
  clones that most need checking.

`tools/git_unpushed_audit.sh` does both, repairs a missing `main` refspec in
place without widening a deliberately narrow one, and pushes anything
unreachable with `--push`. Worktrees live in `/tmp`, which macOS prunes, so a
commit existing only there is one cleanup away from gone.

## Manual project overseer: register purpose and evidence

The project overseer is manual-only; do not schedule or enable it without a
new user request. See
`hexapod_walker/prototype_sts3215/rl_move/overseer/README.md` for its CLI.
Discovery inventories existing Claude/Codex/Lab/RL work without controlling it.
For new long-running work, register a stable agent ID, logical task ID, parent,
execution owner, goal (`any_means`/`rl_only`) and scope. Children share their
parent's logical task ID. At meaningful checkpoints record the changed evidence,
a continue/change/stop assessment and the next bounded step; a heartbeat alone
is not progress. Report complete nonoverlapping provider cost receipts when
available; keep unavailable cost unknown. Overseer work and its descendants must
be marked as such so their spending/activity cannot trigger their own review.
All paid overseer calls share one durable wake budget: $20 total including
children, begin wrapping up at $15, $80 per rolling day. Existing execution
owners retain control; a review proposal is not a stop/restart or hardware command.

## Python commands: use uv

For all local project Python commands, use `uv` instead of bare
`python`, `python3`, or direct `.venv/bin/python` paths.

- Prefer `uv run python ...` for scripts and `uv run python -m ...`
  for modules.
- Prefer `uv run pytest ...` or `uv run python -m pytest ...` for
  tests.
- Environment: the repo root `pyproject.toml` + `uv.lock` define the ONE
  venv (`<checkout>/.venv`). `uv sync` creates/updates it (per worktree —
  see `.cursor/rules/agent-worktrees.mdc`); `uv run` uses it from any
  directory. Add dependencies to `pyproject.toml` and run `uv lock`; do not
  `uv pip install` ad hoc, it is lost on the next sync.
- Do not rewrite historical logs, generated run records, vendored code,
  or shebangs just to say `uv`. Native MuJoCo GUI/viewer launches on
  macOS are the named exception: use `uv run mjpython ...` or the
  repo's Makefile wrapper, because Cocoa needs `mjpython`.
- The Uno Q also uses uv. Its web service should launch as
  `/home/arduino/.local/bin/uv run python ...`.

## RL orchestrator status URLs

Routine RL status, reports, metrics, logs, and existing video downloads are
standing-authorized reads; do not ask Lukas for task-level approval or wait
for a reply before reading them. Prefer authenticated RL MCP tools
(`eval_report`, `run_metrics`, `get_run_videos`, etc.) over shell/kubectl
artifact downloads, which can trigger separate sandbox network approvals.
Use the MCP tool's direct video links for playback/download. Do not interpret
this read authorization as permission to change unrelated security settings
or bypass an enforced sandbox restriction.

If native RL MCP tools are absent from the current session, use the documented
authenticated JSON-RPC fallback in
`hexapod_walker/prototype_sts3215/rl_move/orchestrator/README.md`:
prepare the private curl configuration locally, then invoke `curl -f -sS`
directly with `--config` and `--data` (use `-o` for files). This exact route
was verified without a new prompt. Pass this access method to delegated agents
too; do not send routine report reads through ad hoc kubectl downloads.

When the user asks for the agent/orchestrator/progress dashboard, start here:

- Public human dashboard:
  `https://hexapod.cwd1f0-new-cluster.coreweave.app/now`
  (token-gated; append `?key=<status-token>` on first visit).
- Public agent/LLM-readable index:
  `https://hexapod.cwd1f0-new-cluster.coreweave.app/llms.txt`
  (no token required).
- Local port-forward fallback:
  `kubectl --kubeconfig=$HOME/.kube/coreweave.yaml port-forward hexapod-sweep-friction 8090:8090`
  then open `http://127.0.0.1:8090/now`.

The public host is served by the `hexapod-status` LoadBalancer and Caddy on the
controller pod, proxying to `status_server.py` on `:8090`. This is distinct
from the local Mac robot/sim web UI at `http://localhost:8898/rl` and from
BuildViz on `:5183`.

## Where orchestrator STATE lives (vs. code)

The RL orchestrator's runtime state is NOT in this repo. It is its own
repo, written by exactly one process (the controller pod's `snapshot.sh`)
and read by everyone else:

- Repo: `https://github.com/lukas/hexapod-state` (private).
- On disk: `<checkout>/.state/` — a clone of that repo. Refresh with
  `make -C hexapod_walker/prototype_sts3215 state` (clones if missing).
  Worktrees symlink `.state` to the main checkout's clone. Override with
  `HEXAPOD_STATE_DIR`; the controller sets it in `/root/orchestrator.env`.
- On the web: the status URLs above (`/now`, `/llms.txt`), served from
  these same files by `status_server.py`.

What is there: `experiments.json` (the ledger — one entry per launched run,
the source of truth), `backlog.json` / `backlog_failed.json` (launch queue),
`pending_evals.json`, `rl_docs/runs/<run>.md` (per-run stories, GENERATED
from the ledger — never edit), `RL_LOG.md` (one-line-per-cycle log, append
only via `ops.sh logline`), and the machine-written journals
`OPERATOR_QUESTIONS.md`, `rl_docs/SKILLS.md`, `rl_docs/tracks/<track>/STATUS.md`.
In this repo, `hexapod_walker/prototype_sts3215/rl_docs/runs`, `RL_LOG.md`,
`rl_docs/SKILLS.md`, `rl_move/orchestrator/OPERATOR_QUESTIONS.md` and each
track `STATUS.md` are symlinks into `.state`, so existing read paths keep
working once `.state` exists. To EDIT a journal, open the `.state/...` path
(editors refuse to write through a symlink). Human-owned docs stay here:
`STATUS.md`, `CURRENT_TRUTHS.md`, `RL_PLAN.md`, `RESEARCH_RULES.md`, the
track design docs. Code resolves the real paths through
`rl_move/orchestrator/state_dir.py`; do not add `HERE / "experiments.json"`
style paths again. Curated prose (`STATUS.md`, `CURRENT_TRUTHS.md`,
`RL_PLAN.md`, `rl_docs/tracks/*/STATUS.md`) and config (`tracks.json`,
`guardrails.yaml`) stay in this repo.

## Tests: fast, mechanics-only, green

`hexapod_walker/prototype_sts3215/RESEARCH_RULES.md` "Tests" is binding
for every agent, not just the orchestrator: tests finish in under 5 s
(else `@pytest.mark.slow` with a reason), check code paths rather than
measured reward totals or rollout orderings, set the sim model family
explicitly via `monkeypatch.setenv("HEXAPOD_MODEL_SOURCE", ...)`, never
depend on generated artifacts, live only under `rl_move/tests/` (or next
to robot code in `linux_control/`), and `main` stays green. The 14k-line
rollout-ranking bank (`test_task_semantics.py`) was retired on
2026-09-08 and must not be recreated. Run the default loop with
`make -C hexapod_walker/prototype_sts3215 test-fast` (parallel, skips
slow) and the whole suite with `make ... test`.

## BuildViz: semantic catalog and shared hubs

Start with MCP **`list_catalog({collection:"hexapods"})`**, then
**`get_catalog_item({id:"..."})`**, before choosing or creating a build.
The catalog organizes persistent robots, assemblies, studies, and saved views;
old build IDs, branches, and versions remain their source addresses. CLI
fallback: `buildviz catalog list --collection hexapods --json` and
`buildviz catalog show <id>`. Read the returned source and children rather than
inferring identity from an old project name or the number of versions.

The three main robot entries on the cloud hub are:

- [Hexapod 1 — original STS](https://buildviz.cwd1f0-new-cluster.coreweave.app/?catalog=hexapod-1)
  (`hexapod-1`): original RobotLab STS assembly. Its as-built reference is pinned
  to `prototype_sts3215/hexapod-v1`, branch `main`, version
  `2026-08-07-f9c91cf`; later design revisions are separate.
- [Hexapod 2 — three-bearing STS](https://buildviz.cwd1f0-new-cluster.coreweave.app/?catalog=hexapod-2)
  (`hexapod-2`): the owner confirms **two lower bearings and one upper
  bearing**, with a change to spacer-equipped parts **in progress**. The
  selected retrofit is `sts-horn-compression-study` (Spacer-equipped joint
  parts). Its exact installed revision, bearing models, and per-leg retrofit
  progress remain unrecorded; see
  `hexapod_walker/prototype_sts3215/robots/hexapod-2.yaml`. The catalog's main
  STS source is only a design reference, and the current rigid-hip design's
  one-lower/one-upper stack is not an exact match. The old bundled
  `buildviz/hexapod-2` scene does not identify this physical robot.
- [Next hexapod — metal C-clamps](https://buildviz.cwd1f0-new-cluster.coreweave.app/?catalog=hexapod-metal)
  (`hexapod-metal`): planned purchased-56-mm-bracket build, sourced from
  `prototype_sts3215/premade-chorn-56`. Custom CNC overhead and split-clamp
  alternatives remain studies beneath this robot.

Catalog discipline for every agent:

- Use **`create_view`** for an inspection selection of existing geometry,
  pinned to an exact source branch and revision. Select actual instance IDs
  or part types. Showing a chassis or leg by itself does not create another
  robot, build, or experimental branch; an assembly can select components
  from the same full-robot snapshot without copying geometry.
- Use **`publish_revision`** for geometry changes under the existing robot or
  component identity. Classify geometry alternatives, fit coupons, loading
  setups, and comparisons as **studies**, with an explicit parent. A study
  can display a whole robot without becoming a physical-robot entry.
- Every new revision needs a **one- or two-sentence message** stating what
  changed and why when the reason is known. Preserve original messages and
  publication times; mark reconstructed notes retrospective. A view-only
  change belongs to its saved view, not the mechanical revision history.
- Keep current CAD `source` separate from **`asBuilt`**. Record installed
  hardware only from evidence; pin as-built and named milestone references.
  Do not infer installation from the latest scene, a design label, or a
  version number. Version numbers have been reused; use recorded timestamps
  and messages to understand sequence.
- Preserve old source IDs, branches, histories, and URLs. Archive obsolete
  catalog entries instead of deleting their source histories. Reuse the
  catalog identity when publishing to an existing source.

### Two-port convention (5183 central, 5173 dev)

BuildViz uses exactly **two** fixed ports. Never start a server on any other
(random) port.

- **`5183` = the shared central hub — the ONE instance everyone uses.** It
  serves *every* project's builds at once; select one with `?build=<id>`. All
  project builds register into and are viewed from `5183`.
- **`5173` = reserved for BuildViz's own dev/testing** (`npm run dev`). It is a
  local dev server, never the hub. **Leave it alone** — do not view project
  builds on it, do not register into it, do not kill it. (On this machine it is
  kept alive by the `com.lbiewald.buildviz` LaunchAgent — don't touch that.)

Rules:

- **View** any build at `http://127.0.0.1:5183/?build=<id>`
  (e.g. `http://127.0.0.1:5183/?build=hexapod-prototype`).
- **Start / ensure** the central hub with the one canonical command
  (idempotent):

  ```sh
  npx buildviz hub --detach          # single hub on :5183; no-op if already up
  npx buildviz hub status            # is it up? url / pid / build count
  ```

- **Do NOT** start a new dev server on a random port to view a build — no
  `npm run dev -- --port 5199`, no `npx buildviz --port 5174`, no auto-picked
  Vite port. Those are the port sprawl this rule prevents. Do **not** touch
  `5173`. `register`/`push` auto-start the `5183` hub, so the hub is the only
  thing you ever launch.
- **Expose** a project's build by REGISTERING (or pushing) it into the hub:

  ```sh
  npx buildviz register <build-dir> --project <project> --build <build>
  # or send a scene.json layout straight to the hub:
  npx buildviz push --project <project> --build <build> --version main --scene scene.json -m "Describe the mechanical change and its purpose."
  ```

  The per-project `make view-buildviz` targets already do this and open the hub
  URL — prefer them.

- **Verify** the hub before trusting a server: read `~/.buildviz/server.json`
 and confirm `GET http://127.0.0.1:5183/__buildviz/status` returns
 `{ "service": "buildviz-hub" }`. A plain dev server also answers
 `/builds/index.json`, so that alone never proves it is the hub.
- **Mirror to the CLOUD hub** (standing convention, Lukas, Aug 2026): after
 publishing a new default version to the local hub, ALSO push it to the
 CoreWeave-hosted hub at
 `https://buildviz.cwd1f0-new-cluster.coreweave.app` so it is viewable off
 this machine. For the hexapod this is automatic — the sts3215
 `make verify-buildviz` target ends with a failure-tolerant cloud mirror
 step (standalone: `make -C hexapod_walker/prototype_sts3215 push-cloud`,
 script: `tools/push_cloud_buildviz.py`). Auth: the remote hub requires
 `X-API-Key` = `BUILDVIZ_API_KEY` (same key as the local hub; canonical
 source is the CoreWeave k8s secret `buildviz-api-key`:
 `KUBECONFIG=~/.kube/coreweave.yaml kubectl get secret buildviz-api-key -o
 jsonpath='{.data.key}' | base64 -d`). A dead network must never fail the
 local publish — mirror later with `push-cloud`.

Reference: `/Users/Shared/buildviz/README.md` ("How to run BuildViz") and
`/Users/Shared/buildviz/BUILDVIZ_LLM_INTERFACE.md`. If the private package is
not linked into npm's executable path, invoke the same CLI directly as
`/Users/Shared/buildviz/bin/buildviz.mjs`; do not ask npm to download it from
the public registry.

### Current build ids in the hub

`hexapod-prototype` (prototype_v1, animated gait), `prototype_sts3215`
(full robot; motion baked into its single scene.json — the separate
`prototype_sts3215_motion` build id was retired). The `prototype_sts3215`
hub PROJECT also groups sibling builds:
`prototype_sts3215/rigid-hip` (rigid-hip concept variant,
`concepts/rigid_hip`; v1..v20 history migrated with push messages),
`prototype_sts3215/cnc-chorn-overhead` (CNC C-clamp legs-over-head
concept, `concepts/cnc_chorn_overhead`),
`prototype_sts3215/chassis-reinforcement-test`, and
`prototype_sts3215/tibia-yoke-reinforcement-test`. Additional isolated
concept builds are `prototype_sts3215/cnc-chorn-two-piece`,
`prototype_sts3215/fsr-sensor-foot`,
`prototype_sts3215/horn-compression-limiters`, and
`prototype_sts3215/premade-chorn-56`; see
`hexapod_walker/prototype_sts3215/concepts/README.md` for the catalog. The old standalone
concept project ids were retired and deleted locally, but the cloud hub
has no delete endpoint, so STALE copies linger there — ignore:
`cnc_chorn_overhead` (retired 2026-08-27), `sts3215-rigid-hip`
(retired 2026-08-27), and the older `sts3215-rigid-hip-step`.
Two-segment `--project` + `--build` ids resolve fine in the current
viewer on both hubs — via `?project=<p>&build=<b>` and even the legacy
`?build=<p>/<b>` form (verified 2026-08-27; the old ak40-era
"two-segment ids don't resolve" gotcha is fixed, though `prototype_ak40`
itself remains a FLAT id registered with `--build-id prototype_ak40` —
regenerate via `make -C hexapod_walker/prototype_ak40 view-buildviz`).
`prototype_v1/chassis`, `prototype_v1/leg`, `prototype_v1/leg/coxa`,
`rideable_v1`, plus older collision/demo builds (and non-hexapod projects
from the `weird_objects` repo, e.g. `robot-cat`). List them live
with `npx buildviz hub status` or open `http://127.0.0.1:5183/`.

## Scope of robot work

The user grants standing authority to carry out bounded robot experiments,
necessary deployment (including relevant firmware), and routine recovery within
an active robot task without asking for authorization again each turn. Favor
execution and measured progress over repeated confirmation. Work in the known
test area with live observations and an available abort path; this does not
extend to unrelated tasks or an unknown, unobserved environment.

A live camera view plus three distinct fresh healthy telemetry samples counts
as supervision and inspection for routine motion and recovery when it establishes
normal pose and state. Request hands-on help only when those observations are
unavailable or inconclusive, or when they show a persistent condition that
actually requires physical correction.

Do not modify firmware `.ino` files or CAD geometry as a side effect of an
unrelated task. This standing authority supersedes older per-turn permission
wording in project runbooks; their technical checks and emergency responses
still apply.

## Hexapod STS3215 (`prototype_sts3215`) — hardware

**2026-08-06 incident:** agents drove stand/plant with wrong logical zeros
(straight-out legs already read knee ≈ −80°). That caused tip/brownout,
~7 A stilt holds, and a cooked knee servo. Hardware is FULLY RESOLVED
(servo replaced 2026-08-09, bus verified 18/18 healthy — do NOT
resurface it as an open issue); the process lessons are what remain.
Hard rules:

1. **Use bounded, observed motion within the active robot task.** Continue
   experiments, necessary deployment, and routine recovery under the standing
   authority above; do not request another per-turn motion approval.
2. **HTTP over SSH** for control (`:8080` `/api/*`, `/cmd`). Use SSH for
   necessary deployment and service recovery within the active task.
   For robot-control/web edits, use the documented fast loop:
   `make -C hexapod_walker/prototype_sts3215 robot-check`,
   `robot-unit-check`, `robot-status`, and `robot-deploy`
   (`linux_control/dev_loop.sh`). These helpers do not move the robot;
   `robot-deploy` only restarts the web service. If `hexapod.local` is
   flaky, use `make ... robot-resolve` and pass the temporary IP via
   `HEXAPOD_HOST`/`HEXAPOD_SSH` instead of hard-coding it.
3. **Set-zero-here before absolute poses.** If encoders disagree with the
   photo, remap zero — do not command software 0°/stand/plant.
4. **Establish basic controls before loaded motion.** Check live IDs, zeros,
   single-joint air moves, and predict↔encoder agreement. Once these are solid,
   proceed with stand/plant/balance as needed for the active task.
5. **Observe stand-up / plant blends live.** Use a verified starting pose and
   bounded transition in the known test area with an available abort path.
   Hip0+knee80 is stilts, not a low plant.
6. **Stop on a confirmed tip, brownout, hot motor, or persistent missing servo ID.** A
   single missing feedback sample is telemetry noise: retry and require three
   consecutive fresh misses before limping. After a recoverable signal or
   framework stop, inspect the camera and require three fresh healthy samples,
   then retry the complete failed step up to twice. Do not blindly retry an
   actual tip, visibly bad posture, blend failure, brownout, hot motor, jam,
   surprise force, or hard/sustained current event. Reinspect the current pose
   and recovered electrical/thermal telemetry; resume remotely when that
   evidence conclusively establishes a normal state, and request hands-on
   correction only when the condition persists or remains inconclusive. An
   alert or stale historical stop is not by itself
   a confirmed current hazard: use the live camera and telemetry to distinguish
   a recovered/transient condition from an ongoing fault. If hands-on inspection
   is genuinely needed, report that concrete need; another routine permission
   question does not resolve a fault.

7. **Grounded diagnostic retry rule.** For supported, single-joint grounded
   calibration/sysid tests, isolated bad current samples do not end the run:
   require three consecutive over-threshold readings. A confirmed trip limps,
   waits for feedback/current to recover, then retries up to twice
   automatically. A third failed attempt terminates the test limp. Never apply
   this retry rule to a tip, brownout, hot motor, stand/plant motion, jam, or
   surprise force. A single missing-ID sample is not a confirmed stop; use the
   three-consecutive-read rule above.

Details: `.cursor/rules/hexapod-sts-hardware-safety.mdc`,
`hexapod_walker/prototype_sts3215/EMERGENCY_HANDLING.md`, and
`hexapod_walker/prototype_sts3215/rl_move/API.md`. The emergency-handling
document is canonical when choosing hold versus controlled stop versus limp.

### Local Mac web hub on `:8898`

Canonical command:

```sh
cd ~/hexapod/hexapod_walker/prototype_sts3215
make web-8898-start       # http://localhost:8898/rl
make web-8898-status
make web-8898-restart
make web-8898-stop
```

This starts a Mac-side `launchctl` job via `uv run python -m
rl_move.sim.web_server`; it is not the Uno Q's `hexapod-web.service`
(`:8080`). The launcher is
`hexapod_walker/prototype_sts3215/sim_viewer/hexapod_web_8898.sh`.
It resolves the robot's current IP unless `HEXAPOD_HOST` is set.

### MuJoCo robot simulation and policy videos

For the native MuJoCo viewer, interactive policy playback, or a video of a
recent walking policy, read
`hexapod_walker/prototype_sts3215/AGENTS.md` (section "MuJoCo robot
simulation") and `hexapod_walker/prototype_sts3215/sim_viewer/README.md`.
The canonical foreground MuJoCo + web UI command is
`hexapod_walker/prototype_sts3215/sim_viewer/sim_web.sh`; use the documented
`rl_move/orchestrator/ops.sh drivevideo` wrapper for checkpoint videos so the
run's actual configuration and full-mesh model are preserved.
