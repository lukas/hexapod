# cw-walkcurr-sac-sv-s1-budget10m

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: RUNNING

**created**: 2026-08-29T18:42:07+00:00

**pod**: hexapod-mjx-train-5

**steps**: 10000000

**parent**: cw-walkcurr-sac-sv-s1

**wandb_id**: fipmnqt9

**hypothesis**: Plain English: SAC seed-1's 2M-step discovery run learned a real stepping gait (all 6 legs cycling, speed matching the 0.05-0.06 cmd band) but falls over via tilt_pitch/tilt_roll in every single eval episode within a couple of steps (fwd 0.02-0.05m) -- a stumble/balance problem, not the stuck-in-place static-quiver problem every PPO arm had. train_ppo_mjx.py's --algo sac path unconditionally refuses --init-from (stock-SAC-only restriction, found this cycle when the checkpoint-continuation respec died clean at that check) so there is no checkpoint-continuation path yet; this arm instead reruns the IDENTICAL seed/diet/algorithm/hyperparams from scratch to a 5x budget (2M->10M) in one process -- under this stack's fixed-seed determinism that reproduces s1's own first-2M trajectory exactly and then keeps training past the point where s1 stopped, which is the practical equivalent of 'continuing' until real SAC-checkpoint warm-starting is built. Only lever: total budget. Prediction-if-true: env/walk_speed holds in the 0.05-0.08 m/s band past 2M while roll_peak_deg/fall rate on the rung-1 panel drops and forward_dist_m rises past the current ~0.02-0.05m ceiling by 10M. Prediction-if-false: falls persist at the same rate/roll_peak with speed pinned through 10M -- the diet has no balance-shaping signal strong enough for this lever alone, and the next fork is adding a mild anti-tilt price (still SV-diet-legal magnitude change, roll/pitch pricing already exists in REWARD.md just zeroed here) or building real SAC --init-from support rather than more raw budget.

**gate**: Rung-1 C-env det+sto fixed-forward panel (n>=6 each) at 10M: PASS needs progress_ratio med >=0.35, slip/m <=3.0, gait_valid >=4/6, and falls (tilt_pitch/tilt_roll term) on <=1/6 det episodes -- i.e. the stumble is fixed, not just the stepping. PARTIAL/continue (08-21): fall rate or forward_dist improving vs cw-walkcurr-sac-sv-s1's baseline (24/24 falls, fwd med ~0.03m) even short of the full bar. FAIL: fall rate and forward_dist unchanged (still ~24/24 falls, fwd ~0.02-0.05m) at 10M with flat reward -- diet lacks a balance-shaping signal at this budget scale, fork to an anti-tilt pricing dose or build real SAC checkpoint-continuation next.

