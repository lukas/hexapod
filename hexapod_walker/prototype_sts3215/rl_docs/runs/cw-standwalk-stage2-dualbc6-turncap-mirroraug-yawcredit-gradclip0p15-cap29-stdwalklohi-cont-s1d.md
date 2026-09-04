# cw-standwalk-stage2-dualbc6-turncap-mirroraug-yawcredit-gradclip0p15-cap29-stdwalklohi-cont-s1d

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: RUNNING

**created**: 2026-09-04T15:47:17+00:00

**pod**: hexapod-mjx-train-1

**steps**: 2000000

**parent**: cw-standwalk-stage2-dualbc6-turncap-mirroraug-yawcredit-gradclip0p15-cap29-stdwalklohi-cont-s1

**wandb_id**: krfeo459

**hypothesis**: Plain English: 4th independent seed1-family plain-continuation (same recipe as cont-s1/-s1b/-s1c -- init-from the SAME frozen cap29-stdwalklo-hi-s1 checkpoint, zero lever, only trainer RNG seed changes) to build a real n>=3 control distribution for the 5/10 seed1 lever-cell re-score flip, since -s1b came back an ambiguous THIRD sign-asymmetric pattern matching neither cont nor cont-s1 cleanly.

**gate**: MECHANISM-HEALTH CANARY ONLY: do not judge skill acquisition, close a behavior/reward class, or require mature gait at this checkpoint. MECHANISM-HEALTH CANARY ONLY, no fixed pass/fail. Report probe_turn_authority pure-turn/combined wz_med both signs vs cont/cont-s1/cont-s1b/cont-s1c. Training must finish clean for the read to count.

