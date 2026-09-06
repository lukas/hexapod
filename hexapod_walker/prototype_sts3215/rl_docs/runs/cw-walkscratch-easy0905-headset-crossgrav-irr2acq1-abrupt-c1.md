# cw-walkscratch-easy0905-headset-crossgrav-irr2acq1-abrupt-c1

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: CANARY PASS - INFORMATIVE-POSITIVE

**created**: 2026-09-06T01:44:00+00:00

**pod**: hexapod-mjx-train-3

**steps**: 2000000

**parent**: headset-halfgrav-irr2-acq1

**wandb_id**: 2vlneqky

**hypothesis**: Plain English: this cycle's crossgrav-irracq1 canary showed the FIRST irr-timing-jitter seed (halfgrav-irr-acq1) survives an abrupt jump to full 1g cleanly. Does the SAME recipe's 2nd seed (halfgrav-irr2-acq1, a distinct champion ACQ PASS at 40M, gait_valid 19/24) survive the identical abrupt gravity_scale 0.5->1.0 jump, or was the first seed's clean transfer a per-seed fluke? This gives the irr-timing crossgrav finding its own n=2 seed confirmation, matching the seed-robustness discipline already applied to every other rung in this campaign (widen2-c1/c2b/c3, irr-c1/c2, irrwiden-c1/c2).

**gate**: PASS/INFORMATIVE-POSITIVE if gait_valid stays majority (>=4/6) in walk/det with no chronic single-leg sacrifice -- confirms cross-gravity-transfer is seed-general for the irr-timing recipe, not a single-seed fluke. FAIL/INFORMATIVE-NEGATIVE if it collapses to the leg[1,4] chronic-sacrifice fingerprint -- would mean seed variance, not recipe, drives transfer success. Either outcome is informative; do not require a mature 40M-grade gait at 2M.

**verdict**: Plain English: does the irr-timing-jitter crossgrav recipe's SECOND independent seed (halfgrav-irr2-acq1, a distinct 40M champion, gait_valid 19/24 at native 0.5g) also survive an abrupt jump to full 1g, or was the first seed's clean transfer (irracq1-abrupt-c1, already PASS) a fluke? Evidence: 2M canary, aggregate gait_valid 22/24 (walk/det 6/6 sac=[], walk/sto 6/6 sac=[], walk_startjitter/det 4/6 with only 2 ISOLATED single-episode leg flags [4] then [1] -- never the same leg twice, not chronic -- walk_startjitter/sto 6/6 sac=[]), 0 falls/terminations in all 24 episodes, slip_per_m tightly banded 3.34-4.71 (matches the crossgrav family's band), walk_det_0 frame strip shows genuine six-leg alternating-contact cycling with clear body translation. Why: this is the gate's own pre-registered PASS/INFORMATIVE-POSITIVE branch (majority-or-better gait_valid in walk/det, no chronic single-leg sacrifice) -- irr-timing crossgrav transfer is now confirmed on its 2nd independent seed, matching the n=2 discipline already closed for the widen2 and other rungs in this campaign; per-seed luck is ruled out as the explanation for the irr-timing recipe's transfer success. What's next: matched 40M ACQ continuation launched this cycle (headset-crossgrav-irr2acq1-abrupt-c1-acq1, train-3) to confirm at full acquisition scale, same template as the sibling irracq1-abrupt-c1-acq1 continuation.

