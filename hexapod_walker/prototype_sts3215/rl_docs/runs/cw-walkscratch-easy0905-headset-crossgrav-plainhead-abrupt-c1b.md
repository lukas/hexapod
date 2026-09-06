# cw-walkscratch-easy0905-headset-crossgrav-plainhead-abrupt-c1b

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: PASS

**created**: 2026-09-06T02:18:04+00:00

**pod**: hexapod-mjx-train-1

**steps**: 2000000

**parent**: cw-walkscratch-easy0905-headset-halfgrav-acq1

**wandb_id**: 59h70mm0

**hypothesis**: Plain English: headset-halfgrav-acq1 (the plain 3-way 0/+-45deg heading champion, the base lineage every medhead/widen2/irr/composite champion descends from) is the CLEANEST champion in the whole halfgrav roster (gait_valid 24/24 -- 6/6 in all 4 modes, no sacrificed leg ever) but has never itself been tested for cross-gravity-transfer -- only its descendants (medhead, widen2c1, irr, irrwiden, widenirr) were. Since the composite irrwiden-c1-acq1 (this cycle's own CANARY FAIL) just showed transfer degradation CAN happen even from a clean 0.5g parent, does the campaign's cleanest, simplest reference champion transfer cleanly to abrupt 1g, or does it also degrade -- giving the sweep its missing baseline/simplest-case data point?

**gate**: DISCOVERY (2M), abrupt 1g jump from the cleanest (24/24) halfgrav champion. PASS/INFORMATIVE-POSITIVE if gait_valid stays majority (>=4/6) in walk/det with no chronic single-leg sacrifice -- extends cross-gravity-transfer confirmation to the simplest possible recipe, the natural baseline the rest of the sweep has been implicitly assuming. FAIL/INFORMATIVE-NEGATIVE if walk/det collapses to minority -- would mean even the cleanest, simplest champion isn't immune, undermining the working theory that transfer difficulty tracks recipe complexity (composite vs simple) rather than being uniformly fragile.

**verdict**: CANARY PASS - INFORMATIVE-POSITIVE (crossgrav sweep's simplest-baseline test). The cleanest 3-way (0,+-45deg) halfgrav champion (headset-halfgrav-acq1, 24/24, never sacrificed a leg) survives an abrupt 0.5g->1.0g jump just as cleanly as every composite descendant tested this campaign: gait_valid 23/24 (walk/det 6/6, walk/sto 6/6, walk_startjitter/det 5/6 with ONE isolated single-episode leg-4 flag not chronic, walk_startjitter/sto 6/6), 0 falls/terminations in all 24 episodes, slip_per_m tightly banded 2.8-4.8. Reward quarters climb cleanly 39.5->79.6->116.8->148.0 (healthy, matches the shape of every other PASSing crossgrav canary). Video (walk_det_0, 8-frame strip) shows genuine six-leg alternating-contact cycling with clear checkerboard-floor body translation across the strip -- textbook clean gait, no pathology. This closes the sweep's missing simplest-case baseline: even the plain, never-composited champion is NOT immune to a real transfer degradation risk being present in principle (as irrwidenc1 showed for a composite), but here it simply transfers cleanly, reinforcing the working theory that transfer difficulty tracks recipe complexity rather than being uniform. Own launch-bug note already recorded in STATUS (KILLED_LAUNCH_BUG on the -abrupt-c1 attempt; this -c1b relaunch used the correct explicit --init-from). Next: matched 40M ACQ continuation (queued this cycle).

