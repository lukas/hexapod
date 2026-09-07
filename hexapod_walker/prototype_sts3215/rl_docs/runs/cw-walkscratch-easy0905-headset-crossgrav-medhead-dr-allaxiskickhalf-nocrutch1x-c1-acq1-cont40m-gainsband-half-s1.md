# cw-walkscratch-easy0905-headset-crossgrav-medhead-dr-allaxiskickhalf-nocrutch1x-c1-acq1-cont40m-gainsband-half-s1

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: CANARY_PASS

**created**: 2026-09-07T12:56:12+00:00

**pod**: hexapod-mjx-train-8

**steps**: 2000000

**parent**: cw-walkscratch-easy0905-headset-crossgrav-medhead-dr-allaxiskickhalf-nocrutch1x-c1-acq1-cont40m

**wandb_id**: fqyap3ro

**hypothesis**: Plain English: is this composite's persistent ~5/m steady-state slip gap (present even in undisturbed episodes, all 4 reward-shaping fixes closed) caused by this DR axis's WIDTH, not the reward? Single lever vs the plain cont40m champion: per-servo gain jitter halved (kp_scale_pct 0.20->0.10, kv_scale_pct 0.25->0.125). Seed 1 of a 2-seed pair (s0 companion). Prediction-if-true: held-out slip_per_m drops materially in undisturbed episodes with gait/falls holding. Prediction-if-false: slip stays flat -- axis exonerated, move to the next candidate or accept the gap as this composite's hardening boundary (both friction and compliance also being tested this same cycle).

**gate**: MECHANISM-HEALTH CANARY ONLY: do not judge skill acquisition, close a behavior/reward class, or require mature gait at this checkpoint. DR-BAND NARROWING CANARY (mechanism-health/diagnostic tier): retrains from the SAME cont40m champion under gains DR jitter halved, everything else byte-identical (no slip-shaping reward active). Tests whether the composite's steady-state undisturbed-episode slip gap (baseline 4.2-5.7/m) is DR-band-driven, since 4 independent reward-shaping mechanisms are now closed 4/4. PASS-IMPLICATED if held-out slip_per_m in undisturbed episodes drops >=15% median vs baseline with gait_valid/falls holding. FAIL-EXONERATED if slip stays within noise. Confound: this is a retrain (2M adaptation), not a pure re-eval -- a PASS-IMPLICATED read should be corroborated by re-evaluating the frozen cont40m checkpoint at the same band (zero-spend) before funding more budget.

**verdict**: CANARY PASS (mechanism healthy: reward rose cleanly 16.8->421 across quarters, no crash/NaN, 2M steps completed). Scientific reading (mechanism-health tier, informational only, not a skill verdict): FAIL-EXONERATED for the gains-jitter-band-width hypothesis. Halving dr.kp_scale_pct/kv_scale_pct (0.20/0.25 -> 0.10/0.125) does NOT reduce the composite's steady-state slip gap -- gait_valid 22/24, numerically the SAME total AND the SAME episode-level fingerprint as the frozen parent cont40m champion's own DR-0 gate (leg2 sacrifice at walk/sto ep4 AND walk_startjitter/det ep1 in both, nothing else). slip_per_m med 4.87/5.12/4.60/5.49 across the 4 modes vs champion's own 4.98/5.17/5.10/5.42 -- within noise, no mode clears the >=15% drop bar. Rules out servo-gain jitter band width as the driver of the persistent undisturbed-episode slip gap (1/2 seeds; s0 sibling still evaluating on its own pod under another cycle's kick -- left for that reader, do not duplicate). Converges with the same-cycle frictionband-half-s0 finding: two independent axes, two different seeds, both replicate the champion's exact per-episode signature almost verbatim -- consistent early signal that the composite's slip gap is not DR-band-width-driven on either axis tried so far.

