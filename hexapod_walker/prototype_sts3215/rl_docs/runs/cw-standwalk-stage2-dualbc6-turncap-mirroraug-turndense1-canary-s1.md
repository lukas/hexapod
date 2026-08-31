# cw-standwalk-stage2-dualbc6-turncap-mirroraug-turndense1-canary-s1

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: FAIL

**created**: 2026-08-31T19:40:04+00:00

**pod**: hexapod-mjx-train-4

**steps**: 2000000

**parent**: cw-standwalk-stage2-dualbc6-turncap-mirroraug-turnpay-canary-s1

**wandb_id**: 2ra2xpoj

**hypothesis**: Seed-1 twin of cw-standwalk-stage2-dualbc6-turncap-mirroraug-turndense1-canary -- same single lever (goal.walk_turn_in_place_frac 0.30->0.60, 2x turn-segment density, unchanged reward weights) off the exact turnpay-canary-s1 recipe/init, testing whether the credit-assignment fix (if any) is seed-consistent like every prior mechanism-class canary pair in this campaign has been (wz within 0.01-0.03 between seeds every time).

**gate**: MECHANISM-HEALTH CANARY ONLY: do not judge skill acquisition, close a behavior/reward class, or require mature gait at this checkpoint. SAME gate as cw-standwalk-stage2-dualbc6-turncap-mirroraug-turndense1-canary (seed0): PASS if probe_yaw_credit forward_verdict is CREDIT-REWARDS (or corr_toward_value_delta>=+0.15) on >=3/4 of the wz_cmd=+-0.25 x seed-internal-probe combos on the 2M checkpoint AND probe_turn_authority wz_med>=0.10 both signs AND det walk gait_valid>=5/6 with clean progress. FAIL if forward_verdict stays BLIND/PUNISHES on >=3/4 of combos regardless of wz_med. PARTIAL otherwise; joint read with the seed0 twin.

**verdict**: CANARY FAIL - MECHANISM, JOINT CLOSE 2/2 (density lever refuted both seeds). Plain English: giving the critic more turn practice does not teach it to value turning, on this seed either -- the joint turndense1 pair is now closed and the density hypothesis is dead. Ran the gate's own named instruments myself (checkpoint pushed to a free pod, train-5, exact 96-key training cfg-set from seed0's own probe run replayed verbatim -- same lineage/recipe, same cfg). probe_yaw_credit forward-only value_delta verdict is BLIND/PUNISHES on ALL 4/4 combos (wz_cmd=+-0.25 x seed-internal-probe 0/1): wz+0.25 seed0/1 = CREDIT-BLIND (corr_toward_value_delta -0.088/-0.044), wz-0.25 seed0/1 = CREDIT-PUNISHES (-0.201/-0.278) -- 0/4 CREDIT-REWARDS, none clearing the +0.15 PASS bar. Per the gate's own text this decides FAIL regardless of turn authority ('FAIL if forward_verdict stays BLIND/PUNISHES on >=3/4 of combos ... regardless of wz_med'). probe_turn_authority wz_med is actually fine at this early 2M checkpoint (+0.116/+0.110, -0.140/-0.128, clears >=0.10 both signs) -- matches seed0's own +0.127/+0.117,-0.161/-0.136 within noise, expected since 2M is too early for erosion, but the gate explicitly does not let this rescue clause 1. Pulled the walk_det_0 frame strip myself off the still-finishing standard gate harness (train-4, informational): clean six-leg gait, robot upright, no fall, no gait-collapse confound -- this is a genuine credit-assignment reject on both seeds, not a farmed side effect. JOINT CONCLUSION (both seed0 FAIL + seed1 FAIL, identical 4/4-BLIND/PUNISHES signature, wz_med within 0.02 of each other both signs): 2x turn-in-place exposure does NOT fix the critic's credit-assignment blindness identified by the 09:4x/19:4x finding -- this is not a data-density problem. Per the gate's own escalation path the next lever is an explicit critic-side feature or a dedicated value-warmup phase (architecture-side, genuine new-code work). NOT started this cycle: the parallel stillbal-acq1{,-s1} pricing-symmetry retention pair (k_yaw_still 50->5, same erosion phenomenon from a different angle) is still training (train-0 ~26M/38M, train-1 ~10M/38M) and was explicitly pre-registered as the decisive fork this exact architecture escalation is deferred behind -- that reasoning still holds: rushing the critic build now would pre-empt a cheaper pending answer. No other track has legal runnable GPU work (joystick/amp/cpg DONE-or-maintenance, todaypolicy delivered, walkcurr RETIRED, re-confirmed fresh). 10/12 GPU pods free but nothing legal to launch ahead of the stillbal fork's own result -- did not launch a new arm. Next cycle: once stillbal-acq1{,-s1} finish/close, decide whether to start the critic-side/value-warmup build (now unconditionally, since BOTH the density lever (this pair) and -- pending its own result -- the pricing-symmetry lever will be closed).

