# cw-walkscratch-easy0905-headset-crossgrav-medhead-dr-allaxis-nokick-crutchoff-s0-widenbis180-legdutyratiofresh

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: CANARY FAIL - INFRASTRUCTURE

**created**: 2026-09-08T00:22:13+00:00

**pod**: hexapod-mjx-train-1

**steps**: 2000000

**parent**: cw-walkscratch-easy0905-headset-crossgrav-medhead-dr-allaxis-nokick-crutchoff-s0-widenbis180

**wandb_id**: tipif77i

**hypothesis**: PLAIN ENGLISH: same new additive per-leg duty-balance reward charge as s0-widen8-acq1-legdutyratiofresh (see that run's hypothesis for the full design/bank-proof), applied fresh-provenance to the MILDER widenbis180 lineage (6-way heading set, one added 180deg heading vs widen8's 3 added headings) instead of the severe widen8 case -- every prior mechanism in this campaign (legdutyterm1/legdutyfresh) was tested on both lineage severities in parallel. PREDICTION IF TRUE: recovers on the milder lineage at least (even if the severe widen8 case needs more budget), matching the pattern where milder pathologies are easier to fix. PREDICTION IF FALSE: same leg-0 sacrifice persists regardless of severity, reinforcing that this is one mechanism-shape question, not a severity-dependent one.

**gate**: MECHANISM-HEALTH CANARY ONLY: do not judge skill acquisition, close a behavior/reward class, or require mature gait at this checkpoint. PASS: previously-chronic leg-0's duty recovers (peer-relative ratio >=0.22 majority of episodes), gait_valid materially improves vs the undosed s0-widenbis180 baseline (>=18/24 pre-widen8 clean band), 0 new falls. CONTINUE (08-21): reward+gait_valid trending up but short. FAIL: leg-0 sacrifice persists at the same fingerprint regardless.

**verdict**: CANARY FAIL - INFRASTRUCTURE: not a mechanism result, INVALID. Same activation-guard bug as the widen8 siblings: the new walk_leg_duty_ratio_charge contact-bookkeeping block was never added to the shared activation guard (sim_env.py's g_gait/g_duty/g_swing/g_dband/k_drag/k_park/... condition list), so on this recipe (k_park_duty=0, k_step_event=0, no other gate armed) the EMA update never ran -- the charge was silently INERT the whole run, bit-identical to charge=0. Bug found+fixed by the operator (commit ebad6d0d, 'Activate standalone leg-duty ratio reward contact tracking', +1 new regression test). Superseded by cw-walkscratch-easy0905-headset-crossgrav-medhead-dr-allaxis-nokick-crutchoff-s0-widenbis180-legdutyratiofresh-guardfix1 (same recipe, fixed code, VERIFIED RUNNING).

