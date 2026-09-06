# RL watchdog observations — 6 September 2026

These six timestamped records preserve observations and actions from the local
fleet watchdog. They are historical snapshots, not live fleet status. Use the
authenticated orchestrator tools for current runs, capacity, and outcomes.

The latest record, `state_20260906T050630Z.json`, corrects the budget interpretation
in `state_20260906T045400Z.json`: the original 8M-step allocation for each walking
arm was an initial experiment plan, not a permanent user-imposed limit. The
watchdog mistakenly stopped the turns continuation. Its checkpoint and KILLED
ledger were preserved, the instructions were corrected, and one recovery was
queued for the remaining 3,871,232 steps of that same additional 8M. At the last
recorded check, its launcher was waiting for the shared launch lock; the record
does not claim verified resumed training or a passing walking policy.

The records also distinguish active optimization from CPU evaluation/video work
that retains GPU memory. Early GPU release was demonstrated, but the latest
review still required fixes to publication recovery and runtime provenance
before broader unattended use of the deferred artifact option.

The recurring task's current instructions are recorded in
[WATCHDOG.md](../../hexapod_walker/prototype_sts3215/rl_move/orchestrator/WATCHDOG.md).
These files contain no authentication configuration or downloaded videos.
