# cw-walkscratch-easy0905-headset-base-irr-placementjit-c1

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: RUNNING

**created**: 2026-09-05T22:42:43+00:00

**pod**: hexapod-mjx-train-3

**steps**: 2000000

**parent**: cw-walkscratch-easy0905-headset-base-irr-acq1

**wandb_id**: dctducci

**hypothesis**: Plain English: does exposing training to the SAME imperfect start-pose distribution the eval walk_startjitter panel already tests fix the base(1g) family's chronic leg-1/4 favoritism, when 7 independently-designed reward-price mechanisms (walk_gait_gate, walk_duty_gate x9 doses/checkpoints, walk_swing_gate x4) all failed on this exact checkpoint class? Code read (rl_move/sim/domain_rand.py, sim_env.py:600-630): this whole easy0905 family trains at --dr-scale 0.0 with NO dr.placement_noise_deg/bad_start_* override, so every training episode starts from the IDENTICAL nominal pose -- the policy has literally never seen a perturbed start joint configuration, while eval_checkpoint.py's walk_startjitter mode (the ONE mode where irr_acq1 shows the pathology; plain walk/det on the narrow 3-way irr set already runs 6/6 clean per its own PASS notes) tests exactly that gap. This is a genuinely different, already-proven mechanism (not a reward shape): dr.placement_noise_deg was built+bank-validated on the joystick track months ago (cw-walk-placementnoise6-r3, PASS: 'own-cfg det+sto 12/12 gait_valid, 0 term... DR0 nominal-placement retention is CLEAN') and works at --dr-scale 0.0 via the absolute-override path (sim_env.py:621-630, setattr bypasses dr_scale scaling) -- zero new code, zero new reward keys, no bank-test gap (it is a state-distribution fix, not a reward mechanism). Dose (jitter 3deg, 25% chance of one 8-16deg-off joint) is set to MATCH eval_checkpoint.py's own walk_startjitter defaults exactly, closing the train/eval gap directly rather than guessing a dose. This is arm 1/3 of a batch: retrofit onto irr_acq1 (this arm, most name-checked pattern), retrofit onto medhead_acq1 (2nd arm, same family/different heading breadth), and a from-scratch bake-in onto the lightly-trained s0c1 2M seed (3rd arm, mirrors the campaign's own fresh-vs-retrofit split already used for both closed reward mechanisms).

**gate**: MECHANISM-HEALTH CANARY ONLY: do not judge skill acquisition, close a behavior/reward class, or require mature gait at this checkpoint. MECHANISM-HEALTH CANARY ONLY (2M): repair-signal if walk_startjitter/det's flagged legs (1,4) majority-clear the harness gait_valid duty>0.10 bar (matching this family's own accepted-PASS range) with 0 new falls, AND plain walk/det stays >=5/6 valid (no regression from irr_acq1's own clean 6/6). FAIL - MECHANISM if the same legs stay majority-parked in walk_startjitter/det regardless of whether training exposed real start-pose variance (check env/v_along_cmd_m_s and reward trend for real learning signal, not saturation).

