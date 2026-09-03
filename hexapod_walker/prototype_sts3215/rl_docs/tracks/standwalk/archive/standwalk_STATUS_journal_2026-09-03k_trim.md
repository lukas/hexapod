# standwalk STATUS journal archive — 2026-09-03k

Moved verbatim from STATUS.md top when superseded by the
2026-09-03 ~15:2x rollout-trace-tool Update.

Update, 2026-09-03 ~15:0x (idle-kick, spec-first work on Next item 2):
**built + ran BOTH semantics-bank twins the item asked for
(`rl_move/tests/test_task_semantics.py`, `test_steer_while_walking_
beats_going_straight` / `test_steer_income_is_monotone_in_tracking_
accuracy` / `test_rise_stall_draws_more_current_and_less_height_than_
partial` / `test_rise_stall_prices_worse_than_honest_partial`) — ALL
FOUR PASS, under the yawdensity family's OWN reward.* cfg-set (course/
kernel/yaw stack for steer, mesh/100Hz rise stack + current_hot for
rise-stall).** This is a genuine, if unglamorous, finding: neither of
the two most obvious "reward literally prefers the bad behavior"
hypotheses holds. (1) STEER: forcing a simultaneous body-frame
(vx=0.08, wz=0.25) command and scripting a twin that tracks BOTH vs
one that tracks vx only and ignores wz, the tracking twin wins by
~230-300/ep on every seed, and income is MONOTONE increasing in
tracking-fraction all the way through 1.3x overshoot (no local
optimum short of full accuracy) — the course/yaw pricing terms, taken
in isolation on a scripted twin from a common start, do NOT reward
going straight over steering. (2) RISE-STALL: a hand-built "reach
honest partial height then keep fighting for +40deg more knee than
the actuator can hold" twin DOES sustain current near the family's
own ceiling (2.62A) and DOES end up lower than the honest partial
(69mm vs 121mm) — but it earns 1/3 the honest partial's return
(514-517 vs 1669-1720/ep, seeds 0-2), driven mostly by the rise_ref
tracking term collapsing once the target diverges, plus a smaller
current_hot charge. **Read this as narrowing, not closing, the
redesign**: it rules out the plain "the reward is upside-down"
explanation for both symptoms, which means the real driver is more
likely (a) the concurrent BC-anchor imitation supervision (trained
toward a straight-walking teacher) fighting the RL steering gradient,
or (b) a within-episode PPO exploration/credit-assignment gap once a
rollout is already deep into a bad rise state, or (c) a genuinely
different failure SHAPE than either scripted twin captures (no real
qpos/action trace survived the original dig-in to check against —
only aggregate metrics in `logs/ckpt_eval/yawdensity_s1_riseAB_
cap29cf/report.json`). Full bank + caveats in the test file itself
(STEER/rise-stall sections, bottom of the file). **Recommended next
step, not yet started**: before building a reward-code arm, either
(i) dump a real qpos/action trace from a fresh stalling rollout and
rebuild the rise-stall twin as a faithful replay, or (ii) run a
zero-training bc_anchor_walk_coef ablation specifically on the
steering-while-walking-forward axis (the existing anchor-coef
ablations were scoped to turn-in-place ticks only, per
`train.bc_anchor_walk_turn_skip`, never to combined walk+turn ticks).
**Unrelated pre-existing regression found while broad-testing this
change (NOT caused by it, confirmed via `git stash` on the identical
2 tests): `test_score_honest_ordering` / `test_score_flagleg_earns_
scraps` (the RISE stand-score bank, SCORE_OVERRIDES) both FAIL on
`main` as of this cycle — flagleg (151.7) now out-earns partial
(103.2). Likely fallout of today's joint-frame-v2 `_q0_robot_abs`
fixes elsewhere in this file (the RAW_PLANT/WALK_PLANT comments
document three such fixes already today) touching the shared
`_rise_rollout`/RISE_REF machinery this bank also uses. Not fixed
here (out of scope for this item, and other concurrent cycles are
already working that exact bug family) — flagging so it isn't
mistaken for fallout of the new steer/rise-stall banks.**

Earlier updates (14:2x seed1 dig-in resolution, 13:3x seed0 verdict,
13:2x initial flagged dig-in, and everything before) moved VERBATIM
to `archive/standwalk_STATUS_journal_2026-09-03j_trim.md` +
`2026-09-03{a..i}_trim.md` + `2026-09-02{f,h}_trim.md`.
