# standwalk — mesh-model stance retrain, then distill into walking

Update, 2026-09-04 ~07:0x (**SELECTIVE per-leg omega boost — the
untried candidate the prior cycle named — built, validated
zero-training, and now spending its first RL canary (2-dose x
2-seed, 4 runs, all VERIFIED RUNNING).**)

Unlike every REFUTED candidate on the "reshape the commanded yaw
ANGLE" axis (uniform `combined_yaw_arm_scale`, selective
`combined_yaw_amplify_scale`, the unwired "detangle" idea — archived
below), this lever changes the TRUE foot target: on a combined tick,
only the 3 legs the vx cross term ATTENUATES below their own
pure-omega magnitude get their foot displacement (dx/dy/dz, hip+knee
included) recomputed with a boosted omega — mirroring the
already-tried UNIFORM `train.bc_anchor_teacher_omega_boost` but
restricted to the legs that actually lose authority. New
`TripodGait.combined_selective_omega_boost` +
`probe_turn_authority.py --scripted-selective-omega-boost` +
`train.bc_anchor_teacher_selective_omega_boost` BC-anchor wiring (13
new tests, 149/149 green overall). Zero-training scripted-teacher
validation (real MuJoCo physics, not the kinematic replay): dose
3.0-4.0 raises combined wz_med from ~0.081/-0.077 to
0.20-0.24/-0.20-0.24 rad/s — BOTH signs, sign-SYMMETRIC (unlike every
prior lever) — with pure-turn/pure-walk BIT-EXACT untouched; beats
the uniform lever's own best dose on real wz (0.231 vs 0.168 rad/s).
Launched `cap29-stdwalklohi-selomegaboost{3p0,4p0}{,-s1}` (2M-step
canaries, respec off the `yawarm1p5{,-s1}` ancestor, that lever reset
to identity) against the same `cap29-stdwalklo-hi{,-s1}` control used
throughout — VERIFIED RUNNING train-1/2/3/4. Pre-committed decision
rule: sign-asymmetric pure-turn regression like every prior lever
closes the geometry/teacher-lever axis for good; clearing it makes
this the first candidate that is genuinely different in kind (real
torque, not commanded-angle reshape).

Prior banner (per-leg instrumentation + 2 REFUTED candidates closing
the angle-reshape axis) moved VERBATIM to `archive/standwalk_
STATUS_journal_2026-09-04aa_trim.md`.
