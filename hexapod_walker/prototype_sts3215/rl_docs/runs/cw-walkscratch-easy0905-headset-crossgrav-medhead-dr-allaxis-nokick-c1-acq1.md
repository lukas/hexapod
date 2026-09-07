# cw-walkscratch-easy0905-headset-crossgrav-medhead-dr-allaxis-nokick-c1-acq1

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: ACQ_FAIL

**created**: 2026-09-06T10:55:24+00:00

**pod**: hexapod-mjx-train-2

**steps**: 40000000

**parent**: cw-walkscratch-easy0905-headset-crossgrav-medhead-dr-allaxis-nokick-c1

**wandb_id**: fvj0g1kr

**hypothesis**: Plain English: does the full ~30-axis realism composite, with kick fully disabled (the one axis proven to break it) and the 3x torque crutch still on, hold up at real acquisition budget (40M), not just a 2M canary -- this is QUEUE AIM item (1)'s composite-ACQ funding step, licensed by this exact recipe's own canary PASS (19/24 gv, 0 falls). Single lever vs the canary: budget 2M->40M, otherwise byte-identical (dr.walk_kick_prob=0.0, all other ~28 DR axes at full medhead-dr dose, torque_scale=3.0 crutch on).

**gate**: ACQ gate (40M): aggregate gait_valid majority (>=18/24) sustained at ACQ scale (matching or improving the 19/24 canary), 0 falls/terminations, no NEW chronic single-leg sacrifice (the canary's flagged sto legs varied episode-to-episode, not one leg every time). PASS -> full composite realism (item 1) is closed FOR REAL at acquisition scale, contingent only on the still-open no-crutch bisection (allaxiskickhalf-nocrutch1x-c1) for the crutch-removal question. FAIL/entrenches -> the composite needs more than kick-removal alone; audit which of the other ~28 axes destabilizes under sustained training even though each passed solo.

**verdict**: Closing a fork that's sat unverdicted since 09-06 ~12:2x (item(1)'s full-30-axis-realism-composite-with-crutch question): this 40M ACQ continuation FAILS its own pre-registered 0-falls bar -- 2/24 episodes terminate via tilt_roll (roll_class=fell, peak 30.8deg walk/det ep1, 34.2deg walk_startjitter/sto ep4), and in BOTH cases the frame strip shows a clean 4-frame walking gait, then a push-perturbation marker, then the robot rolling onto its side over the next 1-2 frames -- a genuine push-recovery failure, not a spontaneous walking collapse (gait_valid actually IMPROVED to 23/24 vs the 2M canary's 19/24; the one non-fall gait_valid flag is a single sacrificed-leg episode, sac=[3], not a fall). Roll levels run elevated (14-28deg 'leaning') in nearly every episode, fall or not -- this composite runs close to its stability edge generically, the 2 falls are the tail of a continuum, not a fluke. Combined with the already-recorded 09-06 14:4x finding that this SAME recipe's fresh seeds (-s1 seed3, -s2 seed4) BOTH fail with tilt_roll falls even at their own 2M canary (worse than this seed, which only failed once trained to 40M) -- this is now 3/3 seeds showing the identical push-triggered tilt_roll fingerprint, a recipe-level attractor, not seed noise. VERDICT: ACQ FAIL - PUSH-RECOVERY FRAGILE. This formally closes 'kick-removal-alone' as a sufficient recipe for the full ~30-axis realism composite with the torque crutch (dr.torque_scale=3x) still on -- kick was A broken ingredient, not the ONLY one. Per this same finding's own already-recorded recommendation (09-06 14:4x), retreats from 'keep spending ACQ budget on this exact recipe' to bisecting the remaining axes. This cycle acted on that recommendation directly: launched a single-lever crutch-isolation pair (cw-walkscratch-easy0905-headset-crossgrav-medhead-dr-allaxis-nokick-crutchoff-{s1,s2}, torque_scale 3->1 only, same seeds/init-from/kick=0/push=0.3 as the already-failed -s1/-s2 canaries) to test whether the crutch itself is the destabilizing factor under push, since the one known-clean full-realism composite (allaxiskickhalf-nocrutch1x-c1) differs on BOTH torque_scale AND kick dose at once and never isolated which axis matters. Both finished their 2M canary already; gate evals kicked+registered via evalpending, unverdicted for the next reader.

