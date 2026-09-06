# cw-walkscratch-easy0905-headset-crossgrav-medhead-ramp-c1

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: CANARY PASS - INFORMATIVE (cross-gravity transfer confirmed)

**created**: 2026-09-05T23:46:20+00:00

**pod**: hexapod-mjx-train-0

**steps**: 2000000

**parent**: cw-walkscratch-easy0905-headset-halfgrav-medhead-acq1

**wandb_id**: zv97tks6

**hypothesis**: Plain English: matched-budget companion to crossgrav-medhead-abrupt-c1 (same cycle) -- does a GRADUAL gravity ramp (0.5g->1.0g linearly over the first 1M of a 2M continuation, using the already-built+proven sched.key=ease.gravity_scale engine, sched_value confirmed to ramp correctly in a past run cw-gait-ease1) let the leg-healthy halfgrav-medhead-acq1 champion (ACQ PASS, gait_valid 22/24, 0 falls) adapt to full gravity WITHOUT losing the six-leg gait, where an abrupt jump might shock it into the chronic leg-1/4 favoritism fingerprint that has now closed 8/8 reward-price mechanisms plus gSDE on the base(1g) family? This isolates ramp-vs-abrupt as the second half of a clean 2-arm comparison: if abrupt fails but ramp holds, gravity TRANSITION SHOCK (not 1g dynamics per se) is the causal driver, and a slower curriculum-widen-across-gravity becomes the next lever for base(1g); if both fail identically, 1g dynamics themselves force the pathology regardless of transition speed, closing cross-gravity-transfer entirely and hardening the reallocate-to-halfgrav call.

**gate**: DISCOVERY (2M), ramped-gravity arm: run the harness (walk+walk_startjitter, det+sto) with gravity having reached 1.0 by the end of training (ramp completes at 1M of this run's 2M budget, so the eval checkpoint sees full 1g). PASS/INFORMATIVE-POSITIVE if gait_valid stays majority (>=4/6) in walk/det with no chronic single-leg (<0.10 duty every episode) sacrifice -- evidence a gradual transfer curriculum reaches 1g without the pathology, license a longer ramp+40M continuation. FAIL/INFORMATIVE-NEGATIVE if gait_valid collapses to the same leg[1,4] fingerprint regardless of the gentler transition -- read together with the abrupt sibling to decide whether shock-speed or 1g-dynamics-per-se is the driver. Either outcome is informative; do not require a mature 40M-grade gait at 2M.

**verdict**: Gradual gravity ramp (0.5g->1.0g linearly over first 1M of this 2M continuation, ease.gravity_scale via sched.key engine) on the same leg-healthy halfgrav-medhead-acq1 champion also does NOT reproduce the base(1g) chronic leg-1/4 fingerprint. Harness gait_valid 21/24 (marginally better than the abrupt sibling's 20/24): walk/det 6/6 CLEAN (sac=[] every episode), walk/sto 6/6 clean, walk_startjitter/det 3/6 (same mild leg-4 softening, duty 0.07-0.15, 47-117 real swings/20s -- not chronic), walk_startjitter/sto 6/6 clean (abrupt sibling was 5/6 here). 0 falls/terminations in all 24 episodes. Video (walk_det_0 frame strip) confirms genuine six-leg cycling, body translating upright. Read together with the abrupt arm: BOTH transition speeds hold the six-leg gait at full 1g -- since neither collapsed, this cannot separate 'gravity-transition shock' from '1g dynamics force it regardless' (that would need a FAIL), but it jointly and cleanly refutes the 1g-dynamics-forces-it-regardless branch for an already leg-healthy policy, confirming cross-gravity transfer as a real, transition-speed-insensitive repair path for the base(1g) family. Per the gate's own pre-registered text this licenses a 40M acquisition continuation; launched cw-walkscratch-easy0905-headset-crossgrav-medhead-ramp-c1-acq1 same cycle (gravity fixed flat at 1.0 for the continuation, sched disabled since the ramp already completed).

