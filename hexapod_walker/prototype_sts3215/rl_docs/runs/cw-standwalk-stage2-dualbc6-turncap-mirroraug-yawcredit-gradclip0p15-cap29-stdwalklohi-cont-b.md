# cw-standwalk-stage2-dualbc6-turncap-mirroraug-yawcredit-gradclip0p15-cap29-stdwalklohi-cont-b

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: PASS

**created**: 2026-09-04T16:23:08+00:00

**pod**: hexapod-mjx-train-2

**steps**: 2000000

**parent**: cw-standwalk-stage2-dualbc6-turncap-mirroraug-yawcredit-gradclip0p15-cap29-stdwalklohi-cont

**wandb_id**: q5j38b8i

**hypothesis**: Plain English: the seed0 half of the geometry-lever FAIL wall (9/10 FAIL) is currently scored against a SINGLE zero-lever continuation draw (cont); the 09-04 dig-in proved single-draw comparators on this axis swing up to 65% per clause and that 4/4 seed1 zero-lever continuations collapse negative-combined turn authority (cb_neg 0.127+/-0.008) while cont holds 0.190. This is the 2nd independent seed0 zero-lever plain-continuation (same recipe as cont — init-from frozen cap29-stdwalklo-hi, zero lever, only trainer seed 21) to build the seed0 control band: decides (a) whether the seed0 FAIL wall survives band scoring and (b) whether cont's high cb_neg was a lucky draw or a real seed0/seed1 lineage difference.

**gate**: MECHANISM-HEALTH CANARY ONLY: do not judge skill acquisition, close a behavior/reward class, or require mature gait at this checkpoint. MECHANISM-HEALTH CANARY ONLY: no behavior gate, no fixed pass/fail. Training must finish clean (W&B state=finished). Report probe_turn_authority 4-clause magnitudes (pure/combined x +/-, probe-seeds 0/1 median, full cfg replay via rescore_turn_authority cfg) alongside cont (pt 0.172/0.200, cb 0.132/0.190), frozen parent s0 (pt 0.223/0.250, cb 0.110/0.170), and the n=4 seed1 band; then band-score the 10 seed0 lever cells vs the n=3 seed0 band per the 09-04 methodology ruling.

**verdict**: CANARY PASS (control-validity read, as designed). 2nd independent zero-lever seed0 continuation (seed 21, init-from frozen cap29-stdwalklo-hi); trained clean (W&B finished @2.03M). probe_turn_authority (own pod train-2, full 84-key cfg replay, --vx-cmds 0.0,0.08): pt_pos 0.162, pt_neg 0.157, cb_pos 0.121, cb_neg 0.171. Together with cont/cont-c this completes the n=3 seed0 zero-lever control band (pt_pos 0.162-0.200, pt_neg 0.157-0.200, cb_pos 0.121-0.132, cb_neg 0.152-0.190) that answers standwalk STATUS Next#2: (a) the seed0 '9/10 FAIL' wall does NOT survive as a real claim -- scored via the old single-control table method, cont-b and cont-c (themselves zero-lever) ALSO score FAIL vs cont (both PASS=False), proving the single-draw comparator is invalid for seed0 same as seed1; band-scored against the n=3 control, only 1/10 seed0 lever cells (yawarm1p5) wins both cb signs, matching the near-null seed1 result -- geometry levers still do not reliably IMPROVE combined turn authority. (b) cb_neg does NOT collapse in the seed0 band (0.152-0.190, tracks frozen-parent-s0 0.170) unlike the tight low seed1 band (0.120-0.138) -- the cb_neg continuation-erosion finding is SEED1-LINEAGE-SPECIFIC, not a lineage-independent effect. Full band table + manifest: logs/ckpt_eval/rescore_turn_authority_09-04/manifest_n4.json (cont_b/cont_c added this cycle).

