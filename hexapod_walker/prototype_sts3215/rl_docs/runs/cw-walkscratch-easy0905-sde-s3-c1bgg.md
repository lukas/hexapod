# cw-walkscratch-easy0905-sde-s3-c1bgg

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: ACQ FAIL (MISALIGNED)

**created**: 2026-09-05T13:28:20+00:00

**pod**: hexapod-mjx-train-9

**steps**: 40000000

**parent**: cw-walkscratch-easy0905-sde-s3-c1b

**wandb_id**: bzf8msie

**hypothesis**: Plain English: sde-s3-c1b (DIG-IN-flagged, legs [1,3] chronically parked, ep_rew_mean climbed to 2198 while walk_speed declined — the same LEGPARK-SKATE exploit as sde-s1-c2/sde-s2-c2/sde-s0-c4) gets the identical structural repair (reward.walk_gait_gate MIN-over-support-legs income gate + k_step_event=1.0 wake-up gradient) already validated in-flight on sde-s1-c3gg/sde-s2-c3gg and just extended to sde-s0-c4gg this cycle. A 4th independent seed sharpens whether the gate reliably escapes the basin regardless of which leg subset got parked, before deciding whether the whole sde/sdehalfgrav+gSDE cell can be revived at this rung.

**gate**: Same rung gate as sde-s1-c3gg/sde-s2-c3gg/sde-s0-c4gg: DR-0 harness gait_valid True on a majority of walk/walk_startjitter det+sto episodes, no chronically-sacrificed leg (all 6 duty>0.10), slip/m trending back toward the 2.9 band, 0 falls, video-confirmed six-leg cycling.

**verdict**: The walk_gait_gate+k_step_event structural repair FAILs on this bare-sde seed too. Harness (logs/ckpt_eval/cw_walkscratch_easy0905_sde_s3_c1bgg_gate/report.json): gait_valid 0/24 primary walk/det (1/24 overall, one lucky sto episode), legs [1] (+[3] intermittently) chronically parked across nearly every episode, slip med 4.0-4.4 (above the 2.9 band), fwd med only 1.2-1.5m/20s. env/walk_gait_gate_factor (wandb_history.csv) sits 0.81-1.0, effectively saturated near ceiling for most of the run despite the harness flagging leg-1 sacrifice throughout -- same non-diagnostic-gate root cause as every other gg FAIL. Reward still rising (quarters 1329/2389/2469/2515) is NOT progress evidence per 08-21 given the saturated internal proxy. **This is the 6th and last of 6 bare-sde/sdehalfgrav-remcost seeds tried under the walk_gait_gate+k_step_event repair -- CLOSES the lever at 6/6 FAIL, fully confirmed** (sde-s1-c3gg, sde-s2-c3gg, sdehalfgrav-remcost-s{0,1}-gg2, sde-s0-c4gg, this run). CURRENT_TRUTHS.md updated. No further walk_gait_gate-repair launches on the sde family; the walk_duty_gate mechanism (5 canaries currently mid-gate-eval) is the only remaining open repair lever.

