# rl_only lower-role RAIL_MOVING per-joint breakdown (2026-10-02, idle-kick
# refill cycle, zero GPU spend -- pure re-analysis of already-collected
# artifacts, no new eval)

## Why
`todaypolicy`/`walkcurr` STATUS (Next item 1, 2026-10-02) closed the
genuine-stall half of the lower-role composed over_current gap (the
L1-hip dead-zone mechanism, fixed via the now-adopted
`safety.hip_pitch_max_deg` SafetyLayer default) and named the
remainder "a policy control-quality lever ONLY ... No mechanism for
that narrower framing is designed yet." Before guessing a new reward
term, this item re-reads the RAIL_MOVING population (the 32/37 traces
the 2026-10-01 `lowerrole_overcurrent_stallclass_2026-10-01` doc found
"high modeled load, NOT corroborated as unsafe") per-JOINT, to check
whether the remaining over_current terminations are spread evenly
across the 18 actuated joints (an undifferentiated control-quality
problem, no single lever would target it) or concentrated (a named
joint worth a targeted price). Reuses the exact trace JSONs already on
disk (`lowerrole_overcurrent_stallclass_2026-10-01/current_trace_*/
*_over_current.json`, `trip_summary.final_joint` + `.stall_
classification` fields) -- no new capture, no new eval, no GPU.

## Result
37 traces total, 32 RAIL_MOVING / 5 CORROBORATED_STALL (matches the
stallclass doc). Per-joint breakdown of the 32 RAIL_MOVING traces
(`SIM_JOINT_NAMES` index -> name, `hexapod_core.joint_frame`):

| joint index | name | RAIL_MOVING count | share |
|---|---|---|---|
| 16 | L5_pitch (hip) | 15 | 47% |
| 7 | L2_pitch (hip) | 7 | 22% |
| 8 | L2_knee | 6 | 19% |
| 2 | L0_knee | 3 | 9% |
| 17 | L5_knee | 1 | 3% |

L5 hip alone accounts for just under half of every RAIL_MOVING
termination, consistent with the stallclass doc's own raw-count read
("L5 hip's share (15/37 raw) is RAIL_MOVING ... the rearmost leg's hip
still working hard late in a real descent"). This is a genuinely
CONCENTRATED signature, not an undifferentiated 18-joint spread --
L5 hip + L2 hip/knee together cover 28/32 (88%).

## What this does and does not change
Does NOT reopen the already-CLOSED per-joint/per-magnitude levers:
`k_current_hot` (already active in this recipe, 1.0/2.0A, does not
stop these trips) and `k_torque_headroom` (doses 3/10/30, SEED-PRUNED
-- training stagnated outright, not just a weak gate) are both
magnitude/duration prices on a SINGLE actuator's own current reading,
already tried and refuted on this exact lineage. The system-ID doc
(`lowerrole_overcurrent_systemid_2026-10-01`) already confirmed the
scripted open-loop baseline is near-perfectly LOAD-SYMMETRIC across
all six legs at every trained depth (hips 0.575-0.579A, <0.003A
spread) -- so L5's concentrated share is a POLICY-CHOSEN weight
distribution, not a geometric/mass-distribution fact about the
rearmost leg.

## Candidate lever (not yet tried on this lineage): `reward.k_load_even`
Structurally different shape from both closed levers: prices the
Herfindahl index of FOOT NORMAL FORCES across all (non-unload) legs
each tick (`balance_reward_posture.py`, dense/mode-independent,
default OFF) -- i.e. it taxes WHICHEVER leg currently carries a
disproportionate share of body weight, not any single joint's current
level or dwell time. This targets the load-CONCENTRATION shape this
doc just found directly, without re-taxing instantaneous/sustained
current (the axis `k_torque_headroom` already showed breaks training
on this recipe). `k_load_even` WAS already tried and closed, but only
on a DIFFERENT role/failure shape (standwalk's isometric flat-start
RISE stall-fight, dose bracket 2/8/16/32, "closed short of a clean
PASS") -- the exact same new-role/new-failure-shape argument that
licensed re-trying `k_torque_headroom` here (which it did, independent
of this term, per `lowerrole_overcurrent_stallclass_2026-10-01`'s own
hypothesis text) applies again: a roaming mid-descent load-
redistribution question is not pre-closed by a flat-start isometric
one. Already built + tested, zero code change needed. Queuing a 3-dose
canary bracket (s0 only, from-scratch, matching the exact `torquehr`
precedent's no-warm-start/single-seed-first convention) --
see walkcurr/STATUS.md Next.

Evidence: re-derived from `lowerrole_overcurrent_stallclass_2026-10-01/
current_trace_{s0,s1}_seed{0,100}/*_over_current.json`
(`trip_summary.final_joint`/`.stall_classification` fields), joint
index -> name via `hexapod_core.joint_frame.SIM_JOINT_NAMES`.
