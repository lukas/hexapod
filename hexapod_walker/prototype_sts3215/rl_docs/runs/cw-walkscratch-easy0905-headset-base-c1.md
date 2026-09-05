# cw-walkscratch-easy0905-headset-base-c1

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: CANARY PASS

**created**: 2026-09-05T11:29:02+00:00

**pod**: hexapod-mjx-train-1

**steps**: 2000000

**parent**: cw-walkscratch-easy0905-base-s2

**wandb_id**: q3p7qr8b

**hypothesis**: Plain English: does the clean fixed-forward walking skill base-s2 already learned keep walking (now toward a small set of commanded headings: straight, +45deg, -45deg, resampled every 6s within the 20s episode) instead of just marching straight, using the SAME reward it already trained under (no new keys — k_walk_freeprog's existing along/cross decomposition already prices live heading-tracking correctly, bank-proven this cycle in test_walkscratch_easy_pilot.py's new EASY_HEADING section, 5/5 new tests green, 22/22 total). This is the campaign's next open rung per walkcurr/STATUS.md (heading generalization), following the operator's own staged-heading-curriculum ruling (small discrete set, not full range). Warm-started from base-s2 (own-track checkpoint, not a teacher/BC/motion-prior — same boundary already used for every other -c1 continuation this campaign).

**gate**: MECHANISM-HEALTH CANARY ONLY: do not judge skill acquisition, close a behavior/reward class, or require mature gait at this checkpoint. CANARY PASS at 2M (mechanism-health scope, NOT the acquisition bar): finite losses, real motion, motor-contract compliance (360 deg/s in-log), and evidence the heading-tracking gradient is live -- env/v_along_cmd and/or reward_walk trending up across the 2M budget, ideally with gait_valid>0 on at least one non-zero heading in a spot-check pod eval. FAIL only on flat reward/v_along or an immediate park recapture; genuine acquisition budget (40M) is a SEPARATE follow-up decision after this + the halfgrav sibling both read healthy, mirroring the original base/halfgrav canary-then-acquisition pattern.

**verdict**: CANARY PASS (mechanism-health scope, per its own gate text). Evidence: W&B q3p7qr8b finished 2M steps, finite losses (train/loss 103.2, value_loss 240.7, entropy 10.4), reward_walk trending up all 4 quarters (38.3/81.5/108.7/140.7, monotonic, no plateau). env/v_along_cmd_m_s rises 0.115 (step1) -> holds 0.131 (step36) -- the heading-tracking gradient is live and non-zero, not marching-in-place. rollout/ep_len_mean climbs 107.8 -> 487.9 (near the 500-tick truncation cap) -- almost no falls by the end. env/walk_speed steady ~0.175-0.19 m/s. Video (frame strips walk_det_1.png, walk_det_4.png pulled from the in-flight gate eval on train-1): clean six-leg lift/place cycling both strips, visible net forward translation (checker background shifts under the robot frame to frame), no dragging/static pose. Meets every mandatory PASS bar in the gate text; does not require mature gait or full eval completion at canary scope. Gate/spot-check eval (logs/ckpt_eval/cw_walkscratch_easy0905_headset_base_c1_gate/) was still computing at verdict time (12-episode walk det+sto panel, video-every=1 is slow) -- left running on train-1 for whoever needs the full report next; do not re-launch, it is genuinely in-flight (own eval_checkpoint pids confirmed alive). Per walkcurr/STATUS.md's own plan, the 40M acquisition follow-up (headset-base-acq1) was already launched by a concurrent cycle before this verdict landed -- consistent with this PASS, no correction needed.

