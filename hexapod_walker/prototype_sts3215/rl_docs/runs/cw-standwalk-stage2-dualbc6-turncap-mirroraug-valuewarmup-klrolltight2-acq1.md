# cw-standwalk-stage2-dualbc6-turncap-mirroraug-valuewarmup-klrolltight2-acq1

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: RUNNING

**created**: 2026-09-01T06:16:01+00:00

**pod**: hexapod-mjx-train-0

**steps**: 38000000

**parent**: cw-standwalk-stage2-dualbc6-turncap-mirroraug-valuewarmup-klrolltight-acq1

**wandb_id**: ocxe34st

**hypothesis**: Plain English: pushing the update-size cap even tighter (0.02->0.01, now BELOW the trainer's own --target-kl=0.02) on top of the already-validated freeze+guard combo -- does turn authority keep climbing toward the >=0.10-both-signs PASS bar, or does the policy stop being able to adapt at all? This cycle's own 12-point probe_turn_authority curve on valuewarmup-klrolltight-acq1 (freeze 8M + kl-rollback=0.02) verdicted PARTIAL-BETTER vs the 0.05 sibling: final pos 0.0803/0.0756 (up from 0.068/0.068), neg -0.1131/-0.1175 (more negative than -0.109/-0.110) -- both signs improved, confirms the update-size dose-response holds even combined with freeze, exactly the gate's own PARTIAL-BETTER branch which names 'one more notch down' as the next step. In-training clean throughout (eval/walk survived_frac=1, walk_startjitter survived_frac=1, reward rising every quarter, kl_rollback_count=8 total, realized approx_kl bounded 0.012-0.019 post-unfreeze -- tighter than the 0.02 arm's own 0.01-0.03 band, confirming the guard is engaging harder). Identical recipe to valuewarmup-klrolltight-acq1 (actor-freeze-steps=8000000, same turnpay-canary init, same seed 0) except --kl-rollback 0.02->0.01.

**gate**: PASS/promote-to-stage2-source if final (38M) probe_turn_authority (own TURNCAP_CFG_SET) wz_med >=0.10 both signs AND det walk gait_valid>=5/6 zero falls AND purewalk det progress_ratio in/above 0.40-0.48. PARTIAL-BETTER if final wz_med improves over valuewarmup-klrolltight-acq1's own final (pos>0.078, neg more negative than -0.115) but still misses PASS -- dose-response still monotonic, motivates yet one more notch (0.005) or a seed twin to confirm. PARTIAL-SAME/WORSE if final reads land within noise of or below the 0.02 sibling's plateau -- 0.02 already captured the achievable gain from this lever; stop tightening, escalate to reward-decomposed critic for the remaining positive-sign gap. FAIL if gait_valid or progress_ratio regress hard vs the 0.02 sibling (cap too tight, starves adaptation entirely) -- bracket back up toward 0.02/0.015.

