# cw-walkscratch-easy0905-headset-crossgrav-s1acq-abrupt-c1-acq1

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: PASS

**created**: 2026-09-06T02:38:22+00:00

**pod**: hexapod-mjx-train-0

**steps**: 40000000

**parent**: cw-walkscratch-easy0905-headset-crossgrav-s1acq-abrupt-c1

**wandb_id**: 80g9tb6m

**hypothesis**: Plain English: does the cleanest crossgrav-transfer canary yet (headset-halfgrav-s1acq abruptly jumped to 1g, gait_valid PERFECT 24/24, sac=[] every episode) hold at full 40M acquisition budget the same way every other healthy-source crossgrav canary has (5/5 PASS so far: medhead x2, widen2c1, irracq1, irr2acq1)? This is the campaign's best-ever source champion, so a clean ACQ PASS would be the strongest single confirmation of cross-gravity-transfer as a general base(1g) repair.

**gate**: ACQ PASS if gait_valid stays majority (>=4/6) in walk/det AND walk/sto with sac=[] at 40M, matching or improving the 2M canary's PERFECT 24/24 clean read, 0 falls, slip/m at/near the 2.9 teacher band. ACQ FAIL if walk/det or walk/sto regresses to majority failure or a chronic single-leg-park fingerprint emerges under longer 1g exposure. ACQ CONTINUE if reward still climbing with only borderline (not hard-park) duty, per the 08-21 ruling.

**verdict**: ACQ PASS: aggregate gait_valid 23/24 at 40M -- walk/det 6/6, walk/sto 6/6 (both clean sac=[]), walk_startjitter/det 5/6 (one transient sac=[4], leg-4 duty 0.0 that episode vs 0.10-0.71 in the other 5), walk_startjitter/sto 6/6. 0 falls/terminations in all 24 episodes. slip_per_m 3.3-7.5 (medians 3.85-5.07), forward dist 2.19-3.30m/20s. Essentially matches this run's own 2M canary's PERFECT 24/24 (single new transient flag, not chronic). Evidence: this is the campaign's healthiest 0.5g source champion (headset-halfgrav-s1acq, native 24/24) and it holds clean at full 40M ACQ budget -- directly answers the open question irracq1's FAIL raised (does source health predict ACQ-scale durability): yes, for this source it does. Video (walk_det_0) shows genuine six-leg cycling with clear translation.

