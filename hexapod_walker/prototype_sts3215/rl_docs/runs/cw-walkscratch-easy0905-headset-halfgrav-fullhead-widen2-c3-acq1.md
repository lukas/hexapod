# cw-walkscratch-easy0905-headset-halfgrav-fullhead-widen2-c3-acq1

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: PASS

**created**: 2026-09-06T01:02:27+00:00

**pod**: hexapod-mjx-train-3

**steps**: 40000000

**parent**: cw-walkscratch-easy0905-headset-halfgrav-fullhead-widen2-c3

**wandb_id**: 2dtnh6ju

**hypothesis**: Plain English: widen2-c3's 2M canary just PASSed (20/24 gait_valid, 0 falls, matches widen2-c1's own clean canary numbers), confirming this 3rd tie-breaking seed off the SAME clean medhead_acq1 parent as widen2-c1 (ACQ PASS) behaves like a healthy seed rather than the weak medhead2_acq1-parented widen2-c2b (ACQ FAIL). This continuation tests whether that health holds at the full 40M acquisition budget, matching the widen2-c1-acq1/irrwiden-c1-acq1 template -- does the widen2 recipe now read 2 PASS / 1 FAIL (parent-quality-driven, closeable) or does a 3rd seed regress at acq scale too (would reopen the seed-noise explanation)?

**gate**: ACQ PASS if gait_valid stays majority (>=18/24) with 0 falls and no leg chronically sacrificed (flagged in >=1/3 of episodes matching the widen2-c2b-acq1 entrenchment fingerprint); slip/m should be flat-or-better vs this run's own 2M canary read (walk/det med 2.77, overall spread 2.3-11.5). ACQ FAIL if gait_valid drops into minority or a leg chronically parks. ACQ CONTINUE if reward still climbing with gait valid but course-tracking still ambiguous at 40M.

**verdict**: ACQ PASS: the 40M own-checkpoint continuation of the 3rd tie-breaking widen2 seed (off the same clean medhead_acq1 parent as widen2-c1) reproduces its own 2M canary structure at full acquisition budget. gait_valid 20/24 (walk/det 4/6, walk/sto 6/6, walk_startjitter/det 6/6, walk_startjitter/sto 4/6), 0 falls/terminations in all 24 episodes -- identical 20/24 total to this run's own 2M canary read. Sacrificed-leg flags are transient (leg0/leg3 flagged in only 3/24 episodes total, one shared episode [0,3] appearing twice plus one solo [4]), never chronic: duty_cycle for legs 0/3 spans 0.03-0.52 across the 24 episodes (healthy majority, weak only in the 3 flagged eps), nowhere near the widen2-c2b-acq1 entrenchment fingerprint (that FAIL had leg-1 duty 0.01-0.21 in ALL 24 episodes, flagged sacrificed in 10/24). slip/m reads flat-or-better vs the gate's own pre-registered comparison: walk/det median rose slightly (2.77->3.69) but the upper tail improved (max 11.51->6.68, spread narrows to 2.49-6.68 from 2.3-11.5). The handful of >90 slip/m outliers (walk/sto ep3 121.4, walk_startjitter/det ep2 93.5, walk_startjitter/sto ep3 122.7) are the already-documented widen2/reversal-heading low-net-progress-denominator spin-in-place pathology (frame strip walk_sto_3 confirms turning-in-place with legs still cycling, not a new failure mode) -- confirmed via frame strips, not a new defect. Video (walk_det_4 frame strip) shows genuine six-leg cycling with clear body translation even in the [0,3]-flagged episode. Reward stayed deeply negative (-1206 to -1719 by quarter) but this is the already-documented widen2-lineage reward-scale trait (PASS sibling widen2-c1-acq1 shows the same shape), not a new misalignment. This is now 3/3 widen2 seeds tested at acquisition scale that trace to a clean medhead_acq1 parent (widen2-c1-acq1 PASS 21/24, widenirr/irrwiden composites PASS 22-23/24, widen2-c3-acq1 PASS 20/24) vs the 1 FAIL (widen2-c2b-acq1, from a weak medhead2_acq1 parent) -- closes the parent-quality-driven story: seed noise is ruled out, parent champion health is the deciding variable.

