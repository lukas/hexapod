# Lower-role over_current: why `hold_min_load_apply_lower` FAILED, and
# the better-targeted replacement (`lower_joint_limit_terminate_s`)

2026-10-01, zero GPU spend for the diagnosis (two already-queued
training arms consumed GPU and were mechanically SEED-PRUNED before
this analysis; the replacement mechanism below is newly queued this
same cycle).

## 1. The minloadlower-acq1 FAIL, explained

`cw-stance50hz-rlonly-lowerrole-scratch-sac-{s0,s1}-drramp-minloadlower-acq1`
(respec of the matched drramp-acq1 parents with
`safety.hold_min_load_apply_lower=1`) were both mechanically
SEED-PRUNED by `seed_pruner.py` at 5-5.8M/8M steps (reward EMA slope
-31/-39 per window, `ep_len` regressing). W&B reward-quarter curves:

| run | parent quarters | minloadlower quarters |
|---|---|---|
| s0 | [149, 366, 337, 262] | [-33, 70, **119**, **30**] |
| s1 | [96, 373, 379, 262] | [-29, 104, **120**, **34**] |

Both minloadlower arms peak around reward ~120 (vs parent ~340-380)
then COLLAPSE back to ~30 — not a flat/stalled learner, a genuine
regression after partial progress. `terminations/hold_min_load` fires
on nearly every sampled W&B row throughout training (not just at the
end), and `rollout/ep_rew_mean` never exceeds ~70 in the per-episode
samples, consistent with episodes being cut very early and often.

### Root cause (new CPU-only tool: `eval_lifecycle_handoff_rlonly.py
--minload-trace-dir`)

Replayed the UNMODIFIED parent checkpoints (s0, s1; no
`hold_min_load_apply_lower`) through the same lifecycle harness,
capturing the exact quantity the termination's EMA tracks
(`env._minload_min_force_now(floor_n)`, worst-over-six-feet
instantaneous touch force) at every tick, for ALL episodes (healthy
AND failed, 12 each seed).

**Result: the worst-over-feet EMA reads below the 0.3 N floor on
97-100% of ticks of EVERY episode, even at EMA smoothing tau up to
5 s, independent of whether the episode is `lower_ok` or not.**
Offline-replaying the production EMA+counter logic
(term_s=1.0, grace_s=1.0) against these traces shows the termination
would fire at t=1.98-2.16 s on **100% of the 12 sampled episodes**
(6 `lower_ok`, 6 failed) — i.e. it is not a rare edge-case
over-trigger, it is a near-universal one, explaining the training
collapse completely (every episode gets capped at ~2 s regardless of
policy quality once the key is on).

Per-leg inspection explains why: on a HEALTHY (`lower_ok=True`)
episode, legs 1/3/4 read **median force 0.0 N** (unloaded most of the
episode) while legs 2/5 carry the real load (median 13-16 N) — this
policy family's normal lower-mode descent is NOT "all six feet evenly
loaded at all times" (the hold role's own assumption); it relies on
sustained per-leg load asymmetry as part of ordinary operation. A
MIN-OVER-FEET instantaneous measure cannot tell "some leg is always
the momentary worst" (normal) from "the SAME leg is always the worst"
(the real pathology) — because at any given instant some leg reading
near-zero is simply normal for this gait.

A **per-leg-tracked EMA** variant (each leg's own continuity counter,
not a shared minimum) was also tried offline: it removes the
near-universal ~2 s firing, but on seed s1 it STILL false-fires on
most `lower_ok` episodes (joint 15 = leg5 hip reads near-zero force
for 2-4 s stretches even in healthy runs) — because s1's policy
routinely runs leg5's hip near-zero-load for extended but ultimately
harmless stretches while still visibly moving. This is exactly the
`RAIL_MOVING` pattern the existing stall-corroboration work (09-30)
already named and distinguished from `CORROBORATED_STALL` via a
QVEL-based staticity check, not a load/duty check.

**Conclusion: load magnitude (instantaneous OR per-leg-EMA, OR duty)
cannot discriminate a genuine stuck-leg stall from this policy
family's normal asymmetric gait. CLOSED, do not re-dose
`hold_min_load_apply_lower`'s floor/grace/tau at any value — the
defect is the signal, not the threshold.**

## 2. The correctly-targeted replacement:
`safety.lower_joint_limit_terminate_s`

The L1-hip root-cause work's OWN evidence was never "low load" — it
was "qpos pinned 0.037 rad past the hip's own 0.52 rad hinge limit
AND qvel effectively static" (hot_qvel_med_rad_s 0.0072-0.0116 rad/s
across the 4 real CORROBORATED_STALL trace JSONs already on disk).
That is exactly the conjunction
`eval_lifecycle_handoff_rlonly.trip_summary()` already computes
post-hoc to separate `CORROBORATED_STALL` (5/37) from `RAIL_MOVING`
(32/37) in the 09-30 forensics. This cycle turns that EXACT,
already-validated conjunction into a LIVE per-tick termination
(`lower_joint_limit_termination`, `balance_terminations.py`), tracked
PER JOINT (never a cross-leg minimum, unlike the closed mechanism):

```
safety.lower_joint_limit_terminate_s      (default 0.0 = off)
safety.lower_joint_limit_margin_rad       (default 0.05, matches
                                            trip_summary's own
                                            near_limit_margin_rad)
