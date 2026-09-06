# cw-walkscratch-easy0905-headset-crossgrav-medhead-irrfwd-c1-acq1

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: PASS

**created**: 2026-09-06T03:11:52+00:00

**pod**: hexapod-mjx-train-3

**steps**: 40000000

**parent**: cw-walkscratch-easy0905-headset-crossgrav-medhead-irrfwd-c1

**wandb_id**: naxsaxqj

**hypothesis**: Plain English: the medhead-irrfwd-c1 2M canary just PASSed (gait_valid 22/24, 0 falls, unusually tight clean slip band) -- composing command-timing-irregularity (irr) jitter natively at 1g on top of the already-crossgrav-transferred medhead champion works at canary scale. Does the same recipe hold at full 40M acquisition budget, matching the campaign's own-checkpoint-continuation pattern already validated for every other crossgrav/irr rung?

**gate**: ACQ PASS if aggregate gait_valid stays >=17/24 with no NEW chronic (<0.10-duty every episode) single-leg sacrifice vs the 2M canary's transient legs-[2,5]-in-2/6-episodes flag; ACQ FAIL if a chronic sacrifice fingerprint emerges that wasn't present at 2M.

**verdict**: ACQ PASS: aggregate gait_valid 21/24 (walk/det 4/6, walk/sto 6/6, walk_startjitter/det 6/6, walk_startjitter/sto 5/6), 0 falls in all 24 episodes. Vs its own 2M canary (22/24): essentially FLAT, not entrenching -- the same episode positions (walk/det ep1, ep5) already showed the identical leg-2/5 softening at 2M (sac [2,5]/[2,5]); at 40M ep5 improves to sac [5] only. Slip/m and progress_ratio nearly identical to the canary across all 4 panels (walk/det slip med 3.72->3.64, prog 1.96->2.01; startjitter/det 3.80->3.55). Contact sheet shows real six-leg cycling, no splayed/frozen leg. Confirms medhead's forward irr-timing composition axis is durable at full 40M acquisition with a stable (not worsening) marginal leg-2/5 signature -- the SAME behavioral class as the widenfwd sibling, not the irracq1/irr2acq1/s3acq entrenchment pattern (those regressed 9-10 points and converged on a chronic leg-1/4 signature; this one didn't move).

