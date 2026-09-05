# cw-walkscratch-easy0905-headset-base-irr-dgate2-c1

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: RUNNING

**created**: 2026-09-05T17:37:28+00:00

**pod**: hexapod-mjx-train-4

**steps**: 2000000

**parent**: cw-walkscratch-easy0905-headset-base-irr-acq1

**wandb_id**: 9r38bzqi

**hypothesis**: headset-base-irr-acq1 ACQ FAIL (misaligned): walk/det gait_valid only 3/6 with a marginal leg (duty 0.04-0.07, real infrequent swings not near-zero LEGPARK-SKATE) plus uniformly elevated slip_per_m 3.86-4.76 -- the SAME family-wide marginal-underuse class as headset-base-s0c1-acq1, now specifically under the irr-timing (jittered heading-resample) composition, and this campaign's own STATUS note pre-registered walk_duty_gate as the repair candidate for this exact cell once the mechanism's fresh/entrenched reads resolved. They have resolved: bare walk_duty_gate at floor=0.15/dose=0.9 was CANARY FAIL - MECHANISM (INERT-DOSE) on the sibling s0c1 lineage (PPO's own rollout noise already satisfies the lenient floor). This canary applies the stronger, bank-proven floor=0.35/dose=1.0 (walkcurr-dutygate-strongfloor-bank-0905, 39/39 green, proven to leave a healthy tripod's income untouched while pricing a ~0.05-duty twin measurably harder) to the irr-timing lineage's own FAILED 40M checkpoint.

**gate**: MECHANISM-HEALTH CANARY ONLY: do not judge skill acquisition, close a behavior/reward class, or require mature gait at this checkpoint. MECHANISM-HEALTH CANARY (2M): env/walk_duty_min/env/walk_duty_gate_factor must show real movement (not pinned 1.0 the whole run); harness det-mode leg duty should climb measurably above the 0.04-0.07 baseline; slip_per_m should trend down from the 3.86-4.76 baseline, not up; no new falls. FAIL if duty/slip stay pinned at baseline (inert) or a different leg parks or falls appear. PASS licenses a 40M continuation to re-test the irr-timing/1g rung.

