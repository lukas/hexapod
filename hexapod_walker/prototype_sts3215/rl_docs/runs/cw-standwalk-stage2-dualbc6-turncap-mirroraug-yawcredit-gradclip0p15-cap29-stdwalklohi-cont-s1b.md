# cw-standwalk-stage2-dualbc6-turncap-mirroraug-yawcredit-gradclip0p15-cap29-stdwalklohi-cont-s1b

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: PASS

**created**: 2026-09-04T14:40:17+00:00

**pod**: hexapod-mjx-train-9

**steps**: 2000000

**parent**: cw-standwalk-stage2-dualbc6-turncap-mirroraug-yawcredit-gradclip0p15-cap29-stdwalklohi-cont-s1

**wandb_id**: mev8p3s6

**hypothesis**: Plain English: this cycle's re-score of the 6-lever-family FAIL wall against matched continuations (not frozen parents) found seed1 flips 5/10 lever cells to PASS while seed0 stays 9/10 FAIL -- but that flip rides entirely on ONE continuation control (cont-s1, own pure-turn/combined wz_med 0.152/0.105, WEAKER than cont's 0.172/0.132). This is the named falsifier: an independent second seed1 plain-continuation (same recipe -- 2M steps off cap29-stdwalklo-hi-s1, zero lever, identical cfg stack -- only the trainer RNG seed changes 1->21) to test whether cont-s1's weaker floor is a real per-seed-training-dynamics effect (this arm reproduces a similarly weak floor) or cont-s1-specific idiosyncrasy (this arm lands close to cont's stronger floor instead). If it reproduces the weak floor, the 5 PASS cells are legitimate reopen candidates for a confirmatory acquisition run; if it lands strong like cont, the FAIL wall re-closes and cont-s1 was simply an unlucky draw.

**gate**: MECHANISM-HEALTH CANARY ONLY: do not judge skill acquisition, close a behavior/reward class, or require mature gait at this checkpoint. MECHANISM-HEALTH CANARY ONLY: do not judge skill acquisition, close a behavior/reward class, or require mature gait at this checkpoint. This is a CONTROL-VALIDITY check, not a behavior gate: report probe_turn_authority.py pure-turn and combined-tick (vx=0.08) wz_med (probe-seeds 0/1 avg) alongside cont-s1's own read (0.152/0.105) and cont's read (0.172/0.132). No fixed pass/fail threshold -- the finding is whichever number it lands closest to; training must finish clean (W&B state=finished, no infra death) for the read to count at all.

**verdict**: CANARY PASS (control-validity read, as designed — no behavior gate). 2nd independent zero-lever seed1 continuation (seed 21); trained clean (W&B finished @2.03M). DIG-IN RESOLVED (deep model, n=4 spread with cont-s1c/s1d probes run this cycle): the 5/10 seed1 lever-cell reopening was COMPARATOR NOISE — the sign-collapsed rescore_cell PASS vs a single control draw is invalid on this axis (zero-lever controls PASS each other: cont vs cont-s1 = +25.8/+54.2% combined; all 5 reopened cells flip to FAIL when the denominator swaps cont-s1->cont-s1b; per-cell PASS counts vs the 4 control draws are 0/4-2/4). Measured n=4 seed1 zero-lever continuation spread: pt_pos 0.119-0.196 (50% rel), cb_pos 0.064-0.136 (65% rel), pt_neg 0.170-0.198, cb_neg 0.120-0.138 (tight). NEW REAL per-sign finding the collapsed score hid: cb_neg (negative-command combined turn authority) collapses in 4/4 zero-lever continuations (0.127+/-0.008) vs frozen parent 0.142 and seed0 cont 0.190, while 9/10 lever arms sit ABOVE the band at 0.14-0.19 (binomial p~4e-6) — geometry levers don't IMPROVE steering (cb_pos 0/10 wins), they partially PROTECT it against continuation erosion; frozen parents keep the best pure-turn (0.223-0.226 vs all continuations 0.119-0.214). Methodology now tooling: rescore_turn_authority band subcommand (per-clause WIN/LOSS/no-call vs control band). FAIL wall on 'levers improve combined turn authority' stays CLOSED; no acquisition run on the 5 cells. Next: n=3 seed0 control band (cont-b/cont-c launched) to re-score the seed0 half of the wall the same way.

