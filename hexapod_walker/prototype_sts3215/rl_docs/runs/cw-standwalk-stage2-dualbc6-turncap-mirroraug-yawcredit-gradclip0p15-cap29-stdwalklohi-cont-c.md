# cw-standwalk-stage2-dualbc6-turncap-mirroraug-yawcredit-gradclip0p15-cap29-stdwalklohi-cont-c

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: REFUSED

**created**: 2026-09-04T16:22:18+00:00

**pod**: hexapod-mjx-train-3

**steps**: 2000000

**parent**: cw-standwalk-stage2-dualbc6-turncap-mirroraug-yawcredit-gradclip0p15-cap29-stdwalklohi-cont

**hypothesis**: Plain English: 3rd independent seed0 zero-lever plain-continuation (same recipe as cont/cont-b, trainer seed 31) completing the n=3 seed0 control band required by the 09-04 dig-in methodology ruling (per-clause band scoring; single-draw comparators refuted). Together with cont-b it decides whether the 9/10 seed0 lever FAIL wall survives band scoring and whether cb_neg continuation-collapse is seed1-specific or lineage-independent.

**gate**: MECHANISM-HEALTH CANARY ONLY: do not judge skill acquisition, close a behavior/reward class, or require mature gait at this checkpoint. MECHANISM-HEALTH CANARY ONLY: no behavior gate, no fixed pass/fail. Training must finish clean (W&B state=finished). Report probe_turn_authority 4-clause magnitudes (full cfg replay, --vx-cmds 0.0,0.08) vs cont/cont-b/frozen-parent-s0 and band-score the 10 seed0 lever cells vs the n=3 seed0 band.

**refused_reason**: hexapod-mjx-train-3 code marker 804da7d2d040a44dc4a2c949f6a18338ec57576b-dirty != local HEAD 804da7d2d040a44dc4a2c949f6a18338ec57576b and the delta is not benign-orchestrator-only. Sync first: snapshot.sh --sync hexapod-mjx-train-3 (and snapshot/commit before that if the tree is dirty).

