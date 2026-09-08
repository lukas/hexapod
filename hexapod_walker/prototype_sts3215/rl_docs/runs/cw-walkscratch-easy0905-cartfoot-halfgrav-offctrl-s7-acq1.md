# cw-walkscratch-easy0905-cartfoot-halfgrav-offctrl-s7-acq1

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: ACQ PASS

**created**: 2026-09-08T09:04:06+00:00

**pod**: hexapod-mjx-train-1

**steps**: 40000000

**parent**: cw-walkscratch-easy0905-cartfoot-halfgrav-offctrl-s7

**wandb_id**: 1myxq3am

**hypothesis**: Plain English: matched joint-space control for the halfgrav cart_foot 40M acquisition (cw-walkscratch-easy0905-cartfoot-halfgrav-s7-acq1, ON, already running): does the joint-space action space learn to walk at 0.5g over a full budget, and how does its slip compare to the cart_foot sibling at the SAME fresh-init depth? Own-checkpoint 40M continuation of the CANARY-PASSed offctrl-s7 OFF arm. Mirrors the already-answered 1g fork(b) pair (cartfoot-freshinit-offctrl-s7-acq1) on the other validated gravity cell of the base/halfgrav x joint/cartfoot 2x2 matrix.

**gate**: ACQUISITION: >=0.03 m/s median net forward in >=1 of walk/det,sto (0 falls in det), read together with cartfoot-halfgrav-s7-acq1 (ON) at the SAME budget. PASS/CONTINUE per the 08-21 ruling if reward is still rising; slip/m vs the matched ON sibling is the headline comparison, not a hardening bar.

**verdict**: Joint-space (OFF) halfgrav 40M acquisition closes the seed7 halfgrav pair at near-parity with the cart_foot (ON) sibling. 0 falls / 0 safety terminations in all 24 gate episodes across all 4 groups (walk/det,sto + startjitter/det,sto), speed well above the 0.03 m/s floor (fwd med 3.28m/3.14m/3.45m/3.21m over the 20s episode = ~0.16 m/s), reward quarters rise monotonically [-678.2, 232.5, 1044.7, 1346.7] and are still climbing at 40M. Slip/m vs the matched ON arm (cartfoot-halfgrav-s7-acq1, ACQ PASS, slip 1.56/1.72/1.66/1.79): OFF comes in at 1.90/1.91/1.83/1.93, i.e. ratios 1.22x/1.11x/1.10x/1.08x -- 3/4 groups comfortably inside the cohort's established ~1.2x parity band, walk/det just brushing it. Det-mode gait_valid is degraded (0/6 walk/det, sac legs [1,4] every episode; 0-2/6 startjitter/det) but this is the SAME family-wide 'det-only leg-underuse, still cycling not frozen' quirk already precedented as shared and non-blocking across this whole fresh-init cart_foot cohort (base/halfgrav, seeds 7/10/11) -- sto stays clean (5/6, 5/6). Video (walk_det_0 frame strip) shows a level body actually translating with legs still cycling, matching the eval numbers -- no new pathology, no dig-in trigger. Net: this closes the halfgrav seed7 ON/OFF pair as PARITY, mirroring the already-established 1g fork(b) result (cartfoot-freshinit-{c1,offctrl}-s7-acq1) one gravity cell over. Next: this seed7 halfgrav pair is done at 40M; the cohort's seed10/11 halfgrav extension (if launched by another cycle) would complete the n=3 practice already used at 1g.

