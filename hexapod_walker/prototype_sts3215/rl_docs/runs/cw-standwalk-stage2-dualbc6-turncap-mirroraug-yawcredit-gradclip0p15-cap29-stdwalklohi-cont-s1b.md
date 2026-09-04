# cw-standwalk-stage2-dualbc6-turncap-mirroraug-yawcredit-gradclip0p15-cap29-stdwalklohi-cont-s1b

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: RUNNING

**created**: 2026-09-04T14:40:17+00:00

**pod**: hexapod-mjx-train-9

**steps**: 2000000

**parent**: cw-standwalk-stage2-dualbc6-turncap-mirroraug-yawcredit-gradclip0p15-cap29-stdwalklohi-cont-s1

**wandb_id**: mev8p3s6

**hypothesis**: Plain English: this cycle's re-score of the 6-lever-family FAIL wall against matched continuations (not frozen parents) found seed1 flips 5/10 lever cells to PASS while seed0 stays 9/10 FAIL -- but that flip rides entirely on ONE continuation control (cont-s1, own pure-turn/combined wz_med 0.152/0.105, WEAKER than cont's 0.172/0.132). This is the named falsifier: an independent second seed1 plain-continuation (same recipe -- 2M steps off cap29-stdwalklo-hi-s1, zero lever, identical cfg stack -- only the trainer RNG seed changes 1->21) to test whether cont-s1's weaker floor is a real per-seed-training-dynamics effect (this arm reproduces a similarly weak floor) or cont-s1-specific idiosyncrasy (this arm lands close to cont's stronger floor instead). If it reproduces the weak floor, the 5 PASS cells are legitimate reopen candidates for a confirmatory acquisition run; if it lands strong like cont, the FAIL wall re-closes and cont-s1 was simply an unlucky draw.

**gate**: MECHANISM-HEALTH CANARY ONLY: do not judge skill acquisition, close a behavior/reward class, or require mature gait at this checkpoint. MECHANISM-HEALTH CANARY ONLY: do not judge skill acquisition, close a behavior/reward class, or require mature gait at this checkpoint. This is a CONTROL-VALIDITY check, not a behavior gate: report probe_turn_authority.py pure-turn and combined-tick (vx=0.08) wz_med (probe-seeds 0/1 avg) alongside cont-s1's own read (0.152/0.105) and cont's read (0.172/0.132). No fixed pass/fail threshold -- the finding is whichever number it lands closest to; training must finish clean (W&B state=finished, no infra death) for the read to count at all.

