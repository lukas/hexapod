# cw-walkscratch-easy0905-cartfoot-halfgrav-offctrl-s11-acq1

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: ACQ PASS

**created**: 2026-09-08T10:24:01+00:00

**pod**: hexapod-mjx-train-3

**steps**: 40000000

**parent**: cw-walkscratch-easy0905-cartfoot-halfgrav-offctrl-s11

**wandb_id**: i593jcsf

**hypothesis**: Matched joint-space (OFF) control for the halfgrav cart_foot seed11 40M acquisition (cw-walkscratch-easy0905-cartfoot-halfgrav-s11-acq1, ON, already launched by a concurrent cycle on train-0): does the joint-space action space learn to walk at 0.5g over a full budget at seed11, and how does its slip compare to the cart_foot sibling at the same depth? Own-checkpoint 40M continuation of the CANARY-PASSed offctrl-s11 OFF arm, completing the seed11 half of the n=3 halfgrav seed cohort (seed7 already ACQ PASS - PARITY, seed10 pair launched this cycle).

**gate**: MATCHED CONTROL: read together with cartfoot-halfgrav-s11-acq1 at the same budget. >=0.03 m/s median net forward in >=1 of walk/det,sto (0 falls in det); slip/m vs the ON sibling is the headline comparison.

**verdict**: Joint-space (OFF) halfgrav 40M acquisition closes the seed11 halfgrav ON/OFF pair, but this time near-PARITY not an ON advantage. 0 falls/0 safety terminations in all 24 gate episodes across all 4 groups, speed 0.17-0.21 m/s in every episode (>>0.03 m/s floor), reward quarters rise monotonically [-647.4, 285.0, 1066.6, 1372.1], completed naturally at 40,370,176 steps. Slip/m vs the matched ON arm (cartfoot-halfgrav-s11-acq1, ACQ PASS, slip 1.61/1.58/1.50/1.69 for det/sto/startjitter-det/startjitter-sto): OFF comes in at 1.82/1.89/1.83/1.94, ratios 1.13x/1.20x/1.22x/1.15x -- inside the cohort's established ~1.2x parity band, same as seed7's 1.08-1.22x. gait_valid: OFF 10/24 (0/6 det, 6/6 sto, 0/6 startjitter-det, 4/6 startjitter-sto) is NEAR-PARITY with ON's 11/24 (0/6, 6/6, 0/6, 5/6) -- both det panels are 100% single-leg dropout, just a DIFFERENT leg (OFF sacrifices leg4 every det episode; ON sacrifices leg1 every det episode). This does NOT reproduce seed7's headline 22/24-ON-vs-10/24-OFF gap: for seed11 the cart_foot action space gives no gait_valid advantage over joint-space, only the same ~1.15-1.2x slip edge seen in both seeds. Net: closes the seed11 halfgrav ON/OFF pair as SLIP-PARITY-WITH-GAIT-PARITY (not slip-parity-with-gait-advantage like seed7) -- the seed7 gait_valid gap does not generalize across seeds and should not be quoted as a general cart_foot-vs-joint effect. No dig-in trigger: numbers are internally consistent with the video-confirmed family-wide det-only leg-underuse quirk, no new pathology.

