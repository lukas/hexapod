# cw-walkscratch-easy0905-headset-crossgrav-medhead-dr-allaxiskickhalf-nocrutch1x-c1-acq1-cont40m-compliance-half-s1

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: RUNNING

**created**: 2026-09-07T12:57:30+00:00

**pod**: hexapod-mjx-train-7

**steps**: 2000000

**parent**: cw-walkscratch-easy0905-headset-crossgrav-medhead-dr-allaxiskickhalf-nocrutch1x-c1-acq1-cont40m

**wandb_id**: 55g7y2y2

**hypothesis**: Plain English: is this composite's persistent ~5/m steady-state slip gap (present even in undisturbed episodes, all 4 reward-shaping fixes closed) caused by this DR axis's WIDTH, not the reward? Single lever vs the plain cont40m champion: contact_stiff_scale (0.7,2.0 -> 1.025,1.675, same center 1.35, half-width halved). Seed 1 of a 2-seed pair (s0 companion). Prediction-if-true: held-out slip_per_m drops materially in undisturbed episodes with gait/falls holding. Prediction-if-false: slip stays flat -- axis exonerated, move to the next candidate (gains) or accept the gap as this composite's hardening boundary.

**gate**: MECHANISM-HEALTH CANARY ONLY: do not judge skill acquisition, close a behavior/reward class, or require mature gait at this checkpoint. DR-BAND NARROWING CANARY (mechanism-health/diagnostic tier): retrains from the SAME cont40m champion under contact_stiff_scale halved around its own center, everything else byte-identical (no slip-shaping reward active). Tests whether the composite's steady-state undisturbed-episode slip gap (baseline 4.2-5.7/m) is DR-band-driven, since 4 independent reward-shaping mechanisms are now closed 4/4. PASS-IMPLICATED if held-out slip_per_m in undisturbed episodes drops >=15% median vs baseline with gait_valid/falls holding. FAIL-EXONERATED if slip stays within noise. Confound: this is a retrain (2M adaptation), not a pure re-eval -- a PASS-IMPLICATED read should be corroborated by re-evaluating the frozen cont40m checkpoint at the same band (zero-spend) before funding more budget.

