# cw-walkscratch-easy0905-headset-base-irr-acq1

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: fail

**created**: 2026-09-05T14:48:50+00:00

**pod**: hexapod-mjx-train-3

**steps**: 40000000

**parent**: cw-walkscratch-easy0905-headset-base-irr-c1

**wandb_id**: hqxngd1e

**hypothesis**: Plain English: the irregular-direction-change-timing canary on the 1g base heading family (headset-base-irr-c1) reads healthy at 2M and, unusually, the harness's own 24-episode gate panel (run early by the prestage/podeval tooling) already shows the family's established clean fingerprint -- 6/6 gait_valid on plain walk/det, 6/6 on walk/sto, 6/6 on walk_startjitter/sto, 0/24 falls, fwd 0.11-0.17 m/s, only the known walk_startjitter/det leg-1/4 favoritism (3/6) that every other base-family PASS also shows -- this gives it the full 40M acquisition budget to mature under jittered (goal.walk_cmd_resample_jitter=0.5) direction-change timing, mirroring the halfgrav sibling's headset-halfgrav-irr-acq1 (same rung, same cycle). Own-checkpoint warm start only, no teacher/BC/motion-prior.

**gate**: Acquisition milestone at OWN physics (1g) with IRREGULAR direction-change timing: 20s held-out episodes across the 3-heading set with jittered resample timing, >=0.03 m/s median net forward along each commanded heading, 0 falls in 12 det episodes, gait_valid true (no sacrificed legs) in the majority of det episodes, six-leg lift/place on video, no belly drag; report sto. Per 08-21 ruling: continue/realign if still climbing at cutoff rather than an auto-fail.

**verdict**: ACQ FAIL (misaligned) — the base-family (1g) irr-timing acquisition follow-up degrades below the champion lineage it was warm-started from (headset-base-acq1 PASS -> irr-c1 2M CANARY PASS -> this 40M arm FAILs). Evidence: gait_valid only 3/6 in the PRIMARY un-perturbed walk/det mode (FAILS the adopted >=4/6 bar from the s0c1-acq1 ruling) — legs [4],[1],[4] flagged in 3/6 det episodes, duty as low as 0.04-0.07 (below the 0.10 sacrifice bar) though swing_count 37-84/20s (real, infrequent swings — active marginal underuse, not sde-style near-zero-touch LEGPARK-SKATE). walk_startjitter/det also 3/6, one episode's flagged leg duty 0.01. Overall 18/24 passes the secondary bar alone but the AND requires both. Separately, slip_per_m runs 3.86-4.76 across ALL 24 episodes (including the gait_valid ones) — uniformly worse than every base/halfgrav sibling this campaign (typically 2.2-3.0, inside the 2.9 teacher band); this run clears none of them. Video (walk_det_0/1 frame strips) shows legs actively cycling, not a frozen rigid splay — confirms this is the marginal-duty class, not the sde LEGPARK class, but the adopted rule disqualifies it regardless of speed/falls (0/24 falls, reward quarters 503.7/969.4/1118.5/1296.7 still climbing +16% Q3->Q4). Why FAIL not continue-per-08-21: this is the SAME marginal-duty-hardens-not-heals pattern already closed on s0c1-acq1 (canary flagged a weak leg, 40M budget hardened it rather than fixing it) — more budget is not the lever; the reward doesn't price sub-0.10-duty legs enough under the irr-timing (jittered heading resample) composition even though the SAME plain-freeprog recipe passed cleanly without irr-timing (base-acq1/s1c1-acq1) and with irr-timing at 0.5g (need halfgrav-irr-acq1's own read, concurrent-cycle-owned). Consequence: the irr-timing rung's real ACQ gate is NOT a clean pass on the 1g cell off this lineage; the walk_duty_gate mechanism (already mid-canary elsewhere) is the pre-registered repair candidate and should be tried on this cell's irr-timing composition too once its own bare/sde-family read lands, rather than relaunching a plain-recipe seed here. Evidence: logs/ckpt_eval/cw_walkscratch_easy0905_headset_base_irr_acq1_gate/report.json, W&B hqxngd1e.

