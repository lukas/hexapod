# cw-standwalk-stage2-dualbc6-turncap-mirroraug-klrolldriftmatch-acq1-s1

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: ACQ PARTIAL - MATCHED-DRIFT CONFIRMED, JOINT CLOSE 2/2

**created**: 2026-09-01T07:54:03+00:00

**pod**: hexapod-mjx-train-2

**steps**: 8000000

**parent**: cw-standwalk-stage2-dualbc6-turncap-mirroraug-klrolldriftmatch-acq1

**wandb_id**: gbwda915

**hypothesis**: Seed-pass-rate twin of klrolldriftmatch-acq1 (same matched-actor-training-steps confound test: freeze+guard=0.02 final ckpt, init-from-source, --actor-freeze-steps=0, +8M steps to reach 38M actor-training-steps total, matching the guard-only sibling's own 38M-actor-step final read pos 0.0743-0.0754/neg -0.1154 to -0.1204). Only the training seed differs (0->1). Cheap (8M steps, ~10min) confidence check before the campaign either abandons freeze-based mechanism work (if both seeds converge to the guard-only floor) or funds a periodic-re-freeze design (if both hold near 0.078-0.080).

**gate**: Same bands as klrolldriftmatch-acq1 (own probe_turn_authority curve, TURNCAP_CFG_SET). Read jointly with the seed0 arm: BOTH seeds converging to the guard-only floor (~0.075 pos/-0.115 to -0.120 neg) = MATCHED-DRIFT CONFIRMED with n=2, freeze-mechanism line closed with confidence. BOTH holding near 0.078-0.080 pos = FREEZE-PROTECTS confirmed with n=2. Split result = genuinely AMBIGUOUS, report both reads plainly rather than picking a side.

**verdict**: JOINT CLOSE (n=2, with seed0 klrolldriftmatch-acq1, verdicted same cycle). Seed-1 twin of the matched-actor-training-steps confound test: same conclusion. Own 4-point probe_turn_authority curve (2M/4M/6M/8M elapsed=32/34/36/38M actor-steps, TURNCAP_CFG_SET) built on-pod: pos 0.0864/0.0730 (2M) -> 0.0846/0.0739 (4M) -> 0.0870/0.0662 (6M) -> 0.0891/0.0639 (final); neg -0.1055/-0.1019 (2M) -> -0.1110/-0.1091 (4M) -> -0.1046/-0.1148 (6M) -> -0.1029/-0.1091 (final). Final avg pos 0.0765, neg -0.1060 -- within noise of seed0s own final (pos 0.0767, neg -0.1075) and of the guard-only siblings 38M-actor-step floor (pos 0.0743-0.0754, neg -0.1154 to -0.1204); slow continued decline from the shared 0M-elapsed start (pos avg 0.078, neg avg -0.1153), not a held-flat plateau. eval/walk/survived_frac=1.0, all probe rollouts fell=false -- no gait-collapse confound. MATCHED-DRIFT CONFIRMED with n=2: freeze only delays erosion, total actor-training-steps is the real driver of the durable-authority ceiling (~0.075-0.09 pos / ~-0.10 to -0.12 neg), not freeze itself. Closes the freeze-based mechanism line -- no further freeze-only or periodic-re-freeze work funded on this axis; the campaigns remaining named escalation is a reward-decomposed/command-conditioned critic architecture (genuine new-code work, scoped in STATUS.md this cycle, not yet built). Evidence: logs/ckpt_eval/turn_authority_dualbc6_turncap_mirroraug_klrolldriftmatch_acq1_s1_curve.json (built this cycle, on-pod).

