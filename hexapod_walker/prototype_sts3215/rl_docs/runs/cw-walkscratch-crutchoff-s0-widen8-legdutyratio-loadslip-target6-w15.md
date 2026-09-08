# cw-walkscratch-crutchoff-s0-widen8-legdutyratio-loadslip-target6-w15

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: INTENT

**created**: 2026-09-08T15:10:28+00:00

**pod**: hexapod-mjx-train-0

**steps**: 2000000

**parent**: cw-walkscratch-crutchoff-s0-widen8-legdutyratio-loadslip-target6

**hypothesis**: Plain English: the recalibrated target=6.0 load-slip-ratio charge fixed the saturation bug but still missed the pre-registered efficacy bar (2/4 groups on this seed), and the run's own reward telemetry shows why -- ep_rew_mean collapses by tens of thousands purely from this charge's own uncapped weight=150 dominating the raw PPO objective without moving the exported best-checkpoint's actual eval behavior much. This tests the other named repair: keep the fixed target=6.0 but cut the weight 10x (150->15) so the charge can still price excess load-slip without swamping every other reward term (freeprog, action-delta, termination) in the objective. If a much lower weight lets efficacy clear >=3/4 groups with a healthy (non-collapsing) reward curve, weight was the real problem, not the mechanism. If efficacy stays flat/worse at 15, weight was not the limiting factor either and this per-leg mechanism needs a structurally different design, not further dose tuning.

**gate**: MECHANISM-HEALTH CANARY ONLY: do not judge skill acquisition, close a behavior/reward class, or require mature gait at this checkpoint. MECHANISM-HEALTH CANARY: PASS if reward stays healthy (no order-of-magnitude late-training collapse vs the matched guardfix1 baseline's own quarter-over-quarter trend) AND >=3/4 of the 4 held-out groups (walk/det, walk/sto, walk_startjitter/det, walk_startjitter/sto) jointly improve slip AND progress vs the matched 0.30-duty-dose guardfix1-s0 baseline with 0 new falls -- licenses a cont10m depth read and a matched n=3 seed batch at this weight. FAIL (still <3/4 groups, or reward still collapses) closes the weight-reduction branch too, leaving only a genuinely new per-leg mechanism design as the open lead.

