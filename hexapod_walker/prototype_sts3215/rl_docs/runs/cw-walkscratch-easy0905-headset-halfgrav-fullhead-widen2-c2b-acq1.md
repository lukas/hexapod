# cw-walkscratch-easy0905-headset-halfgrav-fullhead-widen2-c2b-acq1

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: ACQ FAIL

**created**: 2026-09-05T22:28:03+00:00

**pod**: hexapod-mjx-train-8

**steps**: 40000000

**parent**: cw-walkscratch-easy0905-headset-halfgrav-fullhead-widen2-c2b

**wandb_id**: 5vqxgqjm

**hypothesis**: Plain English: widen2-c1 and widen2-c2b (2 independent seeds, matched 40M-champion provenance) both showed that widening the halfgrav heading champion's command set from the passing 5-way to the full 8-way compass (adding reversals) keeps the gait valid and tightens reversal-heading tracking, closing the champion-specific-luck alternative. This is the 2nd-seed acquisition-scale (40M) confirmation, run in parallel with widen2-c1-acq1, to build the n=2 acquisition-scale evidence this campaign's own pattern (base/halfgrav heading rungs) requires before calling the widen-from-medhead curriculum shape validated.

**gate**: ACQ PASS if gait_valid stays majority (>=18/24) with 0 falls AND direction_err/course_err at the reversal headings continues to tighten vs this run's own 2M canary read (direrr 62.0, courserr 63.6, slip 4.94) rather than re-widening back toward the confounded widen2-c2's failure range (89/130/124). ACQ FAIL if gait_valid drops into minority or a leg is chronically sacrificed. ACQ CONTINUE if reward is still climbing and gait stays valid but course-tracking is still improving/ambiguous at 40M. Read together with widen2-c1-acq1: if both PASS, the widen-from-medhead recipe is validated at acquisition scale for this ladder.

**verdict**: The 2nd matched-budget seed of the widen-from-medhead-to-full-8-way recipe ENTRENCHES a chronic leg-1 park at 40M, regressing from its own 2M canary (16/24 gait_valid CANARY PASS). Evidence: harness gait_valid drops to 14/24 (walk/det 3/6, walk/sto 6/6, walk_startjitter/det 2/6, walk_startjitter/sto 3/6), well under the run's own pre-registered >=18/24 PASS bar, 0 falls. Leg-1 duty_cycle is low (0.01-0.21, median ~0.11) in ALL 24 episodes and formally flagged sacrificed in 10/24 (sometimes joined by legs 0/3/4 -- one det/walk episode collapses to FOUR sacrificed legs [0,1,3,4] simultaneously, slip_per_m 5.18-8.05 in that cluster). Frame strips (walk_det_4, walk_startjitter_det_2) show the robot mostly rotating/skating in place during the worst episodes rather than translating -- matches the numeric slip signature (up to 128/m in sto mode), not a healthy gait. Why: this is exactly the disqualifying condition the run's own gate names verbatim ("ACQ FAIL if gait_valid drops into minority or a leg is chronically sacrificed") -- both conditions independently true. ep_rew_mean quarters dip then partially recover ([-1283,-1997,-1858,-1720], not net-rising), so this is not the 08-21 continue-on-rising-reward case; the harness fully corroborates a real behavioral regression, not reward/eval misalignment. What's next: this seed shows the widen-from-medhead recipe is NOT uniformly robust at 40M -- its matched sibling widen2-c1-acq1 (verdicted separately this cycle) PASSES the identical recipe cleanly. Read as n=1-of-2 FAIL at acquisition scale: the curriculum-widen step is real (both seeds' 2M canaries PASSed) but does not reliably survive a further 40M of training without a per-leg-utilization safeguard -- this is the SAME base(1g)-family leg-1/4 chronic-sacrifice fingerprint (CURRENT_TRUTHS structural diagnostic: L1/L4 are the hexagon's redundant middle pair) now appearing on a halfgrav(0.5g) seed for the first time, so the gravity-linked-robustness-gap hypothesis needs revisiting -- halfgrav is not immune, just less prone. Do not spend further budget respec'ing this exact checkpoint; if the widen2 rung needs a 3rd seed to break the 1/1 tie, launch a fresh seed rather than continuing this one.

