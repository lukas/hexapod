# cw-walkscratch-easy0905-headset-base-s0c1-dgnoise-c1

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: RUNNING

**created**: 2026-09-05T19:25:35+00:00

**pod**: hexapod-mjx-train-1

**steps**: 2000000

**parent**: cw-walkscratch-easy0905-headset-base-s0c1-dgfresh

**wandb_id**: 6b1c6hy4

**hypothesis**: Root-cause-driven follow-up to headset-base-s0c1-dgfresh's CANARY FAIL - MECHANISM (this cycle): that run showed env/walk_duty_gate_factor genuinely declining 1.0->0.63 (real training-time pricing) yet leg-4 duty in the deterministic policy stayed statistically unchanged from the undosed twin -- because policy_std already sits at its schedule floor (0.135 rad, --log-std-final=-2.0) by 2M, so the duty-gate reward is satisfied by noise-driven duty upticks during noisy rollout collection that never have to move the policy MEAN. This canary changes exactly ONE variable vs dgfresh: --log-std-final -2.0 -> -1.2 (residual stddev 0.135->0.301 rad, more than double), keeping substantial exploration noise alive through the whole 2M budget so duty-seeking trajectories the noise discovers have a real chance to get reinforced into the mean via the policy gradient, instead of just satisfying a training-time metric in passing. Everything else (seed=0, --init-from base_s0_c1.zip, walk_duty_gate=1.0/duty_gate_floor=0.35/duty_gate_window_s=3.0) is identical to dgfresh.

**gate**: MECHANISM-HEALTH CANARY ONLY: do not judge skill acquisition, close a behavior/reward class, or require mature gait at this checkpoint. MECHANISM-HEALTH CANARY ONLY: do not judge skill acquisition or require mature gait at this checkpoint. PASS if walk_startjitter/det leg-4 duty is measurably higher than BOTH the undosed s0c1 twin's report AND dgfresh's own report (logs/ckpt_eval/cw_walkscratch_easy0905_headset_base_s0c1_dgfresh_gate/report.json: duty 0.02-0.07, gait_valid 0/6) -- even a partial climb toward gait_valid counts, this is a mechanism-health canary not a repair confirmation -- with walk/det+sto still >=10/12 valid and no new falls. FAIL if leg duty is statistically unchanged/worse vs dgfresh (matching the same null result at higher noise), or det/sto validity regresses, or falls appear -- closes 'keep exploration noise alive longer' as a companion lever to duty_gate, forcing a structural mechanism (reward computed off the deterministic action, or an init-time change) for the next design pass.

