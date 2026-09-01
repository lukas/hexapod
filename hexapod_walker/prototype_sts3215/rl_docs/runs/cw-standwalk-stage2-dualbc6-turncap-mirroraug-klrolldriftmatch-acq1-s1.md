# cw-standwalk-stage2-dualbc6-turncap-mirroraug-klrolldriftmatch-acq1-s1

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: RUNNING

**created**: 2026-09-01T07:54:03+00:00

**pod**: hexapod-mjx-train-2

**steps**: 8000000

**parent**: cw-standwalk-stage2-dualbc6-turncap-mirroraug-klrolldriftmatch-acq1

**wandb_id**: gbwda915

**hypothesis**: Seed-pass-rate twin of klrolldriftmatch-acq1 (same matched-actor-training-steps confound test: freeze+guard=0.02 final ckpt, init-from-source, --actor-freeze-steps=0, +8M steps to reach 38M actor-training-steps total, matching the guard-only sibling's own 38M-actor-step final read pos 0.0743-0.0754/neg -0.1154 to -0.1204). Only the training seed differs (0->1). Cheap (8M steps, ~10min) confidence check before the campaign either abandons freeze-based mechanism work (if both seeds converge to the guard-only floor) or funds a periodic-re-freeze design (if both hold near 0.078-0.080).

**gate**: Same bands as klrolldriftmatch-acq1 (own probe_turn_authority curve, TURNCAP_CFG_SET). Read jointly with the seed0 arm: BOTH seeds converging to the guard-only floor (~0.075 pos/-0.115 to -0.120 neg) = MATCHED-DRIFT CONFIRMED with n=2, freeze-mechanism line closed with confidence. BOTH holding near 0.078-0.080 pos = FREEZE-PROTECTS confirmed with n=2. Split result = genuinely AMBIGUOUS, report both reads plainly rather than picking a side.

