# cw-walkscratch-easy0905-headset-halfgrav-fullhead-widen2-c3-acq1-cont40m

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: HARDENING FAIL

**created**: 2026-09-06T10:02:23+00:00

**pod**: hexapod-mjx-train-4

**steps**: 40000000

**parent**: cw-walkscratch-easy0905-headset-halfgrav-fullhead-widen2-c3-acq1

**wandb_id**: 9wove9uj

**hypothesis**: Plain English: the 3rd tie-breaking widen2 (8-way heading) seed on 0.5g reproduced its own 2M canary structure at 40M ACQ scale (20/24 gv, 0 falls); a +40M own-checkpoint cont40m endurance continuation (80M cumulative) is the standard cleanliness-margin-predicts-endurance check already confirmed on its base/widenfwd/irrfwd siblings.

**gate**: HARDENING PASS/HOLDS if gait_valid stays majority with 0 NEW chronic single-leg pattern and 0 falls, reproducing (not worsening) the 40M flags; HARDENING FAIL if a chronic leg entrenches, falls appear, or gait_valid drops below majority.

**verdict**: HARDENING FAIL (dig-in adjudication) -- a NEW chronic leg1 low-duty pattern emerges at 80M that was absent at 40M, violating the gate's '0 NEW chronic single-leg pattern' PASS clause. Evidence: parent 40M leg1 duty never <0.10 across 24 eps; at 80M leg1 drops to 0.06-0.10 (swing 42-72) in 4 eps across 3 of 4 modes (walk/det/3 0.10, walk/det/4 0.09, startjitter/det/2 0.06, startjitter/sto/3 0.08). Same class as the s1acq-irrfwd cont40m FAIL precedent (new-mode duty ~0.06 spread) though MILDER than the base(1g) park fingerprint (0.02-0.05/swing 19-49): leg1 still cycles, mean duty over all 24 eps unchanged (0.17), so this is episode-specific sacrifice, not global weakening. Aggregate corroboration: gait_valid 20/24->18/24, fwd dist down in ALL modes (walk/det med 1.85->1.26m); mitigations: 0 falls, majority holds, parent's [0,3] flags reproduce/soften (walk/det/4 identical episode), video shows upright six-leg walking. Reward dipped then recovered (-1262->-652, rising at end): 08-21 misalignment case, but the 6-lever reward-repair grid for this exact pathology closed 09-05 -- no new repair run. Consequence: widen2-c3 joins the duration-driven leg-sacrifice list; its 40M checkpoint is usable but NOT stable past acquisition budget; retire widen2-c3 from champion/cont contention (consistent with its known crossgrav-abrupt attractor). This NARROWS, not overturns, halfgrav cleanliness: it is source-conditional (widenirr-c3 cont40m held; medhead/irrwiden lines clean); halfgrav remains preferred over base(1g), champion picks from medhead/widenirr/irrwiden sources.

