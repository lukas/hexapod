# cw-walkscratch-easy0905-headset-crossgrav-medhead-dr-allaxis-nokick-crutchoff-s1-widen8-acq1-legdutyratiofresh

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: CANARY FAIL - INFRASTRUCTURE

**created**: 2026-09-08T00:16:54+00:00

**pod**: hexapod-mjx-train-0

**steps**: 2000000

**parent**: cw-walkscratch-easy0905-headset-crossgrav-medhead-dr-allaxis-nokick-crutchoff-s1-widen8-acq1

**wandb_id**: xvrxw7t3

**hypothesis**: PLAIN ENGLISH: 2nd-seed replication of the same new additive per-leg duty-balance reward charge tested on s0-widen8-acq1-legdutyratiofresh this same cycle (see that run's own hypothesis for the full design/bank-proof rationale) -- fresh provenance, seed 1, same 8-way heading recipe, charge present from step 0. PREDICTION IF TRUE: matches s0's recovery (previously-chronic leg's duty rejoins the team, gait_valid materially improves). PREDICTION IF FALSE: matches s0's persistence (same front-pair sacrifice regardless). Needed because every prior mechanism in this campaign required >=2 seeds before a verdict (single-seed reads were repeatedly reopened as noise).

**gate**: MECHANISM-HEALTH CANARY ONLY: do not judge skill acquisition, close a behavior/reward class, or require mature gait at this checkpoint. Same gate as s0-widen8-acq1-legdutyratiofresh: PASS if the chronic leg's duty recovers (peer-relative ratio >=0.22 majority of episodes) and gait_valid >=18/24 with 0 new falls; CONTINUE if reward+gait_valid both trending up but short; FAIL if the same sacrifice persists regardless.

**verdict**: CANARY FAIL - INFRASTRUCTURE: not a mechanism result, INVALID. The launched cfg (walk_leg_duty_ratio_charge=150) trained under a bug: the new code's contact-bookkeeping block was never added to the shared activation guard (sim_env.py's g_gait/g_duty/g_swing/g_dband/k_drag/k_park/... condition list), so on this recipe (k_park_duty=0, k_step_event=0, no other gate armed) the EMA update never ran -- the charge was silently INERT the whole run, bit-identical to charge=0. Bug found+fixed by the operator (commit ebad6d0d, 'Activate standalone leg-duty ratio reward contact tracking', +1 new regression test). Superseded by cw-walkscratch-easy0905-headset-crossgrav-medhead-dr-allaxis-nokick-crutchoff-s1-widen8-acq1-legdutyratiofresh-guardfix1 (same recipe, fixed code, confirmed non-zero charge in its own wandb_history.csv).

