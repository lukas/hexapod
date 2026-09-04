# standwalk — mesh-model stance retrain, then distill into walking

Update, 2026-09-04 ~07:2x (**selomegaboost dose3.0/seed0 arm reports:
CANARY FAIL - MECHANISM, 1st of the 4-arm grid to close, same
sign-asymmetric-pure-turn-erosion pattern as every prior teacher-lever
candidate despite this one's clean zero-training validation.**)

`probe_turn_authority.py` on the finished `cw-standwalk-stage2-
dualbc6-turncap-mirroraug-yawcredit-gradclip0p15-cap29-stdwalklohi-
selomegaboost3p0` checkpoint (full 84-key non-train cfg-set replayed,
2 probe seeds averaged) vs the matched `cap29-stdwalklo-hi` seed0
control: pure-turn wz_med +0.166/-0.215 vs control +0.223/-0.250 (25.5%/
14.0% regression, BOTH signs breach the pre-registered 10% cap);
combined-tick (vx=0.08) wz_med +0.084/-0.181 vs control +0.110/-0.170
— positive sign is WORSE, failing the "beats control on both signs"
bar outright regardless of the negative-sign gain. Training reward
genuinely healthy (rising monotonically to 290 at the final step, no
flat tail) so this is the mechanism failing, not a starved run. Same
failure signature as every predecessor on this axis (uniform
omega_boost, yaw_arm_scale, combined-dose ablations, yawboost) —
RL fine-tuning erodes pure-turn even when the teacher-side lever is
bit-exact-by-construction on pure-turn ticks. 3 sibling arms
(selomegaboost4p0, -4p0-s1, -3p0-s1) still finishing/awaiting their
own triage — full axis-close verdict needs all 4; see Next item 2.

Prior banner (candidate build + all-4-launched note) moved to
`archive/standwalk_STATUS_journal_2026-09-04bb_trim.md`.
