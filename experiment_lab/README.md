# experiment_lab

Robot Lab v2 lives in [`hexapod_lab2/`](hexapod_lab2/README.md): the loop
that keeps the hexapod running experiments, the builder/engineer that write
code for it, and the web service (dashboard, JSON API, artifacts, `/mcp`)
on `https://robot-lab.cwd1f0-new-cluster.coreweave.app`.

The original Robot Lab (`hexapod_lab/`, an authenticated experiment queue
with a codex orchestrator, blocker monitor and tag-scan tooling) was retired
on 2026-09-11. Its findings were imported into v2 as runs tagged
`[old-lab]`; see the v2 README for what was kept and where the old data
directory still sits.

    uv sync --extra dev
    .venv/bin/python -m pytest tests_lab2

## Run outcomes

`ok` and `failed` say whether the robot did what the protocol asked. They are
not a verdict on the experiment. A plan whose `intent` is `explore` (the
planner sets it when a run is there to look and learn) is recorded as
`explored` when it completes: no pass, no fail, and the planner's `learned`
paragraph is its result. Hand-run imports default to `explored` unless the
caller marks them `ok` or `failed`. Only `failed` counts toward the loop's
three strikes; `ok` and `explored` both reset them.
