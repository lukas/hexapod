# cw-walkscratch-easy0905-headset-crossgrav-medhead-dr-mass1x-c1

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: PASS

**created**: 2026-09-06T05:08:56+00:00

**pod**: hexapod-mjx-train-0

**steps**: 2000000

**parent**: cw-walkscratch-easy0905-headset-crossgrav-medhead-abrupt-c1-acq1-cont40m

**wandb_id**: uw36u2tb

**hypothesis**: Restore nominal (1x) chassis+leg mass randomization -- the easy0905 recipe has trained with body/leg mass pinned at an exact fixed 1.0x scale (dr-scale=0.0 collapses the RandRanges mass_scale pair(0.85,1.20) to a single fixed point when not explicitly overridden) throughout the whole crossgrav campaign, i.e. every episode sees the EXACT same mass regardless of print/battery/payload spread. Does the campaign's most durable champion (medhead-abrupt-c1-acq1-cont40m, 80M steps, 24/24 clean, 0 falls) survive its own nominal own-DR mass range (0.85-1.20x body, +-10% per-leg-link jitter) without retraining collapse? Isolated single-axis diagnostic, same template as the sibling latency/deadband/torque/noise DR-restoration arms.

**gate**: PASS/INFORMATIVE-POSITIVE if aggregate gait_valid stays majority (>=18/24) across the full 4-panel harness with no NEW chronic single-leg sacrifice and 0 falls -- shows the gait does not depend on the fixed-mass idealization. FAIL/INFORMATIVE-NEGATIVE if it collapses (gait_valid <12/24, a new chronic leg, or falls appear) -- shows mass realism is a binding constraint the DR-rung must budget real training time against.

**verdict**: CANARY PASS: restoring nominal (1x) body/leg mass spread (dr.mass_scale=0.85-1.20 + dr.leg_mass_jitter_pct=0.10, previously pinned at fixed mass all campaign) on the campaign's cleanest champion (medhead-abrupt-c1-acq1-cont40m, 80M, 24/24) costs almost nothing at 2M: aggregate gait_valid 23/24 (walk/det 6/6, walk/sto 6/6, walk_startjitter/det 5/6 one non-chronic leg-4 flag, walk_startjitter/sto 6/6), 0 falls, 0 terminations, reward rising every quarter (55/111/167/237). slip_per_m banded 3.2-5.8, consistent with every sibling DR-restore canary. Joins deadband1x/latency1x/noise1x/tiltnoise1x/torquefade2x/gyronoise1x as a clean single-axis DR PASS -- mass realism is not a binding constraint on this champion. Evidence: logs/ckpt_eval/cw_walkscratch_easy0905_headset_crossgrav_medhead_dr_mass1x_c1_gate/report.json, W&B uw36u2tb.

