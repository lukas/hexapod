# standwalk STATUS journal archive — 2026-09-03c (trimmed from top of STATUS.md)

Update, 2026-09-03 ~03:3x (idle-kick, item 0 STILL mid-flight on
train-6/7, dr0 done both seeds, own-dr ~57% by video count, pace
unchanged): fixed two more semantics-bank reds found on a fresh
post-fix full-suite pass. (1) `test_rise_rock_feedback_levels_it`
was tripping `over_current` at only 3.2-5.7deg tilt (nowhere near its
9deg bound) -- confirming evidence for the pending `safety.
max_current_a` 2.5->2.9A cap raise (same intrinsic curl-current issue
item 0 is validating), fixed by scoping the 2.9A override to this
test's own `ROCK_OVERRIDES` only. (2) Half the recover-bank
q0/qpos-frame class the last entry's audit deferred ("distance
metric, not an action target"): `env.data.qpos` (mujoco_rel) minus
`env._plant_deg` (robot_abs, confirmed via its `q_rad_to_action` use
elsewhere) mixed frames, adding a ~0.6 rad bias that made B0-B4
difficulty bins read as flat noise; `_q0_robot_abs`-wrapping fixed
`test_recover_near_goal_buckets_increase_settled_disturbance` clean
and recalibrated one margin (0.2->0.1 rad) in `test_recover_floor_
rungs_remain_distinct_after_physics_settle`. That second test STAYS
red on a separate, unrelated, isolated bug (tangle_60->70 pad_spread
genuinely DECREASES, 39.10->38.48mm, provably not qpos-related --
flagged for a settle-physics dig-in, no tangle arm queued). Test-only,
no training-default cfg touched. Snapshotted+pushed. Full derivation:
OPERATOR_QUESTIONS.md.

Earlier updates (the 02:0x-03:1x q0/qpos-frame 14-site fix + 2
hold-bank recalibrations + the getup-bank honest-ordering red, and
the 01:5x joint-frame-v2 bug #3) moved VERBATIM to
`archive/standwalk_STATUS_journal_2026-09-03b_trim.md` and
`archive/standwalk_STATUS_journal_2026-09-03a_trim.md`.
