Update, 2026-09-03 ~03:1x (idle-kick, item 0 still mid-flight on
train-6/7, dr0 phase done/own-dr running, pace unchanged): **landed
the q0/qpos-frame fix flagged last entry** -- 14 `test_task_
semantics.py` sites (rise/lower/hold x6/margin/getup/recover/2 RSI
one-shots) fed raw MuJoCo qpos (knee-rel-to-hip) straight into
`q_rad_to_action`/an IK solve expecting robot_abs, double-shifting
the knee; fixed via the existing `mujoco_rel_rad_to_robot_abs_rad()`.
Measured (quiet hold): drift 4.12mm->0.44mm, return 1444.9->1474.87.
Recalibrated 2 hold-bank threshold tests against fresh, correctly-
primitive-pinned measurements (`test_hold_gate_bites_the_stepping`
0.68->0.73; `test_hold_fade_park_is_scraps_not_a_living`'s hip-lift
constants 55->75deg/50->80deg). One NEW red left deliberately
unpapered: `test_getup_honest_ordering`'s partial>freeze rung now
fails on honest numbers -- flagged for a reward-side dig-in, no
getup-mode arm should launch first (none queued). Full ~110-test
slice re-verified otherwise clean. Test-only, no cfg touched.
Snapshotted+pushed. Full derivation: OPERATOR_QUESTIONS.md.
