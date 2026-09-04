# cw-standwalk-stage2-dualbc6-turncap-mirroraug-yawcredit-gradclip0p15-cap29-stdwalklohi-cont-s1c

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: RUNNING

**created**: 2026-09-04T15:42:52+00:00

**pod**: hexapod-mjx-train-9

**steps**: 2000000

**parent**: cw-standwalk-stage2-dualbc6-turncap-mirroraug-yawcredit-gradclip0p15-cap29-stdwalklohi-cont-s1

**wandb_id**: 16jq8zmw

**hypothesis**: Plain English: cont-s1b's own falsifier read came back ambiguous -- it's a THIRD, sign-asymmetric pattern (matches cont on positive-command turn authority, matches-or-worsens cont-s1's weak floor on negative-command), meaning a single matched-continuation control (n=1/seed) is not a stable comparator for the 5/10 seed1 lever-cell re-score flip. This is the 3rd independent seed1-family plain-continuation (same recipe as cont-s1/cont-s1b -- init-from the SAME frozen cap29-stdwalklo-hi-s1 checkpoint, zero lever, only trainer RNG seed changes 1->21->31) to start building an actual control DISTRIBUTION instead of trusting any single draw.

**gate**: MECHANISM-HEALTH CANARY ONLY: do not judge skill acquisition, close a behavior/reward class, or require mature gait at this checkpoint. MECHANISM-HEALTH CANARY ONLY, no fixed pass/fail. Report probe_turn_authority pure-turn/combined wz_med (both signs, probe-seeds 0/1 avg) alongside cont(0.172/0.132 pos, -0.199/-0.190 neg), cont-s1(0.152/0.105 pos, -0.190/-0.123 neg), and cont-s1b(0.196/0.132 pos, -0.170/-0.120 neg). Training must finish clean (W&B state=finished) for the read to count. Purpose: with n=3 independent seed1 continuations, compute a real spread (not a single delta) to decide whether the 5/10 lever-cell flip is inside normal per-seed variance or a genuine effect.

