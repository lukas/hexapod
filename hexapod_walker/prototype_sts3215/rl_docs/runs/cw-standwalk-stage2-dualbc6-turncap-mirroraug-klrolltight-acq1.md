# cw-standwalk-stage2-dualbc6-turncap-mirroraug-klrolltight-acq1

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: RUNNING

**created**: 2026-09-01T03:19:30+00:00

**pod**: hexapod-mjx-train-1

**steps**: 38000000

**parent**: cw-standwalk-stage2-dualbc6-turncap-mirroraug-klrollctrl-acq1

**wandb_id**: kxsb2y0p

**hypothesis**: Plain English: does a TIGHTER cap on the actor's per-update policy jump defend turn authority even better than the 0.05 cap already tested? This cycle's own joint read of valuewarmup-klroll-acq1 (freeze+guard) and klrollctrl-acq1 (guard-only, no freeze) showed: (1) kl-rollback=0.05 ALONE (no actor-freeze needed) reaches the SAME plateau as freeze+guard, just faster (guard-only 8M checkpoint already at pos 0.068/0.082, neg -0.120/-0.118, matching freeze+guard's own 10-22M plateau of pos 0.07-0.086, neg -0.10 to -0.135) -- freeze is refuted as adding anything beyond the guard; (2) both 0.05 arms land at a genuinely NEW, ~2x-higher floor than every prior naked mechanism class (0.024-0.055) but still fall short of the >=0.10-both-signs PASS bar on the positive sign (final 0.068-0.069 pos, both clear 0.10 on neg). This is the direct dose-response test the finding motivates: identical recipe to klrollctrl-acq1 (no freeze, same turnpay-canary init, same seed) except --kl-rollback 0.05->0.02 (tighter, matching the trainer's own --target-kl=0.02 exactly). Prediction-if-true (update-size is the dominant, monotonic driver): the plateau rises further, closing more of the gap to 0.10 pos. Prediction-if-false (0.05 already captured most of the achievable gain / diminishing returns or over-tightening stalls learning entirely): plateau unchanged or authority/gait quality regresses (KL cap too tight to let the policy adapt at all).

**gate**: Two-point dose-bracket vs this cycle's own 0.05 curves (logs/ckpt_eval/turn_authority_dualbc6_turncap_mirroraug_klrollctrl_acq1_*.json, valuewarmup_klroll_acq1_*.json). PASS/promote if final (38M) probe_turn_authority (own TURNCAP_CFG_SET) wz_med >=0.10 both signs AND det walk gait_valid>=5/6 zero falls AND purewalk det progress_ratio in/above 0.40-0.48. PARTIAL-BETTER if final wz_med improves over BOTH 0.05 arms' final reads (pos>0.069, neg more negative than -0.110) but still misses PASS -- confirms monotonic dose-response, motivates an even tighter cap next. PARTIAL-SAME/WORSE if final reads land within noise of or below the 0.05 arms' plateau -- 0.05 already captured the achievable gain from this lever, do not tighten further. FAIL if gait_valid or progress_ratio regress hard vs the 0.05 arms (cap too tight, starves learning) -- bracket back up.

