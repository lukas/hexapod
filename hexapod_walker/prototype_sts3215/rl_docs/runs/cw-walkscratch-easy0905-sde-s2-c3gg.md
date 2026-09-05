# cw-walkscratch-easy0905-sde-s2-c3gg

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: ACQ FAIL

**created**: 2026-09-05T12:39:40+00:00

**pod**: hexapod-mjx-train-7

**steps**: 40000000

**parent**: cw-walkscratch-easy0905-sde-s2-c2

**wandb_id**: vb2m7gr2

**hypothesis**: Second independent seed of the LEGPARK-SKATE structural repair (see sde-s1-c3gg): sde-s2-c2 shows the identical exploit (sacrificed legs [1]/[3,4], reward up while walk_speed declines to the freeprog cap) — same walk_gait_gate=1.0 + gait_gate_stride_mm=5 + k_step_event=1.0 continuation from its own checkpoint. Two seeds decide whether the structural gate reliably recovers six-leg cycling from inside the legpark basin, or whether the sde cell should be closed (Gaussian families are already 8/8 valid-gait PASS at this rung).

**gate**: Acquisition milestone at easy physics WITH gait validity: 20s held-out fixed-forward, >=0.03 m/s median net forward, 0 falls in 12 det episodes, gait_valid true (no sacrificed_legs, all six legs' swing_count > 5) in the majority of det episodes, six-leg lift/place on video, no belly drag; report sto. Watch env/walk_gait_gate_factor (must rise from ~0 toward 1) and env/walk_speed (must NOT collapse to ~0 — full-park recapture = FAIL regardless of reward). Per 08-21: factor rising + speed alive but gate unmet at 40M = continue; reward flat AND factor flat at 0 = FAIL (income blackout, retry at lower gate dose e.g. 0.7).

**verdict**: FAIL (misaligned) - second independent seed of the walk_gait_gate+k_step_event structural repair, same failure class as sde-s1-c3gg. Harness: 0/24 gait_valid across all 4 scenarios (walk/det, walk/sto, walk_startjitter/det, walk_startjitter/sto all 0/6); leg 1 chronically parked (duty 0.0, swing_count 3/20s) every episode. 0/24 falls, walk_speed stable ~0.066-0.14 m/s, ep_len saturates near 2000, ep_rew_mean still climbing to ~2600 at 40M cutoff, no plateau. Same root cause as sde-s1-c3gg (cross-confirmed): env/walk_gait_gate_factor reads ~0.98-0.99 for the whole back half of training despite the harness's duty>0.10 bar flagging leg 1 as sacrificed the entire time - the gate's rare-completed-swing scoring window is satisfied by a token swing every several seconds and never drives the MIN-over-legs factor down the way a true duty-cycle price would. Contact sheet (logs/ckpt_eval/cw_walkscratch_easy0905_sde_s2_c3gg_gate/contact_sheet.png) shows the same rigid-single-leg-extended pose with minimal net body translation. Per 08-21 MISALIGNED, not continue-blind: the mechanism's own internal proxy is ALSO plateaued at its ceiling, so more budget would not move it. Closes the walk_gait_gate repair path for the bare-sde cell at this recipe (2/2 seeds FAIL, matching the earlier sde-idleterm 2/2 FAIL on the alternate repair lever) - per CURRENT_TRUTHS, no cheap repair variant remains untried; a genuinely new per-leg-utilization pricing mechanism (stricter minimum-duty/swing-count term instead of a gameable completion score) needs its own design+bank pass before further sde spend. Awaiting sde-s0-c4gg/sde-s3-c1bgg (still mid-eval) to confirm this is family-wide before closing the cell in CURRENT_TRUTHS.md.

