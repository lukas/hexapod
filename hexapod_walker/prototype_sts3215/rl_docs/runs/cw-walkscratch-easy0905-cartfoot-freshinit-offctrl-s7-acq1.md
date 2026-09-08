# cw-walkscratch-easy0905-cartfoot-freshinit-offctrl-s7-acq1

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: PASS

**created**: 2026-09-08T06:52:55+00:00

**pod**: hexapod-mjx-train-3

**steps**: 40000000

**parent**: cw-walkscratch-easy0905-cartfoot-freshinit-offctrl-s7

**wandb_id**: 0mribzhl

**hypothesis**: Plain English: matched joint-space control for cartfoot-freshinit-c1-s7-acq1 -- same fresh-init recipe, seed, and 40M budget, no cart_foot keys. Own-checkpoint 40M continuation of the HEALTHY-PARITY CANARY-PASSed OFF arm, giving a same-depth same-seed slip/m and gait_valid comparator for the ON arm launched this cycle (avoids reusing the mature cont40m offctrl-s3 comparator, which reached maturity via a long continuation chain, not fresh-init).

**gate**: ACQUISITION: >=0.03 m/s median net forward in >=1 of walk/det,sto (0 falls in det). Read together with cartfoot-freshinit-c1-s7-acq1: this is the joint-space baseline, expected to reach the campaign's established 5-6/m slip band.

**verdict**: Matched fresh-init joint-space control finishes the full 40M fork(b) acquisition budget clean, confirming this cycle's paired ON read is valid. 0 falls/terminations in 24/24 episodes across all 4 groups; gait_valid 6/6 in walk/det, walk/sto, walk_startjitter/sto, but a genuine weak point under walk_startjitter/det: only 1/6 gait_valid, leg 4 sacrificed in 5/6 episodes (one ep also sacrifices leg 1). Mean slip/m by group 2.83/3.41/2.85/3.26, speed_mean_m_s 0.195/0.175/0.191/0.183 -- all comfortably above the >=0.03 m/s gate floor. Reward quarters rise monotonically -376.8->835.0->1580.9->1888.3, consistent with real learning, not a plateau. This confirms the joint-space control itself is healthy at this fresh-init depth (not the source of any ON/OFF gap) and flags the startjitter/det leg-4 fragility as a real, track-relevant weak point independent of the cart-foot question. Read together with cartfoot-freshinit-c1-s7-acq1 (verdicted same cycle).

