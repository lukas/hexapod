# cw-standwalk-stage2-dualbc6-turncap-mirroraug-valuewarmup-klrolltight-acq1

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: RUNNING

**created**: 2026-09-01T03:27:06+00:00

**pod**: hexapod-mjx-train-0

**steps**: 38000000

**parent**: cw-standwalk-stage2-dualbc6-turncap-mirroraug-valuewarmup-klroll-acq1

**wandb_id**: 3nyyea80

**hypothesis**: Plain English: combining a tighter update-size cap with the actor-freeze/critic-warmup -- does that push turn authority all the way to the >=0.10-both-signs DONE bar? This cycle's joint read of valuewarmup-klroll-acq1 (freeze 8M + guard 0.05) vs klrollctrl-acq1 (guard 0.05 only, no freeze) answered the pair's own pre-registered fork as BOTH NEEDED: guard-alone reaches the SAME mid-run plateau (8-20M: ~0.06-0.09 pos/-0.08 to -0.12 neg) FASTER than freeze+guard, but that plateau is NOT durable alone -- it resumes eroding from ~24M onward and ends at final 38M pos 0.055/0.055, neg -0.065/-0.070 (close to the unguarded parent's own floor of pos 0.029/0.032, neg -0.069/-0.065). Freeze+guard=0.05 instead HOLDS its plateau essentially flat 10M->38M (final pos 0.068/0.068, neg -0.109/-0.110 -- the first arm in the whole 10-mechanism-class campaign to clear the neg PASS bar). Identical recipe to valuewarmup-klroll-acq1 (actor-freeze-steps=8000000, same turnpay-canary init, same seed) except --kl-rollback 0.05->0.02 (tighter, matching the trainer's own --target-kl=0.02 exactly) -- combines the two ingredients this cycle showed are separately necessary. Prediction-if-true: final wz_med clears or gets materially closer to >=0.10 on the positive sign too (currently the only missing clause), promotable to stage2 source. Prediction-if-false: pos plateaus at/near 0.068 regardless of tighter cap (0.05 already captured the achievable ceiling of this lever) or the tighter cap starves early adaptation post-unfreeze (authority/gait regress vs the 0.05 sibling).

**gate**: PASS/promote-to-stage2-source if final (38M) probe_turn_authority (own TURNCAP_CFG_SET) wz_med >=0.10 both signs AND det walk gait_valid>=5/6 zero falls AND purewalk det progress_ratio in/above 0.40-0.48. PARTIAL-BETTER if final wz_med improves over valuewarmup-klroll-acq1's own final (pos>0.068, neg more negative than -0.109) but still misses PASS -- confirms tighter-cap dose-response holds even with freeze, motivates one more notch down. PARTIAL-SAME/WORSE if final reads land within noise of or below the 0.05+freeze sibling's plateau -- 0.05 already captured the achievable gain, freeze+guard is at its ceiling; stop tightening, escalate to reward-decomposed critic for the remaining positive-sign gap. FAIL if gait_valid or progress_ratio regress hard vs the 0.05 sibling (cap too tight post-unfreeze, starves adaptation) -- bracket back up toward 0.05/0.035.

