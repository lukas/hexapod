# cw-standwalk-stage2-dualbc6-turncap-mirroraug-yawcredit-gradclip0p15-cap29-stdwalklohi-cont-s1c

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: PASS

**created**: 2026-09-04T15:42:52+00:00

**pod**: hexapod-mjx-train-9

**steps**: 2000000

**parent**: cw-standwalk-stage2-dualbc6-turncap-mirroraug-yawcredit-gradclip0p15-cap29-stdwalklohi-cont-s1

**wandb_id**: 16jq8zmw

**hypothesis**: Plain English: cont-s1b's own falsifier read came back ambiguous -- it's a THIRD, sign-asymmetric pattern (matches cont on positive-command turn authority, matches-or-worsens cont-s1's weak floor on negative-command), meaning a single matched-continuation control (n=1/seed) is not a stable comparator for the 5/10 seed1 lever-cell re-score flip. This is the 3rd independent seed1-family plain-continuation (same recipe as cont-s1/cont-s1b -- init-from the SAME frozen cap29-stdwalklo-hi-s1 checkpoint, zero lever, only trainer RNG seed changes 1->21->31) to start building an actual control DISTRIBUTION instead of trusting any single draw.

**gate**: MECHANISM-HEALTH CANARY ONLY: do not judge skill acquisition, close a behavior/reward class, or require mature gait at this checkpoint. MECHANISM-HEALTH CANARY ONLY, no fixed pass/fail. Report probe_turn_authority pure-turn/combined wz_med (both signs, probe-seeds 0/1 avg) alongside cont(0.172/0.132 pos, -0.199/-0.190 neg), cont-s1(0.152/0.105 pos, -0.190/-0.123 neg), and cont-s1b(0.196/0.132 pos, -0.170/-0.120 neg). Training must finish clean (W&B state=finished) for the read to count. Purpose: with n=3 independent seed1 continuations, compute a real spread (not a single delta) to decide whether the 5/10 lever-cell flip is inside normal per-seed variance or a genuine effect.

**verdict**: CANARY PASS (control-validity read, as designed). 3rd independent zero-lever seed1 continuation (seed 31); trained clean (W&B finished @2.03M). probe_turn_authority (own pod, full 84-key cfg replay, --vx-cmds 0.0,0.08): pt_pos 0.149, pt_neg 0.198, cb_pos 0.136, cb_neg 0.138 — a strong-negative/weak-positive draw, inside the emerging control spread on every clause. Together with cont-s1/s1b/s1d it completes the n=4 seed1 zero-lever band (pt_pos 0.119-0.196, pt_neg 0.170-0.198, cb_pos 0.064-0.136, cb_neg 0.120-0.138) that resolved the dig-in: 5/10 lever reopening = comparator noise; cb_neg collapse is consistent across all 4 zero-lever draws (its 0.138 is the band max, still below every lever arm's 0.14-0.19 except one marginal). Artifact: logs/ckpt_eval/probe_turn_authority_cap29_stdwalklohi_cont_s1c_combined_09-04.json; full resolution in cont-s1b's verdict + standwalk STATUS 09-04 ~16:2x.

