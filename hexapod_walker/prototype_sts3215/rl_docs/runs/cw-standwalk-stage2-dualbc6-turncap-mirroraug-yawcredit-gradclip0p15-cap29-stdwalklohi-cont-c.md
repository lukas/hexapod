# cw-standwalk-stage2-dualbc6-turncap-mirroraug-yawcredit-gradclip0p15-cap29-stdwalklohi-cont-c

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: PASS

**created**: 2026-09-04T16:24:26+00:00

**pod**: hexapod-mjx-train-3

**steps**: 2000000

**parent**: cw-standwalk-stage2-dualbc6-turncap-mirroraug-yawcredit-gradclip0p15-cap29-stdwalklohi-cont

**wandb_id**: ul2iuyd7

**hypothesis**: Plain English: 3rd independent seed0 zero-lever plain-continuation (same recipe as cont/cont-b, trainer seed 31) completing the n=3 seed0 control band required by the 09-04 dig-in methodology ruling (per-clause band scoring; single-draw comparators refuted). Together with cont-b it decides whether the 9/10 seed0 lever FAIL wall survives band scoring and whether cb_neg continuation-collapse is seed1-specific or lineage-independent.

**gate**: MECHANISM-HEALTH CANARY ONLY: do not judge skill acquisition, close a behavior/reward class, or require mature gait at this checkpoint. MECHANISM-HEALTH CANARY ONLY: no behavior gate, no fixed pass/fail. Training must finish clean (W&B state=finished). Report probe_turn_authority 4-clause magnitudes (full cfg replay, --vx-cmds 0.0,0.08) vs cont/cont-b/frozen-parent-s0 and band-score the 10 seed0 lever cells vs the n=3 seed0 band.

**verdict**: CANARY PASS (control-validity read, as designed). 3rd independent zero-lever seed0 continuation (seed 31, init-from frozen cap29-stdwalklo-hi); trained clean (W&B finished @2.03M). probe_turn_authority (own pod train-3, full 84-key cfg replay, --vx-cmds 0.0,0.08): pt_pos 0.200, pt_neg 0.175, cb_pos 0.132, cb_neg 0.152 -- completes the n=3 seed0 band with cont/cont-b (see cont-b's verdict for the full resolution). DIG-IN RESOLVED (standwalk STATUS Next#2, this cycle): seed0 '9/10 FAIL' wall is comparator noise (cont-b/cont-c, themselves zero-lever, ALSO FAIL vs cont under the old single-control method); band-scored only 1/10 seed0 lever cells (yawarm1p5) wins both cb signs. cb_neg does NOT collapse for seed0 (band 0.152-0.190, tracks frozen-parent-s0 0.170), unlike the tight collapsed seed1 band (0.120-0.138) -- confirms the cb_neg erosion finding is seed1-lineage-specific, not general. Binding conclusion updated: NO lever acquisition on this axis for either seed; frozen parents (0.223-0.226 seed1 pure-turn, 0.223/0.250 seed0 pt/cb-pos) remain the best pure-turn/steering checkpoints. Manifest: logs/ckpt_eval/rescore_turn_authority_09-04/manifest_n4.json.

