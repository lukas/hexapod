# cw-walkscratch-easy0905-headset-crossgrav-medhead-dr-allaxiskickhalf-nocrutch1x-c1-acq1-cont40m-frictionband-half-s0

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: CANARY_PASS

**created**: 2026-09-07T12:46:26+00:00

**pod**: hexapod-mjx-train-4

**steps**: 2000000

**parent**: cw-walkscratch-easy0905-headset-crossgrav-medhead-dr-allaxiskickhalf-nocrutch1x-c1-acq1-cont40m

**wandb_id**: hd06097r

**hypothesis**: Plain English: is this composite's persistent ~5/m steady-state slip gap (present even in undisturbed episodes, all 4 reward-shaping fixes closed) caused by this DR axis's WIDTH, not the reward? Single lever vs the plain cont40m champion: friction_scale (0.6,1.4 -> 0.8,1.2, same center 1.0, half-width halved), halved around the same center. Prediction-if-true: held-out slip_per_m drops materially in undisturbed episodes with gait/falls holding. Prediction-if-false: slip stays flat -- axis exonerated, move to the next candidate (contact_stiff/gains) or accept the gap as this composite's hardening boundary (4th reward mechanism already closed).

**gate**: MECHANISM-HEALTH CANARY ONLY: do not judge skill acquisition, close a behavior/reward class, or require mature gait at this checkpoint. DR-BAND NARROWING CANARY (mechanism-health/diagnostic tier, not a skill verdict): retrains from the SAME cont40m champion under a single DR axis's band HALVED around its own center (everything else, incl. reward, byte-identical -- no slip-shaping reward term active, matching the plain champion baseline). Tests the 09-06 ~23:2x recommendation that this composite's persistent steady-state (undisturbed-episode) slip gap (baseline 4.2-5.7 m median in episodes with zero active kick/push) is DR-band-driven rather than reward-shaping-fixable (4 independent per-tick contact-slip reward mechanisms are now closed 4/4, most recently the properly-dose-scaled k=3 foot-slip-tangent lowdose arm, RL_LOG 09-06 20:15/21:0x). PASS-IMPLICATED if held-out gate slip_per_m in undisturbed episodes drops materially (>=15% median vs the 4.2-5.7 baseline range) while gait_valid/falls hold (no new chronic sacrifice, no new fall vs the champion's own clean 22/24-0-falls signature) -- names this axis a real contributor, licensing an ACQ-depth or fuller-removal follow-up. FAIL-EXONERATED if slip stays within noise of baseline despite the narrower band -- rules the axis out. Confound (recorded honestly): this is a retrain (2M fresh adaptation steps), not a pure re-eval of the frozen checkpoint under a narrower eval-time band, so a PASS-IMPLICATED read should be corroborated by re-evaluating the ORIGINAL frozen cont40m checkpoint at the same narrowed band (zero-spend, --cfg-set only) before funding further budget.

**verdict**: CANARY PASS (mechanism healthy: reward rose cleanly 9->404 across quarters, no crash/NaN, 2M steps completed). Scientific reading (mechanism-health tier, informational only, not a skill verdict): FAIL-EXONERATED for the friction_scale-band-width hypothesis. Halving the DR band (0.6-1.4 -> 0.8-1.2, same 1.0 center) does NOT reduce the composite's steady-state slip gap -- gait_valid 22/24, numerically the SAME total AND the SAME episode-level fingerprint as the frozen parent cont40m champion's own DR-0 gate (leg2 sacrifice at walk/sto ep4 AND walk_startjitter/det ep1 in both, nothing else). slip_per_m med 4.98/4.68/4.79/5.50 across the 4 modes vs champion's own 4.98/5.17/5.10/5.42 -- within noise, no mode clears the >=15% drop bar. Verified via kubectl ps that the eval genuinely applied the narrowed dr.friction_scale=0.8,1.2 cfg (checkpoint's own baked-in DR overrides force randomize=True regardless of the --dr-scale=0.0 CLI flag -- this composite's DR is a permanent cfg property, not eval-time-gated). Rules out friction_scale band width as the driver of the persistent undisturbed-episode slip gap (1/2 seeds; s1 sibling still evaluating on its own pod under another cycle's kick -- left for that reader, do not duplicate).

