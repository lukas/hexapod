# cw-standwalk-stage2-dualbc5-turncap-entboost-turnpay-canary

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: RUNNING

**created**: 2026-08-31T06:13:30+00:00

**pod**: hexapod-mjx-train-0

**steps**: 2000000

**parent**: cw-standwalk-stage2-dualbc5-turncap-turnpay-canary

**wandb_id**: vyca9ptd

**hypothesis**: Plain English: the anchor mechanism (dose AND turn-tick-targeted gating) is now exonerated across 4 independent tests -- the turn-authority erosion during RL is somewhere else. This tests the SECOND named next-suspect from the turnskip canary's own gate text: PPO exploration collapse. This lineage's log_std anneal is scoped to the stance core only (--log-std-anneal-core stance), so the walk core's action std is NOT forced down by that explicit schedule, but PPO's own natural entropy decay could still be starving exploration on the minority turn-in-place ticks before the yaw reward's gradient can find the turning behavior. A 4x ent-coef bump (0.005->0.02) on this otherwise-identical turnpay-canary base (same dualbc5_turncap init-from checkpoint, same bank-proven OMNI turn reward stack, same bc_anchor_coef=3.0/isolate_update=1) tests whether more exploration alone restores any turn signal.

**gate**: MECHANISM-HEALTH CANARY ONLY: do not judge skill acquisition, close a behavior/reward class, or require mature gait at this checkpoint. MECHANISM-HEALTH CANARY ONLY: do not judge skill acquisition or require mature gait at this checkpoint. PASS/promising if probe_turn_authority (own cfg minus goal.mode_seq, wz_cmd=+-0.25, walk-mode-filtered, seeds 0/1) wz_med clears meaningfully above the exonerated band (~-0.03..+0.005 across anchor-coef doses AND turn-skip) both signs AND det walk gait_valid stays >=5/6 (rules out 'more exploration traded for gait collapse'). FAIL if wz_med stays <0.03 both signs (exploration dose exonerated too at this level -- next suspect is a structural reward-stack interaction, e.g. the yaw kernel gate itself never firing on this diet, needs a dig-in on the raw per-tick reward components not another training-mechanism knob) or gait_valid craters (higher entropy destabilized the walk core generally, not turn-specific).

