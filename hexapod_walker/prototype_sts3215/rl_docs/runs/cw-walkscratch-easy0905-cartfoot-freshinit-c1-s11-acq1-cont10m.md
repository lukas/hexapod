# cw-walkscratch-easy0905-cartfoot-freshinit-c1-s11-acq1-cont10m

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: ACQ_PASS

**created**: 2026-09-08T07:58:17+00:00

**pod**: hexapod-mjx-train-0

**steps**: 10000000

**parent**: cw-walkscratch-easy0905-cartfoot-freshinit-c1-s11-acq1

**wandb_id**: q25xz4pj

**hypothesis**: Does the fresh-init cart_foot ON arm's seed11 slip PARITY with its matched joint-space control (measured this cycle at 40M: ON/OFF ratio 0.94-1.00x across all 4 groups, 0 falls) HOLD or DEGRADE at 10M more steps (50M cumulative)? This is the 2nd seed to run this exact durability check (seed7's cont10m pair already in flight) -- mirrors fork(a)'s own design, which looked fine at 12M cumulative then developed new falls + 2-6x slip only after +10-20M more steps.

**gate**: ACQUISITION CONTINUATION: read together with the matched offctrl-s11-acq1-cont10m at the same budget. HOLDS = mean slip/m ratio (ON/OFF) <=1.2x in >=3/4 groups AND 0 new falls/terminations vs this run's own 40M read. DEGRADES = ratio >1.5x in >=2/4 groups OR any new fall/termination not present at 40M. Per 08-21 ruling, continue further only if reward is still rising and evals are ambiguous.

**verdict**: ACQ PASS - PARITY HOLDS (seed11 ON, 50M cumulative). 0/24 falls/terminations (same as 40M). ON/OFF slip ratio at 50M: walk/det 0.90x (2.63/2.93), walk/sto 1.02x (3.27/3.20), startjitter/det 0.92x (2.65/2.88), startjitter/sto 1.00x (3.19/3.20) -- 3/4 groups ON<=OFF, 1/4 (walk/sto) essentially breakeven at +2.2%, well inside noise and matching this seed's own 40M ratio shape (0.96/0.94/0.97/1.00x) -- NOT the 1.5-6x inflation fork(a) showed. gait_valid: walk/det stays 6/6 (unchanged from 40M), walk/sto stays 6/6, startjitter/sto stays 6/6; only startjitter/det softens 5/6->1/6 (leg4 duty drops further) -- the same precedented det-only quirk, sto (the noise-robust read) is fully unaffected. Reward rising every quarter (324.3->1910.0), no plateau. Frame strip (contact_sheet.png) shows a level body with clean six-leg cycling and real forward translation, no drag/flag-leg. CONCLUSION: seed11's fresh-init cart_foot vs joint-space slip PARITY finding HOLDS at 50M cumulative -- 2nd of 3 seeds (after seed7) to confirm durability; seed10's pair is the remaining read.

