# cw-walkscratch-easy0905-headset-crossgrav-s3acq-abrupt-c1

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: CANARY_PASS

**created**: 2026-09-06T01:50:13+00:00

**pod**: hexapod-mjx-train-9

**steps**: 2000000

**parent**: cw-walkscratch-easy0905-headset-halfgrav-s3acq

**wandb_id**: yodax2qa

**hypothesis**: Plain English: extends the cross-gravity-transfer test to the 2nd of the halfgrav heading-family n=3 confirmation set's clean champions, headset-halfgrav-s3acq (gait_valid 22/24, 0 falls, active leg-1 micro-underuse not chronic parking). Does this 2nd distinct clean champion (different seed/lineage from s1acq, medhead, widen2c1, irracq1, widenirrc1) also survive an abrupt jump to full 1g? Trained on the same 3-way heading set (0,+/-45deg) as s1acq, matched here exactly. Warm-starts from s3acq, which has never seen 1g.

**gate**: PASS/INFORMATIVE-POSITIVE if gait_valid stays majority (>=4/6) in walk/det with no chronic (<0.10 duty every episode) single-leg sacrifice -- a 6th independent confirmation of cross-gravity-transfer as a general repair path (not one lucky champion). FAIL/INFORMATIVE-NEGATIVE if it collapses to a chronic single-leg-sacrifice fingerprint -- narrows the finding to a subset of leg-healthy sources. Either outcome is informative; do not require a mature 40M-grade gait at 2M.

**verdict**: Cross-gravity-transfer holds on the campaign's 2nd-best 3-way halfgrav champion (headset-halfgrav-s3acq, gait_valid 22/24 at native 0.5g) jumped abruptly to 1g -- 6th independent confirmation of the repair. Evidence: gait_valid 21/24 -- walk/det (primary mode) 6/6 clean sac=[], walk/sto 6/6 clean, walk_startjitter/sto 6/6 clean; walk_startjitter/det softens to 3/6 with leg-1 flagged in 3 episodes (duty 0.07-0.10), but NOT chronic -- the other 3 startjitter/det episodes show the same leg at healthy duty 0.14-0.24, and leg-1 duty never drops near-zero. This is the exact same mild jitter-sensitivity shape already logged on every other healthy-source crossgrav sibling (medhead/widen2c1/irracq1/widenirrc1), not a new pathology. 0 falls/terminations in all 24 episodes. slip_per_m 2.8-4.3 (medians 3.1-3.7), forward distance 2.6-4.2m/20s. Video (walk_det_0) shows genuine six-leg cycling with clear body translation. Why: matches the gate's own PASS/INFORMATIVE-POSITIVE branch (majority gait_valid in walk/det, no chronic sacrifice) -- the campaign's healthy-source crossgrav pattern is now 6/6 confirmations with zero surprises. Next: matched 40M ACQ continuation.

