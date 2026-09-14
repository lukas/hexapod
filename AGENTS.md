# Agent conventions — hexapod

This file is short on purpose. It holds invariants. Anything longer lives
next to the code it describes, and incidents live in the commit that fixed
them.

## Subtract first (Lukas, 2026-09-14)

Agents kept adding to this repo and never removed anything. A MuJoCo-vs-robot
joint convention bug and several firmware timing bugs hid for weeks under the
accumulation. So:

- Every change names what it retires in its commit message. A change that
  only adds needs a stated reason.
- Contracts live in code with a test, never in prose. Joint order, names and
  servo IDs: `hexapod_core/joint_frame.py`. Bus protocol:
  `linux_control/mcu_feetech_bus.py`. Import the contract; do not add a second
  copy, alias or mapping table.
- No silent fallbacks. When firmware, config or a dependency is not what the
  code expects, fail with the fix in the message. Never degrade quietly to an
  older or slower path.
- Do not add to this file, `RESEARCH_RULES.md` or `.cursor/rules` because of
  an incident. Put the lesson in the fix.
- Nothing generated goes in git: logs, artifacts, media, ledgers, run stories.
  Orchestrator state is the plain directory `<checkout>/.state`, mirrored to the
  `hexapod-state` PVC by `state_sync.sh` (`rl_move/orchestrator/state_dir.py`).

## Goals

`hexapod_walker/prototype_sts3215/RL_GOALS.md` is canonical (Lukas,
2026-09-08 and 2026-09-13). Two goals run in parallel: `any_means`, smooth
joystick walking on the physical robot by any effective method now; and
`rl_only`, the same outcome with every motion-producing role learned entirely
through RL and no demonstrations anywhere in its lineage. Each needs an
interactive sim demo, a video and a reproducible launch. Report sim and
hardware readiness separately; a sim or method pass never establishes
physical completion.

## Where things run (merging to main deploys)

- `main` is pulled automatically by the CoreWeave controller pod, the Uno Q
  robots (`linux_control/deploy_manifest.sh` staged tree) and the Mac hub
  worktree `~/hexapod-hub`. Merge to `main` only when you would deploy.
- Orchestrator code commits go to the `orchestrator` branch
  (`rl_move/orchestrator/snapshot.sh`), which merges `main` into itself. A
  human merges `orchestrator` into `main` when its code is wanted there.
- RL status: `https://hexapod.cwd1f0-new-cluster.coreweave.app/now` (token
  on first visit) and `/llms.txt`. Local fallback:
  `kubectl --kubeconfig=$HOME/.kube/coreweave.yaml port-forward hexapod-sweep-friction 8090:8090`.
  Prefer the RL MCP tools; the JSON-RPC fallback is in
  `rl_move/orchestrator/README.md`. These reads are standing-authorized.
- Mac web hub: `make -C hexapod_walker/prototype_sts3215 web-8898-start`
  (`status`, `restart`, `stop`) serves `http://localhost:8898/rl`. This is not
  the robot's `:8080` service.
- MuJoCo viewer and policy videos: `hexapod_walker/prototype_sts3215/sim_viewer/README.md`
  and `rl_move/orchestrator/ops.sh drivevideo <run>`.
- BuildViz: `hexapod_walker/prototype_sts3215/docs/BUILDVIZ.md`. One hub on
  `:5183`; `:5173` is BuildViz's own dev server, leave it alone.
- Metaagent reviews and budgets: `rl_move/overseer/README.md`.

## Working rules

- Worktrees: each agent works in its own git worktree on its own branch and
  commits its own finished work there (`git add <paths>`, never `-A`). Never
  push to or merge `main`; Lukas merges. Details:
  `.cursor/rules/agent-worktrees.mdc`.
- Python: `uv run ...` in the one venv per checkout (`uv sync`). Add
  dependencies in `pyproject.toml` and `uv lock`; no ad hoc `uv pip install`.
  macOS MuJoCo GUI launches use `uv run mjpython`. The Uno Q runs
  `/home/arduino/.local/bin/uv run python ...`.
- Tests: `make -C hexapod_walker/prototype_sts3215 test-fast` is the default
  loop, `make ... test` the whole suite. Rules in `RESEARCH_RULES.md`
  "Tests": under 5 s, mechanics only, `monkeypatch.setenv` for the model
  family, no generated artifacts, one home per test, `main` stays green. The
  retired rollout bank `test_task_semantics.py` must not come back.
- Git reachability: check with `git ls-remote`, not `git branch -r
  --contains`; `tools/git_unpushed_audit.sh` finds and pushes unreachable
  work (some checkouts under `~/Library/Application Support/Hexapod Lab` have
  a narrow fetch refspec).

## Standing authorization (Lukas)

- Routine MCP calls and git commands needed for the active task: status,
  reports, logs, fetch, branch and worktree setup, staging, commits, conflict
  resolution, and pushes that deliver requested work. Pass this to delegated
  agents. Do not re-ask because a tool uses MCP, the network or git metadata.
  `.codex/config.toml` holds the approval defaults.
- Bounded robot experiments, necessary deployment (including firmware) and
  routine recovery within an active robot task, in the known test area, with
  a live camera and an abort path. A live camera plus three fresh healthy
  telemetry samples counts as supervision. Ask for hands-on help only when
  those are unavailable, inconclusive, or show a persistent condition.
- Do not modify firmware `.ino` files or CAD geometry as a side effect of an
  unrelated task.

## Hardware safety (`prototype_sts3215`), non-negotiable

`hexapod_walker/prototype_sts3215/EMERGENCY_HANDLING.md` is canonical for
hold versus controlled stop versus limp. Detail:
`.cursor/rules/hexapod-sts-hardware-safety.mdc`.

1. Control over HTTP (`:8080` `/api/*`, `/cmd`); SSH only for deploy and
   recovery. Dev loop: `make -C hexapod_walker/prototype_sts3215 robot-check`,
   `robot-unit-check`, `robot-status`, `robot-deploy`.
2. Set zero here before any absolute pose. If encoders disagree with the
   picture, remap zero; never command software 0°, stand or plant. Hip 0 with
   knee 80 is stilts, not a low plant.
3. Basic controls before loaded motion: live IDs, zeros, single-joint air
   moves, predict versus encoder agreement. Blends run from a verified pose,
   observed live.
4. The three rule: no guard fires on one sample; three consecutive fresh
   confirming samples make a fault. Stop on a confirmed tip, brownout, hot
   motor, jam, surprise force or persistent missing ID, then run the 30 s
   assessment and retry from a verified safe pose. Three attempts per step.
   Only an operator E-stop, or a fault still present after three attempts,
   waits on a human.
5. Preflight is one health read inside a 10 s budget
   (`sysid/run_hw.py`, `PREFLIGHT_BUDGET_S`). Protection during a run comes
   from the in-loop trips. Do not add pre-run audits, hash checks, rituals or
   camera checks before motion. Planning takes two minutes with a five minute
   hard wall.
