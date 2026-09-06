# cw-walkscratch-easy0905-headset-crossgrav-medhead-ramp-widenfwd-c1-acq1

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: ACQ_FAIL_MECHANISM

**created**: 2026-09-06T03:31:35+00:00

**pod**: hexapod-mjx-train-11

**steps**: 40000000

**parent**: cw-walkscratch-easy0905-headset-crossgrav-medhead-widenfwd-c1-acq1

**wandb_id**: x1nue97w

**hypothesis**: Plain English: the ramp-transition champion's 2M canary just PASSED the same native-1g heading-widen extension test its abrupt sibling passed -- does it hold up at full 40M acquisition scale too, mirroring the abrupt-widenfwd-c1-acq1 companion arm?

**gate**: ACQ PASS if aggregate gait_valid stays >=18/24 with no NEW chronic single-leg sacrifice pattern vs the 2M canary's own 21/24 baseline (max 2/6 per leg); 0 falls required. FAIL/MECHANISM if a chronic leg-sacrifice fingerprint (>=4/6 same leg in any mode) emerges that wasn't present at 2M.

**verdict**: ACQ FAIL - MECHANISM (mild/borderline instance of the established startjitter-panel leg-entrenchment class): aggregate gait_valid 18/24, at the bare floor (2M canary was 21/24). Primary modes hold clean (walk/det 5/6, walk/sto 6/6) but walk_startjitter/det collapses to 3/6 (leg-4 sac in eps 2,3,5) and walk_startjitter/sto to 4/6 (leg-4 ep4, leg-0 ep5) -- leg-4 specifically VIOLATES this run's own pre-registered 'max 2/6 per leg' anti-regression clause (went from 1/6 at 2M canary to 3/6 at 40M in the same mode). This is the FIRST instance of the widely-documented cross-recipe startjitter-panel leg[1,4] entrenchment pattern (CURRENT_TRUTHS 09-06 ~04:1x-04:2x) appearing on a medhead-lineage composite -- but via the 'ramp' gravity-transfer variant, not the 'abrupt' variant that is 5/5 clean across every 40M+ read attempted. Severity caveat, read honestly: this is MILDER than the severe precedent cases (s3acq's leg-1 duty 0.03-0.20 chronic in 4/6+3/6; irracq1's near-zero duty) -- leg-4's own duty here (0.06-0.24 at 40M vs 0.08-0.22 at 2M) is nearly UNCHANGED in magnitude, just crossing the flag threshold 2 more times, and frame strips (walk_startjitter_det_3, _5) show the leg still visibly participating in a genuine six-leg gait with body translation, not a frozen/parked limb. 0 falls/terminations in all 24 episodes; reward net-rose across quarters (-735.2/-970.3/-784.3/-568.4) but per the already-closed structural-repair precedent for this exact pathology class, more training is what CAUSES this entrenchment elsewhere in the campaign, not a fix -- continuing this same recipe is not expected to self-correct. Verdicted FAIL to keep gate discipline consistent with the s3acq/irracq1/irr2acq1 precedent (same behavioral class, same leg role), while flagging the smaller magnitude so a future reader doesn't conflate this with the severe cases.

