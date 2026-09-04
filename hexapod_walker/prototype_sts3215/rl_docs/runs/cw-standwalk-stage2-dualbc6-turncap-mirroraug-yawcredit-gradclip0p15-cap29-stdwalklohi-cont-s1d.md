# cw-standwalk-stage2-dualbc6-turncap-mirroraug-yawcredit-gradclip0p15-cap29-stdwalklohi-cont-s1d

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: PASS

**created**: 2026-09-04T15:47:17+00:00

**pod**: hexapod-mjx-train-1

**steps**: 2000000

**parent**: cw-standwalk-stage2-dualbc6-turncap-mirroraug-yawcredit-gradclip0p15-cap29-stdwalklohi-cont-s1

**wandb_id**: krfeo459

**hypothesis**: Plain English: 4th independent seed1-family plain-continuation (same recipe as cont-s1/-s1b/-s1c -- init-from the SAME frozen cap29-stdwalklo-hi-s1 checkpoint, zero lever, only trainer RNG seed changes) to build a real n>=3 control distribution for the 5/10 seed1 lever-cell re-score flip, since -s1b came back an ambiguous THIRD sign-asymmetric pattern matching neither cont nor cont-s1 cleanly.

**gate**: MECHANISM-HEALTH CANARY ONLY: do not judge skill acquisition, close a behavior/reward class, or require mature gait at this checkpoint. MECHANISM-HEALTH CANARY ONLY, no fixed pass/fail. Report probe_turn_authority pure-turn/combined wz_med both signs vs cont/cont-s1/cont-s1b/cont-s1c. Training must finish clean for the read to count.

**verdict**: CANARY PASS (control-validity read, as designed). 4th independent zero-lever seed1 continuation (seed 41); trained clean (W&B finished @2.03M). probe_turn_authority (own pod, full 84-key cfg replay, --vx-cmds 0.0,0.08): pt_pos 0.119, pt_neg 0.195, cb_pos 0.064, cb_neg 0.125 — the weakest POSITIVE-clause draw of all 4 controls (probe's median flag says FROZEN-BODY but that is the collapsed median being dragged by the weak positive side; pt_neg 0.195 tracks fine, so not the OOD-cfg artifact). This draw single-handedly proves the dig-in's point: the zero-lever continuation process spans cb_pos 0.064-0.136 (65% rel spread) — any lever cell scored vs a single draw of THIS distribution is uninterpretable. Confirms cb_neg collapse 4/4 (0.125, inside the tight 0.120-0.138 band, below all 10 lever arms except one marginal). Artifact: logs/ckpt_eval/probe_turn_authority_cap29_stdwalklohi_cont_s1d_combined_09-04.json; full resolution in cont-s1b's verdict + standwalk STATUS 09-04 ~16:2x.