safety.lower_joint_limit_stall_qvel       (default 0.05 rad/s)
safety.lower_joint_limit_grace_s          (default 1.0 s)
```

Fires only in `mode=="lower"`, only once a SPECIFIC joint has been
BOTH within `margin_rad` of its own `model.jnt_range` AND
`|qvel| < stall_qvel`, continuously, for `terminate_s` seconds past
the segment-entry grace. New model-constant `env._joint_limit_rad`
(cached once at env init from `model.jnt_range`, never DR-mutated —
confirmed via grep, not a `SNAP_ATTRS` entry) and new per-episode
`env._lower_jlimit_low_s` (N_JOINTS,) counter (registered in
`mjx_host.SNAP_ATTRS`, zeroed at reset).

### Validation (zero GPU, offline replay against real + newly
captured traces)

- **True positives**: all 4 real `CORROBORATED_STALL` trace JSONs
  already on disk (`lowerrole_overcurrent_qpos_limit_2026-10-01/`,
  `lowerrole_overcurrent_stallclass_2026-10-01/`) satisfy BOTH halves
  of the conjunction over their hot window (near_joint_limit=True,
  hot_qvel_med_rad_s 0.0072-0.0116 << 0.05) — this termination would
  have caught all 4, and strictly earlier/safer than the actual
  over_current trip (the same episode's eventual failure mode).
- **False positives**: replaying the new live-termination logic
  (margin=0.05, stall_qvel=0.05, term_s=0.5, grace_s=1.0) against 12
  freshly captured per-tick qpos+qvel traces per seed (24 total, both
  `lower_ok` and failed) gives 2/12 false-fires on s1's healthy
  episodes, both within 1-4 s of the NATURAL 15 s episode end
  (t=10.9-14.4 s) — i.e. a materially smaller and far less damaging
  false-positive footprint than either load-based design's
  near-universal ~2 s firing. s0 has zero false-fires in its 12-episode
  sample.

Not a provably zero-false-positive design (12-episode-per-seed samples
are small, and the 2 late false-fires on s1 are real) — but a FAIL
this cheap to anticipate does not justify another from-scratch
training attempt without first trying the properly-targeted
mechanism. Queued (GPU, this cycle, not yet complete):
`cw-stance50hz-rlonly-lowerrole-scratch-sac-{s0,s1}-drramp-jointlimitlower-acq1`
(respec of the matched drramp-acq1 parents,
`--cfg safety.lower_joint_limit_terminate_s=0.5
--cfg safety.lower_joint_limit_grace_s=1.0`, same 8M-step/dr=0.2/SAC
budget). Gate: composed direct-arm `lower_ok` should beat the parent's
24/36 (s0) / 16/36 (s1) and `CORROBORATED_STALL` count should drop
below the parent's pooled 5/37, without a reward-EMA collapse pattern
like minloadlower's (if `lower_joint_limit` termination rate climbs
high enough to reproduce the same collapse, that would mean even the
per-joint conjunction over-triggers under TRAINING dynamics the
12-episode offline sample didn't sample — check the termination
histogram early, same as minloadlower's own gate text instructed).

## Tooling landed this cycle (tested, `ops.sh testdiff` clean,
2963 passed / 2 known failures)

- `eval_lifecycle_handoff_rlonly.py --minload-trace-dir`: per-tick
  min-over-feet force + per-leg force + qpos + qvel capture for EVERY
  lower-phase episode (not just failures, unlike `--current-trace-dir`)
  — lets any future load/limit-threshold idea be offline-replayed
  against real rollouts before spending GPU.
- `balance_terminations.lower_joint_limit_termination` +
  `safety.lower_joint_limit_terminate_s` family (4 new tests,
  `test_lower_joint_limit_termination.py`): default-off, bit-exact,
  LOWER-mode-only live termination reusing the trip_summary
  near-limit+qvel-static conjunction.
