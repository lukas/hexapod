# cw-walkscratch-easy0905-headset-crossgrav-medhead-dr-allaxiskickhalf-nocrutch1x-c1-acq1-cont40m-compliance-half-s0

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: CANARY_PASS

**created**: 2026-09-07T12:52:22+00:00

**pod**: hexapod-mjx-train-4

**steps**: 2000000

**parent**: cw-walkscratch-easy0905-headset-crossgrav-medhead-dr-allaxiskickhalf-nocrutch1x-c1-acq1-cont40m

**wandb_id**: 6yyhv3vz

**hypothesis**: Plain English: is this composite's persistent ~5/m steady-state slip gap (present even in undisturbed episodes, all 4 reward-shaping fixes closed) caused by this DR axis's WIDTH, not the reward? Single lever vs the plain cont40m champion: contact_stiff_scale (0.7,2.0 -> 1.025,1.675, same center 1.35, half-width halved). Seed 0 of a 2-seed pair (s1 companion). Prediction-if-true: held-out slip_per_m drops materially in undisturbed episodes with gait/falls holding. Prediction-if-false: slip stays flat -- axis exonerated, move to the next candidate (gains) or accept the gap as this composite's hardening boundary.

**gate**: MECHANISM-HEALTH CANARY ONLY: do not judge skill acquisition, close a behavior/reward class, or require mature gait at this checkpoint. DR-BAND NARROWING CANARY (mechanism-health/diagnostic tier): retrains from the SAME cont40m champion under contact_stiff_scale halved around its own center, everything else byte-identical (no slip-shaping reward active). Tests whether the composite's steady-state undisturbed-episode slip gap (baseline 4.2-5.7/m) is DR-band-driven, since 4 independent reward-shaping mechanisms are now closed 4/4. PASS-IMPLICATED if held-out slip_per_m in undisturbed episodes drops >=15% median vs baseline with gait_valid/falls holding. FAIL-EXONERATED if slip stays within noise. Confound: this is a retrain (2M adaptation), not a pure re-eval -- a PASS-IMPLICATED read should be corroborated by re-evaluating the frozen cont40m checkpoint at the same band (zero-spend) before funding more budget.

**verdict**: CANARY PASS (mechanism healthy: reward rose cleanly 30.5->421.9 across quarters, no crash/NaN, 2M steps completed). Scientific reading: FAIL-EXONERATED. gait_valid 22/24, numerically the SAME total and the SAME episode-level fingerprint as the frozen parent cont40m champion (leg2 sac at walk/sto ep4 AND walk_startjitter/det ep1, nothing else). slip_per_m med 4.94/5.07/5.02/5.46 vs champion's own 4.98/5.17/5.10/5.42 -- within noise on every mode. 1/2 seeds FAIL-EXONERATED for the contact_stiff_scale band-width axis (s1 sibling still evaluating on its own pod, left for that reader). Combined with the frictionband/gainsband 2/2-seed closures this cycle, ALL THREE item(4) DR-band axes now read the same way: narrowing the band around its own center does not reduce the composite's steady-state slip gap. Working synthesis (pending compliance-half-s1's confirmation): the persistent 4-5/m undisturbed slip is likely NOT a DR-band-width effect at all -- next lever should look elsewhere (e.g. contact/friction MODEL fidelity itself, foot geometry, or accepting the gap as a floor of this composite's gait style) rather than further band-narrowing variants.

