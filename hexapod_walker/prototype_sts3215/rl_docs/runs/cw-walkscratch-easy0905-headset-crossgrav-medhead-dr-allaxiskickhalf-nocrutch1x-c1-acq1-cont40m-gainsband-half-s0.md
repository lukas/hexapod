# cw-walkscratch-easy0905-headset-crossgrav-medhead-dr-allaxiskickhalf-nocrutch1x-c1-acq1-cont40m-gainsband-half-s0

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: CANARY_PASS

**created**: 2026-09-07T12:53:44+00:00

**pod**: hexapod-mjx-train-0

**steps**: 2000000

**parent**: cw-walkscratch-easy0905-headset-crossgrav-medhead-dr-allaxiskickhalf-nocrutch1x-c1-acq1-cont40m

**wandb_id**: 4wf8a0li

**hypothesis**: Plain English: is this composite's persistent ~5/m steady-state slip gap (present even in undisturbed episodes, all 4 reward-shaping fixes closed) caused by this DR axis's WIDTH, not the reward? Single lever vs the plain cont40m champion: per-servo gain jitter halved (kp_scale_pct 0.20->0.10, kv_scale_pct 0.25->0.125). Seed 0 of a 2-seed pair (s1 companion). Prediction-if-true: held-out slip_per_m drops materially in undisturbed episodes with gait/falls holding. Prediction-if-false: slip stays flat -- axis exonerated, move to the next candidate or accept the gap as this composite's hardening boundary (both friction and compliance also being tested this same cycle).

**gate**: MECHANISM-HEALTH CANARY ONLY: do not judge skill acquisition, close a behavior/reward class, or require mature gait at this checkpoint. DR-BAND NARROWING CANARY (mechanism-health/diagnostic tier): retrains from the SAME cont40m champion under gains DR jitter halved, everything else byte-identical (no slip-shaping reward active). Tests whether the composite's steady-state undisturbed-episode slip gap (baseline 4.2-5.7/m) is DR-band-driven, since 4 independent reward-shaping mechanisms are now closed 4/4. PASS-IMPLICATED if held-out slip_per_m in undisturbed episodes drops >=15% median vs baseline with gait_valid/falls holding. FAIL-EXONERATED if slip stays within noise. Confound: this is a retrain (2M adaptation), not a pure re-eval -- a PASS-IMPLICATED read should be corroborated by re-evaluating the frozen cont40m checkpoint at the same band (zero-spend) before funding more budget.

**verdict**: CANARY PASS (mechanism healthy: reward rose cleanly 23.2->372.6 across quarters, no crash/NaN, 2M steps completed). Scientific reading: FAIL-EXONERATED, 2nd seed CONFIRMS s1. gait_valid 22/24, numerically the SAME total and the SAME episode-level fingerprint as the frozen parent cont40m champion (leg2 sac at walk/sto ep4 AND walk_startjitter/det ep1, nothing else). slip_per_m med 5.00/4.83/4.88/5.48 vs champion's own 4.98/5.17/5.10/5.42 -- within noise on every mode. CLOSES the servo-gain-jitter band-width axis 2/2 seeds FAIL-EXONERATED -- halving dr.kp_scale_pct/kv_scale_pct does not touch the composite's steady-state slip gap.

