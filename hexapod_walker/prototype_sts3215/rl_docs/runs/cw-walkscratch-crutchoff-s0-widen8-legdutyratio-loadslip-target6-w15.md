# cw-walkscratch-crutchoff-s0-widen8-legdutyratio-loadslip-target6-w15

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: FAIL

**created**: 2026-09-08T15:10:28+00:00

**pod**: hexapod-mjx-train-0

**steps**: 2000000

**parent**: cw-walkscratch-crutchoff-s0-widen8-legdutyratio-loadslip-target6

**wandb_id**: of5b0lr6

**hypothesis**: Plain English: the recalibrated target=6.0 load-slip-ratio charge fixed the saturation bug but still missed the pre-registered efficacy bar (2/4 groups on this seed), and the run's own reward telemetry shows why -- ep_rew_mean collapses by tens of thousands purely from this charge's own uncapped weight=150 dominating the raw PPO objective without moving the exported best-checkpoint's actual eval behavior much. This tests the other named repair: keep the fixed target=6.0 but cut the weight 10x (150->15) so the charge can still price excess load-slip without swamping every other reward term (freeprog, action-delta, termination) in the objective. If a much lower weight lets efficacy clear >=3/4 groups with a healthy (non-collapsing) reward curve, weight was the real problem, not the mechanism. If efficacy stays flat/worse at 15, weight was not the limiting factor either and this per-leg mechanism needs a structurally different design, not further dose tuning.

**gate**: MECHANISM-HEALTH CANARY ONLY: do not judge skill acquisition, close a behavior/reward class, or require mature gait at this checkpoint. MECHANISM-HEALTH CANARY: PASS if reward stays healthy (no order-of-magnitude late-training collapse vs the matched guardfix1 baseline's own quarter-over-quarter trend) AND >=3/4 of the 4 held-out groups (walk/det, walk/sto, walk_startjitter/det, walk_startjitter/sto) jointly improve slip AND progress vs the matched 0.30-duty-dose guardfix1-s0 baseline with 0 new falls -- licenses a cont10m depth read and a matched n=3 seed batch at this weight. FAIL (still <3/4 groups, or reward still collapses) closes the weight-reduction branch too, leaving only a genuinely new per-leg mechanism design as the open lead.

**verdict**: CANARY FAIL - MECHANISM (closes the weight-reduction branch per its own gate text): cutting walk_leg_loadslip_ratio_charge weight 150->15 (10x) does NOT fix either half of the gate's own bar. (1) Reward health: quarters [34.6, 50.5, -986.7, -4068.7] still collapse ~3 orders of magnitude in the back half -- smaller in absolute size than the weight=150 parent's [34.0, 56.1, -1058.2, -6806.0] but the SAME qualitative shape (healthy first half, catastrophic collapse second half), not the 'stays healthy' bar. (2) Efficacy: vs the matched weight=150 parent (walk/det slip 9.55/fwd 0.61m, walk/sto slip 7.37/fwd 1.00m, walk_startjitter/det slip 9.17/fwd 0.66m, walk_startjitter/sto slip 12.37/fwd 0.59m gv4/6), w15 reads walk/det slip 10.24/fwd 0.52m (worse both), walk/sto slip 7.81/fwd 1.00m (worse slip, flat fwd), walk_startjitter/det slip 9.70/fwd 0.80m (worse slip, better fwd -- mixed), walk_startjitter/sto slip 12.37/fwd 0.50m gv4/6 (flat slip, worse fwd) -- 0/4 groups jointly improve both slip AND progress, all differences are noise-level, not the >=3/4 bar. 0 new falls (matches parent). Contact sheet confirms this is the mature/entrenched-exploiter lineage (genuine forward translation across all 10 frames, unlike the frozen fresh-init runs), so the eval is reading real walking behavior, not a stationary artifact. Net: a 10x weight cut changes the reward-collapse MAGNITUDE but not the exported checkpoint's actual behavior or the mechanism's efficacy -- weight scale is not the limiting factor. CLOSES the weight-reduction branch on this mechanism (per this gate's own text); the sibling w45 (intermediate weight=45, same cycle) brackets this from the other side. Next licensed move: a genuinely new per-leg mechanism design, not further dose tuning of walk_leg_loadslip_ratio_charge.

