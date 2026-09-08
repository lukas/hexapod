# cw-assistfade-rung3-legdutyratio-s0

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: CANARY FAIL - MECHANISM

**created**: 2026-09-08T02:21:09+00:00

**pod**: hexapod-mjx-train-0

**steps**: 2000000

**parent**: cw-assistfade-rung3-residualfade-s0

**wandb_id**: fhzonqmd

**hypothesis**: Does reward.walk_leg_duty_ratio_charge (the new additive per-leg utilization price, bank-proved + already CANARY PASS 3/3 fresh-init on walkcurr/easy0905) fix assistfade rung3's chronic leg-sacrifice-plus-high-slip-drift FAIL on REAL mesh/100Hz physics? Single lever vs the already-FAIL bare cw-assistfade-rung3-residualfade-s0 baseline: adds the charge (dose150, target0.30, grace3s, tau1s -- the exact validated walkcurr dose), otherwise byte-identical (same residual-blend schedule t1_steps=1.4M, same log-std anneal, random-weight init, seed0). This is the track's own named next design lead (TRACK-LEVEL FINDING 09-07 ~14:5x: 'a genuinely new reward mechanism pricing per-leg utilization/load-slip directly'), tried here for the first time on this track.

**gate**: MECHANISM-HEALTH CANARY ONLY: do not judge skill acquisition, close a behavior/reward class, or require mature gait at this checkpoint. MECHANISM-HEALTH canary (2M, matches the bare-rung3 baseline's own budget for a clean single-lever comparison), not an ignition-gate claim. Read env/walk_leg_duty_ratio_shortfall / reward_walk_leg_duty_ratio in wandb_history.csv first to confirm the charge actually engages (non-zero after the 3s grace) -- if it never engages, this is CANARY FAIL - INFRASTRUCTURE, not a mechanism verdict. If it engages: compare held-out walk/det+sto (DR-0) against the bare-rung3-s0 baseline's own report.json -- PASS-if the chronic single/double-leg sacrifice (legs [0,3] in the matched nostdanneal read) measurably narrows or resolves (per-leg duty >=0.10 where the baseline showed <0.05) without new falls or a worse slip/current signature; note separately whether the schedule-collision drift-into-high-slip pattern also improves (bonus, not required for this canary's own verdict). FAIL-MECHANISM if per-leg duty is statistically indistinguishable from the undosed baseline (self-check exactly like the walkcurr retrofit arm's own episode-by-episode diff, per that arm's self-correction lesson) or the run is outright worse (new falls, gait_valid regression). Do not claim rung3 ignition passes from a 2M canary -- a longer acquisition-budget continuation (mirroring the already-run longbudget lever, 6M) is the next step only if this canary shows real per-leg engagement.

**verdict**: CANARY FAIL - MECHANISM: This canary does not improve its matching assisted baseline and is not ready for hardware. CANARY FAIL - matched health regression, not a reward-class closure. Exact cw_assistfade_rung3_residualfade_s0_gate and new cw_assistfade_rung3_legdutyratio_s0_gate both use policy_std0.052, the same normalized launch recipe apart from the four added charge settings, 100Hz motor contract and4.80573kg model. Gait-valid groups go[6,6,2,2] to[6,6,2,1] (16/24 to15/24); simulated over_current terminations go7 to9, not classified as physical falls. Nominal deterministic progress improves0.119 to0.142 and slip/m16.711 to12.674; stochastic progress mean0.106333 to0.103333 and slip/m15.9655 to16.3193 do not improve. Thus the pre-registered no-regression clause is not met, despite that mixed deterministic gain and confirmed charge engagement. This is not a claim of statistical equivalence or universal impossibility. The earlier7-to15 recovery/DIG-IN premise compared against the separate nostdanneal descendant(std0.422); its chronic legs0/3 are not the matched baseline. The true nominal baseline already had12/12 gait-valid with no sacrificed legs. Reviewed the exact new walk_det_0 contact sheet: posture remains nearly stationary with little body translation across10s, consistent with low command progress. No automatic longer continuation from the false recovery premise; future mechanism work remains authorized under existing gates. Hardware-ready:no.

