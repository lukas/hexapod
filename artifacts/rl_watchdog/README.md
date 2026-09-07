# RL watchdog observations — 6–7 September 2026

These eleven timestamped records preserve observations and actions from the local
fleet watchdog. They are historical snapshots, not live fleet status. Use the
authenticated orchestrator tools for current runs, capacity, and outcomes.

The record `state_20260906T050630Z.json` corrects the budget interpretation
in `state_20260906T045400Z.json`: the original 8M-step allocation for each walking
arm was an initial experiment plan, not a permanent user-imposed limit. The
watchdog mistakenly stopped the turns continuation. Its checkpoint and KILLED
ledger were preserved, the instructions were corrected, and one recovery was
queued for the remaining 3,871,232 steps of that same additional 8M. The
record `state_20260906T063330Z.json` confirms the recovery completed. Its matched
assessment retained 24/24 valid gait episodes and zero falls, but failed steering
qualification: course error worsened from 8.55° to 10.2° and both turn directions
missed the yaw-error limit. The recorded next step is a reward alignment audit.

The records also distinguish active optimization from CPU evaluation/video work
that retains GPU memory. That same record verifies a complete deferred-artifact
handoff, publication of all three jobs, and reuse of the freed GPU by another
trainer. Routine adoption was then confirmed in the live arguments of a normal
queued continuation, which was advancing at 4.19M steps on the final check.

That record also documents recovery from a truncated experiment ledger.
All 2,466 keys from the last complete snapshot were present in the repaired main
branch. Later checks and any remaining qualifications are timestamped in the
record; these snapshots should not be used as a substitute for live status.

The three subsequent records cover resumed monitoring, two scratch acquisitions,
and a yaw-reference experiment after a bounded reward-frame audit. The latest
record, `state_20260907T060107Z.json`, was checked at 06:14:43 UTC on 7 September:
the yaw trainer had advanced to 3,096,576 steps, the scratch acquisitions had
finished optimization with artifact publication still pending, and the MJX reset
handoff was undergoing validation. These observations do not establish policy
qualification. Parent and Candidate B comparisons on the corrected course metric
remain requirements of the new experiment's gate, not verified results here.

Filenames identify the heartbeat trigger. Use each record's `checked_at_utc` and
embedded sample timestamps for observation time: the heartbeat triggered at
07:16 UTC on 6 September resumed on 7 September after an approval delay.

The recurring task's current instructions are recorded in
[WATCHDOG.md](../../hexapod_walker/prototype_sts3215/rl_move/orchestrator/WATCHDOG.md).
These files contain no authentication configuration or downloaded videos.
