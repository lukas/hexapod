# cw-standwalk-stage2-dualbc6-turncap-mirroraug-klrolldriftmatch-acq1

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: RUNNING

**created**: 2026-09-01T07:42:02+00:00

**pod**: hexapod-mjx-train-1

**steps**: 8000000

**parent**: cw-standwalk-stage2-dualbc6-turncap-mirroraug-valuewarmup-klrolltight-acq1

**wandb_id**: jdiv01w8

**hypothesis**: Plain English: is the freeze+guard combo's turn-authority durability really PROTECTION, or just an artifact of its actor getting fewer total post-canary gradient-update steps than the no-freeze siblings? Re-analyzing this cycle's own already-collected curves (no new run needed for this part) found: at MATCHED actor-training-step-count (30M), freeze+guard=0.02's final (elapsed 38M, actor trained 30M since 8M frozen: pos 0.0803/0.0756, neg -0.1131/-0.1175) and guard-only=0.02's own 30M-elapsed checkpoint (also 30M actor-trained, no freeze so elapsed==actor-steps: pos 0.0762/0.0764, neg -0.1167/-0.1269) are statistically indistinguishable -- undercutting the 'freeze protects' story in favor of 'less total actor drift explains the plateau, freeze just delays the same erosion.' This is the decisive single-lever test: continue training FROM the freeze+guard=0.02 lineage's own final checkpoint (init-from-source, actor already warmed up so --actor-freeze-steps=0 now, everything else identical incl. --kl-rollback=0.02) for +8M more steps, bringing its ACTOR-training-step total to 38M -- exactly matching the guard-only sibling's own final actor-training-step count (elapsed 38M, no freeze). Prediction-if-'less-total-drift'-is-the-real-driver: authority erodes further, converging toward the guard-only sibling's own 38M-actor-step final read (pos 0.0743-0.0754, neg -0.1154 to -0.1204) -- freeze bought only a head start, not real protection, and freeze-based mechanism work should not be pursued further as a durability fix. Prediction-if-freeze-genuinely-protects: authority stays near its current plateau (~0.078-0.080 pos, not sliding down to ~0.075) even after 8M more actor-training steps -- refutes the total-actor-steps confound, freeze is a real mechanism worth developing further (e.g. periodic re-freeze/re-anchor).

**gate**: Build the own probe_turn_authority curve (TURNCAP_CFG_SET, on-pod) across this run's own snapshots (2M/4M/6M/8M elapsed = 32M/34M/36M/38M actor-steps). MATCHED-DRIFT CONFIRMED if final (8M elapsed=38M actor-steps) pos/neg land within noise (~0.01) of the guard-only sibling's own 38M-actor-step read (pos 0.0743-0.0754, neg -0.1154 to -0.1204) AND the trend across this run's own snapshots shows continued decline (not a step-function) -- total-actor-training-steps is the dominant driver, freeze only delays; do not fund further freeze-only mechanism work on this axis. FREEZE-PROTECTS if final pos/neg stay materially above that band (e.g. pos still >=0.078, no material further decline from the 0M-elapsed starting point of 0.080/0.076) -- freeze provides real protection beyond a head start; motivates a periodic-re-freeze or re-anchor mechanism as the next design. AMBIGUOUS if the read lands between the two bands (e.g. partial decline to ~0.076-0.078) -- run the seed1 twin (launched alongside) before deciding.

