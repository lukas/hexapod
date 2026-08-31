# cw-standwalk-stage2-dualbc6-turncap-mirroraug-turnpay-acq1-s1

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: RUNNING

**created**: 2026-08-31T15:49:29+00:00

**pod**: hexapod-mjx-train-3

**steps**: 38000000

**parent**: cw-standwalk-stage2-dualbc6-turncap-mirroraug-turnpay-canary-s1

**wandb_id**: r4wypksg

**hypothesis**: Plain English: seed-1 twin of cw-standwalk-stage2-dualbc6-turncap-mirroraug-turnpay-acq1 -- same question (does the mirror-augmented turn-authority base keep its turn authority and mature walk quality under a full acquisition budget, or does a slow erosion invisible at 2M show up over a longer horizon), replicated on the second seed whose own 2M RETENTION canary read wz_med +0.129/+0.123 and -0.146/-0.160 (essentially unchanged from its own pre-RL base +0.148/+0.148,-0.152/-0.158, i.e. near-zero erosion) with det walk gait_valid 24/24 (own gate pass, this cycle) and zero terminations. Prediction-if-true: at ~40M cumulative steps this seed also holds wz_med>=0.10 both signs, progress_ratio holds/improves, gait_valid>=5/6, and eval_joystick_gate direction-following materially improves vs the ~45-52deg non-turning-base baseline. Prediction-if-false: wz_med decays toward the <0.03 floor over the longer horizon on this seed too. Running both seeds as a matched pair (not a solo bet) lets a single-seed anomaly be told apart from a real class-level property of the mirror-augmented base.

**gate**: ACQUISITION (continuation of a passed RETENTION canary, phase acquisition, budget ~40M cumulative), seed-1 twin of the -acq1 arm -- SAME gate: PASS/promote-to-stage2-source if probe_turn_authority wz_med >= 0.10 both signs at the final checkpoint AND pure-walk det progress_ratio not regressed vs 0.40-0.48 AND det walk gait_valid >= 5/6 AND eval_joystick_gate direction_err_med materially improved vs the 45-52deg non-turning-base baseline with zero-or-near-zero falls and slip/m <=3.0. FAIL if wz_med decays back under 0.03 both signs by the final checkpoint despite clean gait/progress. PARTIAL/DIG-IN otherwise; read jointly with the -acq1 (seed0) twin the way the source canaries were.

