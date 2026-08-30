# cw-walkcurr-litrep-box-s0

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: RUNNING

**created**: 2026-08-30T22:22:34+00:00

**pod**: hexapod-mjx-train-3

**steps**: 150000000

**parent**: cw-walkcurr-pf-central-sv-s0-rr2

**wandb_id**: fffvsddv

**hypothesis**: Plain English: if we copy what actually worked in the published from-scratch legged-RL recipes -- a TIGHT symmetric action box around the standing stance (Walk in the Park's ablation-proven crucial ingredient, here yaw+-11/hip+-20/knee+-23 deg via the new goal.joint_action_box_* keys), a plain velocity-tracking reward with only mild smoothness (WALKCURR_SV diet + k_action_delta=0.01), fall-only termination (over-current CLAMPED not terminated: safety.over_current_trip_s=999999 -- the 900-1150 kills/window absorbing penalty of every prior arm is in NO published recipe), and a Rudin-2021-scale budget (150M samples, 4096 envs) -- then from-scratch PPO should finally discover a real gait where every unbounded-action-space arm froze or died. Operator literature ruling 08-30 (final pre-registered wave, 2 seeds, rule (a) amended for the box). Bias hip is 40 not the sv arms' 45: operator commit 88d852c3 (08-28) raised the hip cap 30->40, moving the raw mid-range -25 -> -20, so +40 recenters a=0 on WALK_PLANT hip 20 exactly. WALKCURR_SV_LITREP bank 5/5 green; box tests 6/6 green; snapshot bbc569e5.

**gate**: Rung-1 gate at 150M: C-env det fixed-forward panel (n>=6) -- zero tilt terminations, cmd_prog_frac >= 0.35, direction_err_deg <= 30, slip/m <= 3.0, gait_valid >= 4/6 with all six legs cycling, real stepping on video. Mid-run litmus: env/walk_speed must decisively clear the 0.02 m/s static floor and trend toward the 0.05-0.06 band with stable ep_len (freeprog-escape alone is NOT a valid litmus per the 08-29 close-out). NOTE: over-current termination is OFF by design (operator clamp ruling) -- terminations read tilt-only in training AND eval; do not count over_current absence as progress. PRE-COMMITTED (operator ruling d): if BOTH seeds land park-stand/no-gait with flat reward at 150M, RETIRE walkcurr as an honest DONE-negative scope finding (walkteach carries walking); if either seed shows a real gait_valid>0 escape, seed-replicate and re-price current realism next.

