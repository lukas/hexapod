# cw-walkcurr-sac-sv-tilt5-s3

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: FAIL

**created**: 2026-08-30T04:29:57+00:00

**pod**: hexapod-mjx-train-9

**steps**: 20000000

**parent**: cw-walkcurr-sac-sv-tilt5-s1

**wandb_id**: e92fmjow

**hypothesis**: Plain English: is tilt5-s1's partial stepping signal (5/6 gait_valid, 0.055m fwd median, still falls 24/24) a real property of the SAC+anti-tilt(k_roll=k_pitch=5.0) diet, or a seed lottery draw the way the concurrent decleg population sweep is testing for PPO? Operator-ordered overnight population sweep (same MCP order as the b20m/s2 continuations and the decleg/central 100M PPO wave) -- fresh seed 3, byte-identical tilt5 diet/algo/budget (20M, matching the b20m/s2 siblings) otherwise. WALKCURR_SV_TILT bank already green for this dose (6/6, shared by construction with tilt5-s1). Prediction-if-true (diet-driven): this seed matches or beats tilt5-s1's own numbers (gait_valid>=4/6, fwd med approaching/clearing 0.06m) by 20M. Prediction-if-false (seed-lottery only): stays pinned at or below the untreated sac-sv-s1 baseline (24/24 falls, fwd ~0.02-0.05m, gait_valid low) -- narrows the read toward 'tilt5-s1 got lucky', echoing whatever the decleg wave's own s3-s6 arms find for PPO.

**gate**: Rung-1 C-env det+sto fixed-forward panel (n>=6 each) at 20M: PASS needs progress_ratio med>=0.35, slip/m<=3.0, gait_valid>=4/6, falls (tilt_pitch/tilt_roll term) on <=1/6 det episodes. PARTIAL/continue (08-21 ruling): fall rate or forward_dist improving vs the untreated sac-sv-s1 baseline (24/24 falls, fwd ~0.02-0.05m) even short of the full bar. FAIL: pinned at or below the untreated s1 baseline with flat reward -- read jointly with s2/s4/b20m siblings to settle diet-vs-seed.

**verdict**: FAIL, confirms 4/4 tilt5-20M FAIL. DR-0 gate n=24 across all 4 sub-panels: gait_valid 0/6 EVERYWHERE, 24/24 falls (mostly TERM over_current), 2-3 legs flagged 'sacrificed' in nearly every episode. progress_ratio med clears 0.35 on all 4 sub-panels (0.84-1.99) and fwd med 0.10-0.12m -- looked like the partial escape the wave was funded to find, but frame strips (walk_det_0, contact_sheet) show why: the robot stands briefly, then progressively tips over sideways and by frame ~9/12 is lying on its side with splayed/sacrificed legs, SLIDING across the floor rather than cycling stance/swing -- the track's own known 'dragging inflates progress_ratio without a real gait' artifact, now confirmed on video, not inferred. Reward flat (quarters 145.7/150.2/149.8/150.4, no rising trend) -- not an 08-21 continue case. Tally: s1-b20m FAIL, s2 FAIL, s3 FAIL (this), s4 FAIL = SAC tilt5 20M continuation wave now 4/4 FAIL, all convergent on the identical 24/24-fall/flat-reward/zero-valid-gait signature (s3's only difference is a cosmetic drag-inflated progress_ratio, not a real gait). Per STATUS's pre-committed step, this closes lever (iv) (off-policy SAC) and with it every operator-named lever (i-iv) plus every self-invented fork this campaign built -- walkcurr rung-1 is now blocked at the from-scratch MLP/decleg PPO-and-SAC architecture+budget this campaign could fund and test. Filing the fresh operator note now (two remaining honest options: new mechanism idea from operator, or explicit scope ruling to park rung-1 while effort concentrates on standwalk/other tracks).

