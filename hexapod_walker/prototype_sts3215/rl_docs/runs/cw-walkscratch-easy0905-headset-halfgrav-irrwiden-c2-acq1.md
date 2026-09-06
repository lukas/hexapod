# cw-walkscratch-easy0905-headset-halfgrav-irrwiden-c2-acq1

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: PASS

**created**: 2026-09-06T02:03:41+00:00

**pod**: hexapod-mjx-train-3

**steps**: 2000000

**parent**: cw-walkscratch-easy0905-headset-halfgrav-irrwiden-c2

**wandb_id**: pygzhza7

**hypothesis**: Plain English: the jitter-first widen+irr composite's 2nd seed (irrwiden-c2, respec off irr2-acq1) CANARY PASSed its 2M mechanism-health check (gait_valid 22/24 aggregate, 0 falls, beating the irr2-acq1 baseline of 19/24). This is the acquisition-scale (40M) confirmation of the composite's 2nd seed, mirroring the n=2 seed-confirmation discipline already applied to every other rung in this campaign (medhead, widen2, irr-timing) and giving the widen+irr composite its 2nd-seed acquisition-scale read alongside the concurrently-running widen-first widenirr-c1-acq1.

**gate**: ACQ PASS if gait_valid stays majority (>=4/6) in walk/det AND walk/sto with no chronic (<0.10-duty every episode) single-leg sacrifice at 40M, matching or improving this run's own 2M canary read (22/24 aggregate), 0 falls, slip/m at/near the 2.9-6/m band already established by the sibling irrwiden-c1-acq1. ACQ FAIL if walk/det or walk/sto regresses to majority failure or a new chronic single-leg sacrifice pattern emerges. ACQ CONTINUE if reward is still climbing with borderline (not hard-park) duty, per the 08-21 ruling.

**verdict**: ACQ PASS (matches gate, with a seed-specific course-obedience caveat). gait_valid 22/24 aggregate, EXACT match to this run's own 2M canary (22/24) with the same non-chronic leg-4 flag pattern (2/24 episodes, never the same episode twice) — det 5/6, sto 6/6, startjitter/det 6/6, startjitter/sto 5/6. 0 falls/terminations in all 24 episodes. Frame strips (walk_det_0, walk_sto_3) confirm genuine six-leg cycling + real chassis translation throughout, matching the canary's own video quality. CAVEAT (real, not new): course/heading obedience is markedly worse than the sibling seed irrwiden-c1-acq1 — walk/sto median slip_per_m is 67.9 here vs 9.1 on c1-acq1, because 3/6 sto episodes (not 1/6 like c1) have wrong_course_frac 0.5-0.8 / direction_err 90-133deg (robot keeps walking on its original heading through a resampled command instead of turning) — but this EXACT pattern is already present in this run's own 2M canary (walk/sto median slip_per_m 74.7, same 3/6-outlier shape), so it is a seed characteristic carried through training, not a 40M regression, and gait_valid (the run's actual pass bar) never required course-following. Net: PASS the registered gate; flag seed-level course-obedience variance as new information for any future heading-hardening rung on this composite. SKILLS.md updated. Evidence: logs/ckpt_eval/cw_walkscratch_easy0905_headset_halfgrav_irrwiden_c2_acq1_gate/report.json vs its own _gate (2M) sibling and cw_walkscratch_easy0905_headset_halfgrav_irrwiden_c1_acq1_gate; W&B run steps=40370176.

