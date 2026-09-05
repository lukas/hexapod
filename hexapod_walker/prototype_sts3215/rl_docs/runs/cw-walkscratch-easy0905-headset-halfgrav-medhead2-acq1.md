# cw-walkscratch-easy0905-headset-halfgrav-medhead2-acq1

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: CONTINUE

**created**: 2026-09-05T19:18:24+00:00

**pod**: hexapod-mjx-train-3

**steps**: 40000000

**parent**: cw-walkscratch-easy0905-headset-halfgrav-medhead2-c1

**wandb_id**: xa9a26bm

**hypothesis**: Second-seed medium-heading (5-way, 0/+-45/+-90deg) acquisition on the halfgrav(0.5g) family: headset-halfgrav-medhead2-c1's own 2M canary already CANARY PASSED cleanly (24/24 harness gait_valid, zero sacrificed legs, slip near the teacher band), warm-started from a DIFFERENT halfgrav champion (headset-halfgrav-s3acq) than the first-seed acq1 continuation (which used medhead-c1, warm-started from halfgrav-acq1). This gives it the full 40M budget to confirm the medium-heading rung acquires cleanly from a second independent seed, mirroring headset-halfgrav-medhead-acq1's template exactly.

**gate**: ACQUISITION (40M): PASS if held-out walk/det + walk_startjitter/det harness gait_valid majority (>=4/6 each) with no chronically-parked leg (duty>=0.10 on all six) across the 5-way heading set, slip_per_m staying near the 2.9 teacher band, zero falls. CONTINUE if gait_valid is marginal but reward/v_along keep climbing without collapse (08-21). FAIL if a leg re-sacrifices majority-of-episodes or course-tracking degrades toward the far/reversal headings the same way the bare 8-way fullhead jump did. PASS (2nd seed) closes the medium-heading rung's acquisition-scale seed-robustness confirmation at n=2 on the halfgrav family.

**verdict**: 5-way medium-heading 40M continuation on the halfgrav(0.5g) 2nd seed reads MARGINAL, not FAIL: walk/det 4/6 gait_valid meets the gate's own >=4/6 bar, but walk_startjitter/det only 2/6 (misses per-mode bar); walk/sto 5/6, walk_startjitter/sto 5/6 -- 16/24 total. Crucially this is NOT the base family's hard-park pathology: flagged legs' duty_cycle in the failing episodes reads 0.06-0.11 (borderline, matches the FIRST seed's own accepted-as-PASS 0.08-0.09 borderline duty), never the base family's chronic 0.0-0.02, and which leg gets flagged varies across episodes (2,1,[1,4],[1,4]) rather than one leg parked every time. 0/24 falls, slip 1.8-4.0 med mostly at/near the 2.9 band, fwd speed fine (2.83-3.05m/20s med). Reward is genuinely still climbing, not plateaued: quarters -401,-419,-183,+30, and the raw ep_rew_mean history shows a real (noisy) upward trend concentrated in the last ~10M steps (last 5 logged points: -9,101,-24,69,15,95,120,241,135 -- noisy but net higher than the -400s of the first half); env/v_along_cmd_m_s stable ~0.10-0.117 throughout, no collapse. This matches the gate's own explicit clause ('CONTINUE if gait_valid is marginal but reward/v_along keep climbing without collapse') rather than the base family's flat-entrenched failure -- also the halfgrav family is the one that has cleared every other rung this campaign (irr-timing, first-seed medhead) where base hasn't, so a 2nd marginal seed here reads as needing more budget, not a structural close. Next: respec-continue this checkpoint another 40M before re-judging the medhead rung's halfgrav seed-count.

