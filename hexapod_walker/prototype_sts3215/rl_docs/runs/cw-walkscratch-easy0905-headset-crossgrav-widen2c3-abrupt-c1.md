# cw-walkscratch-easy0905-headset-crossgrav-widen2c3-abrupt-c1

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: FAIL

**created**: 2026-09-06T02:22:56+00:00

**pod**: hexapod-mjx-train-0

**steps**: 2000000

**parent**: cw-walkscratch-easy0905-headset-crossgrav-widen2c1-abrupt-c1

**wandb_id**: jlal69m5

**hypothesis**: Plain English: cross-gravity-transfer (halfgrav 0.5g champion warm-started and abruptly jumped to full 1g from tick 0) has now been CONFIRMED for the widen2 recipe on seed 1 (widen2c1-abrupt-c1 CANARY PASS 19/24) plus 4 other distinct recipes (medhead x2, irracq1, widenirr, irrwiden). widen2-c3-acq1 (the just-PASSed 3rd, independently-seeded widen2 champion, gait_valid 20/24 at 40M) has never been cross-gravity-tested. This is the n=2-seed confirmation for the widen2 RECIPE's own crossgrav-transfer specifically (distinct from the irr/composite axes already n=2-confirmed elsewhere): does a 2nd healthy widen2 seed transfer as cleanly as widen2-c1 did, closing the widen2-crossgrav generality the same way irr-timing already closed its own (irr-acq1 + irr2-acq1, 2/2 PASS)?

**gate**: MECHANISM-HEALTH CANARY ONLY: do not judge skill acquisition, close a behavior/reward class, or require mature gait at this checkpoint. PASS/INFORMATIVE-POSITIVE if gait_valid stays majority (>=4/6) in walk/det with no chronic (<0.10 duty every episode) single-leg sacrifice -- extends cross-gravity-transfer to a 2nd independent widen2 seed, closing the widen2-recipe crossgrav question with n=2. FAIL/INFORMATIVE-NEGATIVE if it collapses into the base(1g) leg-1/4 chronic-sacrifice entrenchment fingerprint (same discriminator used throughout this campaign: startjitter panel + per-leg duty, not walk/det alone).

**verdict**: CANARY FAIL - MECHANISM. 2nd independent widen2 seed's abrupt 0.5g->1.0g crossgrav transfer collapses into the campaign's already-characterized leg-1/4 chronic-sacrifice entrenchment fingerprint (CURRENT_TRUTHS base(1g) structural attractor) under the startjitter panel: walk/det 5/6 clean but walk_startjitter/det collapses to 3/6 with legs 1 and 4 recurring across 3 of the 4 flagged episodes (sac=[0,3],[1],[1,4],[4]) plus one flagged walk_startjitter/sto episode (sac=[4]) -- this is the exact discriminator the gate pre-registered (startjitter panel + per-leg duty, not walk/det alone). Video (walk_startjitter_det_3, 8-frame strip) confirms: floor checkerboard barely shifts across the strip despite legs visibly cycling -- genuine low-net-progress/high-slip pathology, not a video artifact (prog 0.80 vs plainhead-sibling's prog ~2.6 at the same budget). Slip/m explodes in walk/sto and startjitter (up to 201.9). Reward trend alone is NOT diagnostic here: checked against sibling widen2c1-abrupt-c1 (PASSed) which shows the same qualitative decline shape (-53->-229) at a milder magnitude than this run's -57.7->-299.1 -- the composite's reward config is inherently negative/declining regardless of pass/fail, so the FAIL call rests on the behavioral eval (gait_valid collapse + fingerprint match), not the reward curve. This closes the widen2-crossgrav n=2-seed question with a SPLIT result (c1 PASS / c3 FAIL): unlike the widen2 own-gravity family (3/3 clean seeds PASS at acquisition), the widen2-crossgrav-transfer recipe is seed-sensitive -- unlike irr-timing crossgrav (2/2 PASS) and the healthy-source-champion crossgrav set (6/6 PASS), widen2's abrupt-transfer robustness does not fully generalize past its first lucky seed. No further widen2-crossgrav arms planned; narrows crossgrav-transfer robustness claims to exclude widen2 as a uniformly-safe composite axis.

