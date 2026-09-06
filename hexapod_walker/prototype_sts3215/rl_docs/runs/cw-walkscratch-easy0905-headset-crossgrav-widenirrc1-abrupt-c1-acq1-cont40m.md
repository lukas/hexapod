# cw-walkscratch-easy0905-headset-crossgrav-widenirrc1-abrupt-c1-acq1-cont40m

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: PASS

**created**: 2026-09-06T03:53:35+00:00

**pod**: hexapod-mjx-train-1

**steps**: 40000000

**parent**: cw-walkscratch-easy0905-headset-crossgrav-widenirrc1-abrupt-c1-acq1

**wandb_id**: 1us3k6k1

**hypothesis**: Plain English: same endurance question as the medhead/widen2c1 cont40m siblings, run on the CLEANEST crossgrav ACQ result so far (widenirrc1-abrupt-c1-acq1: 22/24 gait_valid, 0 falls, zero slip outliers across all 4 modes) -- the widen-then-irr composite recipe. If even the cleanest champion entrenches given another 40M 1g steps, that strengthens the universal-slow-clock reading; if it holds clean, entrenchment risk correlates with recipe cleanliness, not just crossgrav-transfer per se.

**gate**: HARDENING/endurance continuation (+40M, own checkpoint, no cfg change). PASS/HOLDS if gait_valid stays majority (>=4/6) in walk/det AND walk/sto with slip_per_m staying tightly banded (no new outlier class) and no NEW chronic leg beyond this checkpoint's own established 40M read (22/24, sac=[] every clean mode). FAIL/ENTRENCHES if a leg[1,4]-pattern chronic sacrifice newly emerges -- a 3rd recipe confirming the universal-entrenchment reading.

**verdict**: PASS/HOLDS -- 2nd +40M endurance helping (80M cumulative 1g) on the widenirr-then-crossgrav lineage reproduces a clean read, no new entrenchment. Aggregate gait_valid 24/24 -- walk/det 6/6, walk/sto 6/6, walk_startjitter/det 6/6, walk_startjitter/sto 6/6, ALL sac=[] (zero flagged episodes anywhere, an improvement over even the campaign's cleanest sources' single-transient-dip pattern). slip_per_m tightly banded 3.3-5.4 across every panel (no outlier class), close to the 2.9 teacher band. 0 falls/terminations in all 24 episodes. Reward rising every quarter (432/860/987/1092), consistent with the 08-21 ruling and this run's own PASS/HOLDS gate. Video contact sheet confirms genuine six-leg forward cycling with clear body translation. Extends the campaign's endurance finding (cleanliness margin, not budget, predicts outcome): this source was already clean at its first 40M read and stays clean (in fact improves to a perfect 24/24) at 80M cumulative, joining s1acq and medhead as sources that tolerate a 2nd endurance helping.

