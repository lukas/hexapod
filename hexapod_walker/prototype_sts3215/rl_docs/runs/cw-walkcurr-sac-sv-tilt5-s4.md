# cw-walkcurr-sac-sv-tilt5-s4

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: REFUSED

**created**: 2026-08-30T04:34:27+00:00

**pod**: hexapod-mjx-train-10

**steps**: 20000000

**parent**: cw-walkcurr-sac-sv-tilt5-s1

**hypothesis**: Plain English: is tilt5-s1's partial stepping signal (5/6 gait_valid, 0.055m fwd median, still falls 24/24) a real property of the SAC+anti-tilt(k_roll=k_pitch=5.0) diet, or a seed lottery draw the way the concurrent decleg population sweep is testing for PPO? Operator-ordered overnight population sweep (same MCP order as the b20m/s2/s3 continuations and the decleg/central 100M PPO wave) -- fresh seed 4, byte-identical tilt5 diet/algo/budget (20M, matching the siblings) otherwise. WALKCURR_SV_TILT bank already green for this dose (6/6, shared by construction with tilt5-s1). Prediction-if-true (diet-driven): this seed matches or beats tilt5-s1's own numbers (gait_valid>=4/6, fwd med approaching/clearing 0.06m) by 20M. Prediction-if-false (seed-lottery only): stays pinned at or below the untreated sac-sv-s1 baseline (24/24 falls, fwd ~0.02-0.05m, gait_valid low) -- narrows the read toward 'tilt5-s1 got lucky', echoing whatever the decleg wave's own s3-s6 arms find for PPO.

**gate**: Rung-1 C-env det+sto fixed-forward panel (n>=6 each) at 20M: PASS needs progress_ratio med>=0.35, slip/m<=3.0, gait_valid>=4/6, falls (tilt_pitch/tilt_roll term) on <=1/6 det episodes. PARTIAL/continue (08-21 ruling): fall rate or forward_dist improving vs the untreated sac-sv-s1 baseline (24/24 falls, fwd ~0.02-0.05m) even short of the full bar. FAIL: pinned at or below the untreated s1 baseline with flat reward -- read jointly with s2/s3/b20m siblings to settle diet-vs-seed.

**refused_reason**: hexapod-mjx-train-10 already runs cw-walkcurr-sac-sv-tilt5-s4 — GPU pods host exactly one run; pick a free GPU pod.

