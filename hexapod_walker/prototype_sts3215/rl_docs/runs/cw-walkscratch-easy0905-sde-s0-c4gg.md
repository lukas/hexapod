# cw-walkscratch-easy0905-sde-s0-c4gg

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: ACQ FAIL (MISALIGNED)

**created**: 2026-09-05T13:24:55+00:00

**pod**: hexapod-mjx-train-8

**steps**: 40000000

**parent**: cw-walkscratch-easy0905-sde-s0-c4

**wandb_id**: q2kox1j4

**hypothesis**: Plain English: sde-s0-c4 (verdicted FAIL, LEGPARK-SKATE — legs 1/4 chronically parked, 7mm micro-quiver stride, slip/m 4.8-5.2) is a 3rd independent gSDE seed sharing the same exploit already being repaired on sde-s1-c2/sde-s2-c2 via the structural reward.walk_gait_gate (MIN-over-support-legs income gate) + k_step_event=1.0 wake-up gradient (c3gg pair, in flight). This continuation applies the identical fix to a 3rd seed from its own checkpoint, to see whether the gate reliably recovers six-leg cycling across MORE than 2 independently-converged instances of the basin, or whether s0's fingerprint (2-leg park, not 1) resists it differently.

**gate**: Same rung gate as sde-s1-c3gg/sde-s2-c3gg: DR-0 harness gait_valid True on a majority of walk/walk_startjitter det+sto episodes, no chronically-sacrificed leg (all 6 duty>0.10), slip/m trending back toward the 2.9 band, 0 falls, video-confirmed six-leg cycling.

**verdict**: The walk_gait_gate+k_step_event structural repair FAILs on this bare-sde seed too -- LEGPARK-SKATE persists at 40M. Harness (logs/ckpt_eval/cw_walkscratch_easy0905_sde_s0_c4gg_gate/report.json): gait_valid 0/24 across all four scenarios, legs [1,4] chronically parked (identical trajectory every det episode -- deterministic policy collapsed to one gait), slip med 4.3-5.1 (well above the 2.9 band), fwd med only 1.0-1.3m/20s (vs 2.5-3.5m for healthy walkers). Root cause identical to every prior gg FAIL: env/walk_gait_gate_factor sits saturated 0.97-1.0 for effectively the whole 40M run despite two legs reading 0 duty the entire time -- the mechanism's own internal proxy is already at ceiling, so per 08-21 the still-rising reward (quarters 1371/2393/2530/2631) is NOT evidence of progress, it's the reward paying out under a saturated, non-diagnostic gate. This is the 5th of 6 bare-sde/remcost seeds to fail this exact way; closes the walk_gait_gate lever at 5/6 (sde-s3-c1bgg, same batch, pending separately).

