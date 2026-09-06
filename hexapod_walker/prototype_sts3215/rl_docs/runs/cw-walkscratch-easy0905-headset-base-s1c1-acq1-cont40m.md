# cw-walkscratch-easy0905-headset-base-s1c1-acq1-cont40m

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: HARDENING_FAIL

**created**: 2026-09-06T10:01:00+00:00

**pod**: hexapod-mjx-train-2

**steps**: 40000000

**parent**: cw-walkscratch-easy0905-headset-base-s1c1-acq1

**wandb_id**: skhxpa64

**hypothesis**: Plain English: the 2nd base-family (1g, no gSDE, no halfgrav) heading-set seed cleared its own 40M ACQ PASS reproducing the already-banked leg1/4 startjitter-det caveat, not a new failure; a +40M own-checkpoint cont40m endurance continuation (80M cumulative) is the standard cleanliness-margin-predicts-endurance check already confirmed on its own sibling base-family/widenfwd/irrfwd arms.

**gate**: HARDENING PASS/HOLDS if gait_valid stays majority with 0 NEW chronic single-leg pattern and 0 falls, reproducing (not worsening) the 40M leg1/4 caveat; HARDENING FAIL if a chronic leg entrenches, falls appear, or gait_valid drops below majority.

**verdict**: HARDENING FAIL: the 40M->80M own-checkpoint continuation ENTRENCHES the already-banked leg1/4 favoritism into a previously-clean flagship mode instead of holding it. Parent (40M) gait_valid 18/24 with the sacrifice confined ENTIRELY to walk_startjitter/det (0/6, leg1/4 duty 0.01-0.04); this cont40m (80M cumulative) drops to 15/24 with the SAME leg (mostly leg4, occasionally leg1) now also chronic in walk/det (3/6, duty 0.02-0.05 vs healthy legs 0.4-0.8, swing_count 19-49 vs 150-250 — genuine near-park, not borderline) and walk_startjitter/sto (3/6, previously perfect 6/6); walk_startjitter/det itself partially improved (0/6->3/6) but that's a redistribution, not a net gain (18/24->15/24 overall). Video (walk_det_0/1/2 contact sheets) shows the same leg staying planted/undercycling while the other five carry the gait. ep_rew_mean still rising every quarter (559->1047->1232->1406) -- per the 08-21 ruling this is not an automatic fail signal, but this run's OWN pre-registered HARDENING gate specifically exists to test whether the good behavior HOLDS under more budget, and its 'chronic leg entrenches' FAIL clause is squarely met regardless of reward or aggregate majority. This directly corroborates headset-base-s0c1-acq1's own DIG-IN finding (09-05 ~14:2x, same file) that one 1g-family seed already hardened this exact way at 40M while s1c1 stayed clean -- s1c1 has now ALSO hardened, just one training-length increment later, confirming the base(1g) family's leg1/4 pathology is a training-DURATION effect that eventually catches every seed given enough budget, not a seed-specific anomaly. Closes 'champion pick should use s1c1' (STATUS 09-05 ~14:2x) -- neither surviving 40M base-family seed (s0c1, s1c1) stays clean past 80M; do not select either checkpoint's cont40m as a champion, and downweight the base(1g) family generally in favor of the already-more-robust halfgrav(0.5g) sibling (clean through irr-timing/medhead/widen axes) for any downstream use. No new repair mechanism warranted -- this is confirmation of an extensively pre-established, already-closed pathology (6 reward-shaping repair levers closed 09-05), not a new open question. Next: read headset-base-acq1-cont40m (still training, the base family's 3rd and last cont40m candidate) to see if it shares this fate; if so, retire the base(1g) family's 40M+ checkpoints from champion contention entirely and standardize on halfgrav for base-gravity-family walking work.

