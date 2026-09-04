# cw-standwalk-stage2-dualbc6-turncap-mirroraug-cap29-stdwalklohi-dualcontinue-noyawcredit

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: RUNNING

**created**: 2026-09-04T04:25:24+00:00

**pod**: hexapod-mjx-train-1

**steps**: 2000000

**parent**: cw-standwalk-stage2-dualbc6-turncap-mirroraug-yawcredit-gradclip0p15-cap29-stdwalklo-hi

**wandb_id**: r0s6tke4

**hypothesis**: Plain English: the just-closed TripleGruActorCriticPolicy canary (2/2 FAIL) is confounded -- it warm-started from cap29-stdwalklo-hi (trained WITH train.yaw_credit_coef/_vf_coef/_grad_clip + --gru-dual-log-std-split/--log-std-anneal-core) but then trained 2M MORE steps with those training-time mechanisms DROPPED (by design, 'first-canary discipline'), at the SAME TIME as the Dual->Triple architecture swap. So the observed pure-turn regression could be caused by removing yaw_credit/log_std_split during continued training, not by the architecture change -- the 'matched control' (the frozen cap29-stdwalklo-hi checkpoint, trained WITH those mechanisms throughout) never went through this same mechanisms-off continuation, so the comparison conflates two variables. This run isolates the confound: SAME start checkpoint, SAME 2M-step budget, SAME reward/goal/obs cfg-set and dropped yaw_credit/log_std_split mechanisms as the Triple arm, but --gru-dual (not --gru-triple) -- i.e. exactly what cw-standwalk-stage2-dualbc6-turncap-mirroraug-cap29-stdwalklohi-dualcontinue ran, minus only the architecture split.

**gate**: MECHANISM-HEALTH CANARY ONLY: do not judge skill acquisition, close a behavior/reward class, or require mature gait at this checkpoint. MECHANISM-HEALTH CANARY / CONFOUND-ISOLATION ONLY: this run's job is to explain the already-closed Triple canary's FAIL, not to itself pass/fail the item-2 gate. Read with the SAME probe_turn_authority.py --vx-cmds instrument (full non-train cfg-set replay) against the SAME cap29-stdwalklo-hi{,-s1} control used for the Triple canary. THREE possible readings: (A) this Dual-continuation ALSO regresses pure-turn by a similar 10-26% -> the training-mechanism drop (not the architecture) is the cause, representational-interference hypothesis neither confirmed nor refuted, re-run the Triple canary WITH yaw_credit/log_std_split kept on to get a clean single-lever read; (B) this Dual-continuation holds pure-turn within the 10% cap (like the original control) -> the mechanisms are NOT the cause, the Triple architecture itself genuinely regressed pure-turn, strengthening (not weakening) further architecture-side skepticism; (C) either way, compare this run's OWN combined-tick wz_med to the Triple arm's -- if Dual (this run) beats Triple on combined-tick too, the architecture split bought nothing over a plain continuation.

