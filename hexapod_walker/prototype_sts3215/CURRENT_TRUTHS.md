# CURRENT TRUTHS - accepted facts and rulings

Last compacted: 2026-08-30 for the `todaypolicy` sixth-track update.
Archive copy: `archive/CURRENT_TRUTHS_2026-08-30_pre_todaypolicy_compaction.md`.
Accepted facts, not narrative. If old prose disagrees, this file wins.

## Mission
Six registered tracks live in `rl_move/orchestrator/tracks.json`:
- `joystick`: RL from scripted gait to joystick control.
- `amp`: from-scratch AMP program; done at MuJoCo transfer M5.
- `cpg`: direct low-dimensional CPG/SE2 controller search.
- `walkcurr`: prior-free PPO walking; no BC, gait clock, or motion prior.
- `standwalk`: keep trying for ONE mesh/100 Hz policy that can sit,
  rise, joystick-walk, and lower.
- `todaypolicy`: deliver a useful policy-controlled MuJoCo/controller
  bundle today. It may compose policy+state pieces and does not mark
  `standwalk` green.
Out-of-scope operator runs get honest triage but no agent follow-ups.

## Today Answer
- DELIVERED 2026-08-30: `todaypolicy-mlpsf-tuck-v1` packaged, all TODAY
  bars PASS on a fresh controller-side full-mesh regen; GO for
  controller handoff. Durable evidence + GO/NO-GO + selector path:
  `rl_docs/tracks/todaypolicy/bundle_mlpsf_tuck_v1/`.
- Bundle candidate: `todaypolicy-mlpsf-tuck-v1`.
- Stand/lower role: scripted tuck by default; compare learned
  `stand_stancemix_tuckclock_scratch8m{,_s1}` when useful.
- Walk role: `cw-walk-allheading-mlp-singleframe-acq1-stdanneal`,
  exported as `linux_control/policies/walk_allheading_mlp_singleframe_acq1_stdanneal.json`.
- Full-mesh evidence (`logs/manual_drive/cw_walk_allheading_mlp_
  singleframe_stdanneal_hybrid_tuck_ux_human28/`): zero falls, no
  sacrificed legs, progress_ratio 0.418, course_err_1s_med 2.57deg,
  wrong_course_frac 0.0. Stable and obedient, but speed-soft.
- Upgrade candidate: `cw-walkteach-scripted-allhead-acq12m{,-s1}`.

## Model And Control Contracts
- New PPO/MJX launches use mesh-family 100 Hz unless a registered
  legacy exception says otherwise.
- Checkpoints started before the 2026-08-24 mesh flip are
  primitive-family 25 Hz policies. Do not warm-start or evaluate them
  as mesh/100 Hz unless explicitly proven.
- `control_hz` metadata must match the runner; missing metadata means
  legacy 25 Hz. Policies output 18 raw joint targets through SafetyLayer.
- Long PPO acquisition launches should set `--log-std-final` from the
  start; uncapped `train/std` repeatedly ruined stochastic rollouts.

## Run Interpretation
- Video and gate eval outrank reward alone.
- Simulated over_current is UNCALIBRATED (operator 09-04,
  fb_20260904T074505): a bit-exact 2.64 A pin is the actuator
  forcerange rail image (2.2 N*m x 1.2 A/N*m), not a measured stall;
  at trip threshold 2.9 the estimator (railing at 2.64) can never
  trip. Rail hits alone never fail a run or close a mechanism —
  corroborate with `audit_over_current.py` (CORROBORATED_STALL vs
  RAIL_MOVING) and report current telemetry separately. Evidence:
  `logs/ckpt_eval/oc_audit_09-04/OC_AUDIT_SUMMARY.md`. Real-robot
  protections stay untouched.
- Compare reward trend to gate/eval trend before spending more. Rising
  reward with flat/bad eval means audit reward, eval, simulator, or
  tooling before same-recipe seed sweeps.
- Bad eval with both reward and eval improving may justify continuation.
- Known exploit on video is a metric/tooling bug to repair, not a
  lineage kill by itself.
- walkcurr easy0905 bare recipe (freeprog income only,
  k_park_duty/k_walk_idle_charge/k_loadslip_excess all 0) + gSDE
  (`--use-sde`) reliably converges to a SACRIFICED-LEG QUADRUPED
  SHUFFLE at full gravity: 1-2 legs chronically airborne (duty
  0.00-0.23, single-digit ground touches per 20s episode) while the
  remaining legs take ~7mm micro-strides — clears the raw
  >=0.03 m/s floor and racks up near-full-episode reward (0 falls)
  while `gait_valid`-style checks fail and slip/m runs ~1.7-1.8x the
  2.9 teacher band. Confirmed on 3/3 full-gravity sde seeds
  (sde-s0-c4, sde-s1-c2, sde-s2-c2, 09-05) — gSDE-specific: the
  non-gSDE base/halfgrav families train cleanly under the identical
  bare recipe (4/4 ACQ PASS, six-leg video-confirmed). This is the
  SAME behavioral class the `WALKCURR_PF_IDLE_TERM` bank
  (`test_task_semantics.py`, 08-24) already diagnosed on the older
  pf_fwd lineage: soft anti-park prices ALONE leave the degenerate
  stance as PPO's cheapest optimum; the validated fix pairs
  `k_park_duty`/`k_walk_idle_charge`/`k_loadslip_excess` WITH a
  qvel-based `safety.walk_idle_terminate_s` termination. UPDATE 09-05
  ~13:1x: that qvel-idle-terminate port was tried
  (`cw-walkscratch-easy0905-sde-idleterm-{s0,s1}`, 2M canaries) and
  CLOSED — CANARY FAIL, detector-gamed not repaired: W&B scalars look
  escape-shaped (the `walk_idle_terminate` termination reason
  disappears from the final checkpoint's rollout captions,
  `ep_len_mean` triples) but the downloaded final-checkpoint video on
  both seeds shows the SAME static splayed-leg frozen pose as
  `sde-s0-c4` (on-screen speed 0.001-0.032 m/s, no leg mid-swing) —
  enough qvel/servo jitter dodges the specific threshold without the
  underlying pathology resolving into six-leg walking. Do not relaunch
  this qvel-idle-terminate variant on the sde family; the family's
  sole active repair candidate is now the structural
  `reward.walk_gait_gate` (`sde-s1-c3gg`/`sde-s2-c3gg`, already
  funded/training; `sdehalfgrav-remcost-*-gg*` mirrors it for the
  halfgrav+gSDE cell) — if that also fails, no cheap repair variant
  remains untried and a genuinely new per-leg-utilization pricing
  mechanism needs its own design+bank pass before further sde spend.
  Separately: `reward.walk_gait_gate` and
  `reward.k_walk_move_current` were tried against a related
  leg-sacrifice/rigid-tripod-lock exploit on the joystick track's
  harder full-DR `joyfullcurr13` curriculum (RL_LOG 08-25) and BOTH
  were CLOSED (made the fall rate worse, at every dose/architecture
  tried) — do not relaunch either lever here without accounting for
  that prior closure.
  UPDATE 09-05 ~14:3x: the `walk_gait_gate`+`k_step_event` structural
  repair (`sde-s1-c3gg`/`sde-s2-c3gg`) is now CLOSED too — 2/2 seeds
  ACQ FAIL (misaligned). It DOES partially work (multi-leg sacrifice
  narrows to exactly one chronically-parked leg per seed, duty 0.0,
  ~3 swings/20s) but harness `gait_valid` is still 1/24 and 0/24. Root
  cause read directly from `wandb_history.csv`: `env/walk_gait_gate_
  factor` sits at 0.98-0.99 for the ENTIRE back half of training even
  though the harness's stricter duty>0.10 bar flags the same leg as
  sacrificed the whole time — the reward-side gate's "recently
  completed swing" scoring window is satisfied by a rare token swing
  every several seconds and never drives the MIN-over-legs factor down
  the way a true duty-cycle price would. This is the SAME
  rare-token-dodge shape already seen on the qvel-idle-terminate
  lever, just via a different threshold. Both named bare-sde repair
  levers (idle-terminate, gait-gate) are now closed 2/2 each — per the
  09-05 ~13:1x note above, no cheap repair variant remains untried;
  any further sde revival needs a genuinely new per-leg-utilization
  mechanism (e.g. a hard minimum-duty/minimum-swing-count price, not a
  completion-score the policy can satisfy with one swing per many
  seconds) with its own design+bank pass. `sdehalfgrav-remcost-{s0,s1}
  -gg2` (same lever ported onto the remcost recipe) were left running,
  not preemptively killed — read their own report.json before assuming
  the same fate; the remcost recipe already prices term_cost
  differently and may not share the exact failure mode. Evidence:
  `logs/ckpt_eval/cw_walkscratch_easy0905_sde_s{1,2}_c3gg_gate/
  report.json`, `logs/experiments/cw-walkscratch-easy0905-sde-s{1,2}-
  c3gg/wandb_history.csv`, W&B notes on `zr5lg756`/`vb2m7gr2`.
  UPDATE 09-05 ~14:4x: those two `sdehalfgrav-remcost-{s0,s1}-gg2`
  arms landed and it does NOT get a pass on remcost's different term
  pricing — both ACQ FAIL (misaligned), the SAME fingerprint (legs
  1/4 chronically parked, duty 0.0-0.03 nearly every episode,
  `gait_valid` 2/24 both seeds, `env/walk_gait_gate_factor` SATURATED
  at 0.985-1.0 for essentially the whole 40M run rather than a real
  ~0->1 climb). Video (`walk_det_0.png` contact sheets, both runs)
  shows the identical splayed-rigid-leg drag as the bare-sde FAILs.
  The `walk_gait_gate`+`k_step_event` lever is now CLOSED 4/4 across
  every recipe tried (bare sde x2, sdehalfgrav+remcost x2) — do not
  relaunch it anywhere in the sde/sdehalfgrav family; the per-leg-
  utilization pricing design question is fully open again pending a
  genuinely new mechanism (hard minimum-duty/swing-count price, not a
  gameable completion score). Evidence: `logs/ckpt_eval/
  cw_walkscratch_easy0905_sdehalfgrav_remcost_s{0,1}_gg2_gate/
  report.json`, `wandb_history.csv` for both runs, W&B notes
  `wrc80ii4`/`dq6gfe29`.
  UPDATE 09-05 ~15:4x: the remaining two bare-sde gg seeds
  (`sde-s0-c4gg`, `sde-s3-c1bgg`) landed and FAIL the same way --
  `gait_valid` 0/24 and 0/24 primary det (1/24 overall for c1bgg),
  legs [1]/[1,4] chronically parked, `env/walk_gait_gate_factor`
  saturated 0.81-1.0 (c1bgg) / 0.97-1.0 (c4gg) despite the sacrifice.
  **The `walk_gait_gate`+`k_step_event` repair is now CLOSED 6/6,
  fully confirmed across every bare-sde/sdehalfgrav-remcost seed
  tried -- do not relaunch it anywhere in this family.** The only
  surviving repair candidate is the newer `reward.walk_duty_gate`
  mechanism (per-leg trailing-duty income gate, built 09-05 ~15:1x,
  bank-proved in `test_walkscratch_easy_pilot.py`); its first 5
  canaries (`headset-base-s0c1-dgate-c1`, `sde-{s1,s2}-dg1`,
  `sdehalfgrav-remcost-{s0,s1}-dg1`) are mid-gate-eval as of this
  update -- read those before trying any further gait-gate variant.
  Evidence: `logs/ckpt_eval/cw_walkscratch_easy0905_sde_{s0_c4,
  s3_c1b}gg_gate/report.json`, W&B `q2kox1j4`/`bzf8msie`.
  UPDATE 09-05 ~16:0x, CORRECTED ~16:2x (provenance): 3 of those 5
  `walk_duty_gate` first-canary verdicts landed (`sde-s2-dg1`,
  `sdehalfgrav-remcost-{s0,s1}-dg1`) — all 3 **CANARY FAIL**, but per
  the respec-clone provenance gotcha directly above, NONE of them
  actually warm-started off a mature converged exploiter as first
  written: `sde-s2-dg1`'s real `--init-from` is `sde_s2.zip`, the
  ORIGINAL 2M canary that TERMINATES tilt_pitch (falls) in every
  single eval episode, not the 40M `sde_s2_c2.zip` exploiter; both
  `sdehalfgrav-remcost-{s0,s1}-dg1` carried NO `--init-from` at all —
  fully FROM SCRATCH with `reward.walk_duty_gate=1.0` from step 0.
  Re-reading with the correct ancestry: the gate factor itself
  behaved correctly (declined 0.69-0.92, i.e. penalizing, not
  saturating/gamed) and det-mode `gait_valid`/`sac` genuinely cleared
  (no chronically-parked leg) on all three — the specific one-leg-park
  exploit is prevented from forming at all. What emerged instead
  within the 2M budget was a DIFFERENT non-walking failure, split by
  recipe: `sde-s2-dg1` (from the falls-every-episode 2M ancestor)
  made real progress — stopped falling in det — but ends each episode
  having yawed ~174deg from start with current 0.30A->1.40A (a
  spin/destabilize pattern, not directed travel), falls 5/6 in sto;
  both `sdehalfgrav-remcost-{s0,s1}-dg1` (from scratch, remcost's
  term_cost pricing + duty_gate together) go to a FULL FREEZE (v
  0.001-0.037 m/s, net displacement 0.00-0.01m over the whole 20s det
  episode, slip 20-75x the ~2.9 band from leg micro-vibration with no
  net travel, falls 6/6 in sto) — a leg that never lifts keeps duty
  near 1.0, comfortably clearing the 0.15 floor even cheaper than a
  real gait (which necessarily drops a swinging leg's duty below
  ceiling), so full stasis is a strictly EASIER way to satisfy
  `walk_duty_gate` than walking is, AND this matches the remcost
  recipe's own launch hypothesis, which explicitly predicted "retreat
  to the ~0-income park basin" as its failure mode if term_cost
  pricing over-corrects toward fall-aversion — now confirmed directly
  from scratch, no warm-start confound needed. Reward for the remcost
  pair tracks their UN-gated from-scratch parents' own trajectories at
  matched absolute env steps almost exactly (not a new collapse from
  duty_gate; remcost is already this negative on its own).
  **Diagnosis: closes "walk_duty_gate=1.0 on the early
  falls-every-episode sde_s2 2M checkpoint" (n=1) and "walk_duty_gate
  =1.0 + remcost term_cost pricing, from scratch" (n=2) as repair
  recipes** — do not relaunch either exact combination; still NOT
  proof the `walk_duty_gate` mechanism itself is unsound absent
  remcost's fall-aversion pricing, since remcost's own term_cost is a
  plausible independent contributor to the freeze. Launched the
  disambiguating pair this cycle (from scratch, NO remcost pricing,
  NO inherited checkpoint at all): `cw-walkscratch-easy0905-sde-
  dgfresh-s0` / `-sdehalfgrav-dgfresh-s0` (2M canaries, `reward.
  walk_duty_gate=1.0` from step 0, otherwise identical to `sde-s0`/
  `sdehalfgrav-s0`) — read those before trying any further
  `walk_duty_gate` variant. If fresh init (no remcost) ALSO
  freezes/spins, the mechanism needs an explicit anti-idle complement
  (`reward.k_walk_idle_charge`, already implemented, 0 in every arm so
  far) paired with the duty floor before further spend, per this
  file's own note above that soft anti-park prices alone leave the
  degenerate stance as PPO's cheapest optimum. `sde-s1-dg1` /
  `headset-base-s0c1-dgate-c1` (the remaining 2 of the original
  5-canary batch) were not read this cycle — a concurrent cycle
  appears to own `sde-s1-dg1` (a sibling `cw-walkscratch-easy0905-sde-
  s1-c2-dgatefix` launch was found RUNNING on train-4 at cycle end,
  presumably that cycle's own repair attempt on this same finding —
  read its notes before assuming this entry is the last word; W&B logs
  show it already verdicted `sde-s1-dg1` itself as CANARY PASS
  scope-corrected, escapes LEGPARK in det with all-leg duty>=0.22).
  Evidence: `ops.sh review cw-walkscratch-easy0905-sde-s2-dg1` /
  `cw-walkscratch-easy0905-sdehalfgrav-remcost-s{0,1}-dg1`, W&B notes
  on the three verdicted runs (re-verdicted with FORCE=1 after the
  provenance correction).
  UPDATE 09-05 ~16:3x: the disambiguating fresh pair (+1 name-collision
  duplicate) all landed: `sde-dgfresh-s0`/`-s0b` (2 independent W&B
  runs, same recipe) and `sdehalfgrav-dgfresh-s0`, all **CANARY FAIL -
  MECHANISM (FULL FREEZE)**. `reward.walk_duty_gate=1.0` from step 0,
  NO remcost pricing, NO inherited checkpoint (fresh init) still
  converges to the identical fingerprint as the remcost dg1 pair: det
  walk fwd med 0.02-0.07m/20s, IDENTICAL to 2 decimals across all 6 det
  episodes (video-confirmed static splayed-leg pose, no leg mid-swing
  at any sampled tick), `env/walk_duty_gate_factor` saturated 0.92-1.0
  for the ENTIRE 2M run on all 3, `ep_rew_mean` quarters strictly
  worsening (not the 08-21 rising-reward-bad-eval case). **This closes
  the ambiguity for good: the freeze is intrinsic to `walk_duty_gate`
  itself** (a trailing-duty floor is trivially satisfied by keeping
  ALL SIX legs near-planted with zero net motion — cheaper than any
  real gait, which necessarily drops a swinging leg's duty below
  ceiling) — not an artifact of remcost's term_cost pricing, nor of
  warm-starting from an already-entrenched exploiter; both confounds
  are now independently ruled out. **`walk_duty_gate` alone is CLOSED
  as a from-scratch repair lever for the sde/sdehalfgrav leg-sacrifice
  pathology.** The sole remaining path is pairing it with
  `reward.k_walk_idle_charge` (the anti-park travel floor, already
  implemented, 0 in every arm to date) — this is a genuinely NEW
  design+bank pass (a joint duty-floor + travel-floor mechanism), not
  a relaunch of either lever alone; do not fund another bare
  `walk_duty_gate` arm (fresh OR entrenched-checkpoint) until that
  pass lands. The concurrent entrenched-checkpoint `dgatefix` batch
  (`sde-{s1,s2}-c2-dgatefix`, `sdehalfgrav-remcost-{s0,s1}-dgatefix`)
  is a separate confound (does duty_gate cure an ALREADY-entrenched
  exploiter) and should still be read on its own once it lands.
  Evidence: `ops.sh review cw-walkscratch-easy0905-{sde-dgfresh-s0,
  sde-dgfresh-s0b,sdehalfgrav-dgfresh-s0}`, W&B `8h25tu4l`/`vwnbmgq2`/
  `c3kd1elp`.
  UPDATE 09-05 ~16:4x: the from-scratch disambiguating pair landed —
  `sde-dgfresh-s0`/`-s0b` (accidental duplicate, same fingerprint) and
  `sdehalfgrav-dgfresh-s0` all **CANARY FAIL — FULL FREEZE**, 3/3 (a
  concurrent cycle's verdicts; independently corroborated here for
  `sde-dgfresh-s0`: det fwd 0.06m/20s across all 6 episodes, per-leg
  duty 0.75-0.96 but `stride_m_mean=0.001`/swing_count up to 302 in 20s
  — a high-frequency near-zero-amplitude leg vibration that satisfies
  the duty floor without producing a real step, not literal stillness).
  **Bare `walk_duty_gate` from scratch is now CLOSED**: the mechanism
  correctly prevents the one-leg-park exploit but a six-legs-all-
  planted (or all-vibrating) stance is a strictly cheaper way to clear
  a trailing-DUTY floor than any real gait, confirming the design note
  above. **CROSS-REFERENCE CORRECTION to the "Next: pair with
  k_walk_idle_charge" note every one of these three FAILs carried**:
  that pairing is NOT untested terrain — `cw-walkscratch-easy0905-sde-
  idleterm-{s0,s1}` (09-05 ~14:xx, FAIL) already ran `k_park_duty=4.0`
  + `k_walk_idle_charge=2.0` (`walk_idle_speed_m_s=0.025`, `tau_s=1.0`)
  + a HARD `safety.walk_idle_terminate_s=3.0` qvel-based cutoff on this
  exact sde/easy0905 base recipe, and STILL converged to the same
  static splayed-leg pose (on-screen speed 0.001-0.032 m/s): the
  qvel-based terminate got jitter-dodged (mean|qvel|>=2deg/s satisfied
  by servo micro-vibration with no coherent stepping — the SAME
  vibration-not-stride signature as the bare-duty-gate freeze above)
  and the soft idle-charge was simply paid down as an accepted ongoing
  cost, never escaped, within 2M. **Three independently-designed
  price/termination mechanisms now share one fate on this recipe**
  (`walk_gait_gate`+`k_step_event`; `k_park_duty`+`k_walk_idle_charge`+
  qvel-terminate; bare `walk_duty_gate`) — reward-shaping alone has not
  evicted the sde/easy0905 static-quiver absorbing basin within a 2M
  budget in 6 attempts. A `walk_duty_gate`+`k_walk_idle_charge` combo
  (dropping the dodgeable qvel-terminate, since idle-charge's own
  along-speed EMA prices BODY displacement not joint motion — a
  harder-to-fake signal) is a genuinely new combination and worth one
  more canary pair, but treat a 4th FAIL as closing "price-shaping
  alone" for this recipe and escalate to a structural intervention
  (BC/CPG-seeded init, a higher entropy/exploration schedule, or a
  moving-state curriculum start) rather than a 5th price variant.
  Launched: `cw-walkscratch-easy0905-sde-dgidle-{s0,s1}` (2M canaries).
  Evidence: `ops.sh review cw-walkscratch-easy0905-sde-dgfresh-s0`,
  `cw-walkscratch-easy0905-sde-idleterm-{s0,s1}` verdicts, W&B
  `8h25tu4l`.
  UPDATE 09-05 ~16:5x: 3 of the 4 entrenched-checkpoint `dgatefix` arms
  (`sde-s2-c2-dgatefix`, `sdehalfgrav-remcost-{s0,s1}-dgatefix` —
  `--init-from` verified pointing at each seed's real 40M LEGPARK
  checkpoint, not the provenance-bug-affected early ancestor) landed
  and all 3 are **CANARY FAIL - MECHANISM**, but with a THIRD distinct
  fingerprint, different from both prior closed patterns
  (saturating-factor-despite-sacrifice, and full-freeze): the factor
  genuinely DECLINES across training on all 3 (bare-sde 1.0->0.64,
  remcost-s0 1.0->0.72, remcost-s1 1.0->0.66 — real, ungamed
  penalizing pressure, not saturation) and there is no full-freeze —
  all 3 keep real forward speed (0.09-0.26 m/s) and net displacement
  (1.5-4.6m/20s). The mechanism is applying honest pressure to an
  already-entrenched exploiter; it just isn't enough to escape within
  2M. The two recipes diverge on reward direction though: bare-sde
  (`sde-s2-c2-dgatefix`) has ep_rew_mean quarters RISING throughout
  (94->224->332->406, the 08-21 rising-reward/bad-eval pattern — a
  genuine continue-candidate), while both remcost seeds have
  ep_rew_mean quarters WORSENING (-344->-495, -322->-582 — the
  exploiter absorbing more penalty for the same frozen 2-leg-park
  behavior without any escape appearing). All 3 stay at harness
  walk/det `gait_valid` 0/6 with the SAME 1-2 legs stuck at 0.00-0.01
  duty the whole clip (leg 1 alone for bare-sde; legs 1+4 for both
  remcost seeds — same leg pair both remcost seeds, suggesting a
  structural rather than random exploit). **Read together with the
  concurrent cycle's still-unverdicted `sde-s1-c2-dgatefix` (DIG-IN
  flagged, factor also declining 1.0->0.54, harness pending at time of
  writing) this makes 3/4 (soon 4/4) of the entrenched-checkpoint
  batch FAIL the 2M funding bar** — but unlike the from-scratch
  `dgfresh`/bare-`walk_duty_gate` closures, none of these show the
  mechanism being gamed; they show it working exactly as designed but
  arriving too late against a checkpoint that already spent 40M steps
  entrenching the sacrifice. This argues the next lever for the
  entrenched-checkpoint case specifically is a LONGER continuation of
  the most promising arm (`sde-s2-c2-dgatefix`, rising reward, no
  worsening) rather than a new mechanism — do not relaunch bare
  `walk_duty_gate` variants on these exact checkpoints without either
  (a) a longer budget on the one rising-reward seed, or (b) waiting
  for `sde-s1-c2-dgatefix`'s own harness read to complete the n=4
  picture. Evidence: `ops.sh review cw-walkscratch-easy0905-{sde-s2-
  c2-dgatefix,sdehalfgrav-remcost-s0-dgatefix,sdehalfgrav-remcost-s1-
  dgatefix}`, W&B `jw13d0rn`/`mmbhvbzs`/`m9sj7qzp`.
  UPDATE 09-05 ~17:2x: both `walk_duty_gate`+`k_walk_idle_charge`
  fresh-from-scratch canaries landed — `sde-dgidle-{s0,s1}` 2/2
  **CANARY FAIL — FULL FREEZE/VIBRATION** (s0: det fwd med 0.047m/20s,
  stride_m_mean 0.001m, duty 0.78-0.98 on all six legs via
  high-frequency in-place vibration not stride, slip_per_m 95.97 —
  33x the 2.9 band; sto/startjitter modes fall more, not less, 5-6/6
  terminations). **This closes reward-shaping-alone repair for the
  bare-sde/easy0905 LEGPARK-SKATE pathology for good: 6 independently
  designed price/termination mechanisms now FAIL (walk_gait_gate+
  k_step_event 6/6, k_park_duty+k_walk_idle_charge+qvel-terminate 2/2,
  bare walk_duty_gate fresh 3/3, walk_duty_gate on entrenched
  checkpoints 4/4 below funding bar, walk_duty_gate+k_walk_idle_charge
  fresh 2/2).** No further gSDE price/termination variant should be
  funded. Per this campaign's OWN launch hypothesis (`sde-s0`'s notes,
  verbatim: "ONLY change vs base-s0 is --use-sde"), the controlled A/B
  this closure needs was already run at launch time: the identical
  bare recipe passes ACQ cleanly on the non-gSDE base/halfgrav
  families (4+/4, six-leg video-confirmed) and fails on every gSDE
  seed tried (7+). **gSDE is the confirmed causal ingredient — CLOSE
  the gSDE sub-lineage entirely** (no further from-scratch or repair
  spend); the one live exception is `sde-s2-c2-dgatefix-cont40m`
  (entrenched-checkpoint, genuinely rising reward, 08-21-justified,
  already funded/running) — let it finish as a sunk-cost read, fund no
  NEW gSDE arms after it. Remaining walkcurr GPU budget belongs to the
  working base/halfgrav (Gaussian) curriculum ladder. Evidence:
  `logs/ckpt_eval/cw_walkscratch_easy0905_sde_dgidle_s0_gate/
  report.json`, RL_LOG 09-05 17:2x, W&B `4ubnoqq3`.
  UPDATE 09-05 ~17:3x: `sde-dgidle-s1` (seed 1) independently confirms
  the SAME fingerprint — harness det walk fwd=0.10m/20s (IDENTICAL
  across all 6 episodes, deterministic), stride_m_mean 0.001m, duty
  0.72-0.97 on all six legs (high-frequency vibration not stride,
  matching `sde-dgidle-s0`'s own read) — the gSDE sub-lineage closure
  above is now n=2/2 on this exact price combo, not n=1. **Separately,
  the two non-gSDE `headset-{base,halfgrav}-fullhead-c1` full-8-way
  heading canaries (Gaussian families, NOT part of the gSDE closure)
  landed with a verdict CORRECTION worth recording**: the harness
  shows `gait_valid` 22/24 and 24/24 respectively (six legs cycling,
  forward_dist_m 2.3-3.4m/20s in EVERY episode, zero det falls) — a
  real, stable six-leg gait, not a collapse, contrary to what the
  training-rollout W&B averages alone suggested (`env/v_along_cmd_m_s`
  ~0.01 the whole run). The actual failure is course-tracking:
  `success` 0/24 both arms (walkcurr's own bar needs vel_err_mean
  <=0.03) because `direction_err_mean_deg` swings 28-161deg
  episode-to-episode as the 8-way command resamples — episodes near
  the original {0,+-45} training set track well (direrr 28-48deg,
  POSITIVE return, progress_ratio 1.3-2.4) while episodes drawing
  quarter-turn/reversal headings degrade hard (direrr 86-161deg,
  return down to -6416, negative progress_ratio). This is
  distance-graded generalization, not a binary break, and reconciles
  the W&B-only read (batch-averaged across all 8 headings including
  the badly-tracked ones). Both verdicts were corrected in place
  (FORCE=1) after this landed. Built + bank-proved the missing
  intermediate rung: `EASY_HEADING_MED` (5-way: 0,+-45,+-90, NO
  reversal beyond a quarter turn) in `test_walkscratch_easy_pilot.py`,
  5 new tests, 37/37 green (`walkcurr-headingmed-bank-0905` snapshot,
  pushed). Launched 2M canaries warm-started from each family's own
  small-set heading champion: `headset-base-medhead-c1` (train-1),
  `headset-halfgrav-medhead-c1` (train-2), both VERIFIED RUNNING —
  read those before attempting the full 8-way jump again on either
  family. Evidence: `ops.sh review cw-walkscratch-easy0905-sde-dgidle-
  s1`, `logs/ckpt_eval/cw_walkscratch_easy0905_headset_{base,halfgrav}
  _fullhead_c1_gate/report.json`, W&B `q3vgzdlu`/`a0zu90u6`/`xiajh8ja`.
  UPDATE 09-05 ~18:2x: `sde-s2-c2-dgatefix-cont40m` (the one live
  gSDE exception kept running as a sunk-cost read per the ~17:2x
  note above) landed at the full 40M budget — **ACQ FAIL**, gait_valid
  1/24, leg 1 (sometimes +4) chronically sacrificed, walk/det episodes
  IDENTICAL across all 6 draws (dead-leg drag, frame-strip-confirmed).
  Crucially, `env/walk_duty_gate_factor` genuinely declined 1.0->0.62
  through the first ~2M (the signal that licensed this continuation)
  but then MONOTONICALLY RE-SATURATED to 0.85-0.94 by 40M despite the
  persisting sacrifice — exactly the disqualifying condition the
  gate named at launch — while `ep_rew_mean` climbed hugely
  (90->2100+) on the other five legs' work and `env/walk_speed` stayed
  flat ~0.13-0.14 m/s throughout. **This closes the last live gSDE
  exception: the gSDE sub-lineage (bare-sde + sdehalfgrav-remcost,
  every repair mechanism tried, fresh-init or entrenched-checkpoint)
  is now CLOSED end-to-end. Fund NO further gSDE arm of any kind.**
  Separately, `headset-halfgrav-medhead-c1` (the halfgrav sibling of
  the base-family medhead canary) landed and independently confirms
  the base sibling's PASS shape: DR-0 harness `gait_valid` TRUE 24/24,
  zero sacrificed legs, zero terminations, slip_per_m med 2.4-3.7 (near
  the 2.9 band) — a genuine CANARY PASS despite `ep_rew_mean` falling
  -24.6->-164.5 (explained by a flat per-tick reward x the same fixed
  ep_len ramp the base sibling's PASS already characterized, not a
  collapse). 40M acquisition continuation `headset-halfgrav-medhead-
  acq1` launched (VERIFIED RUNNING train-2), mirroring
  `headset-base-medhead-acq1`. Evidence: `ops.sh review
  cw-walkscratch-easy0905-{sde-s2-c2-dgatefix-cont40m,headset-halfgrav-
  medhead-c1}`, W&B `66wc8jin`/`uxuboegj`.

  UPDATE 09-05 ~18:3x: `headset-base-s0c1-dgate2-c1` (the STRONGER
  `duty_gate_floor` dose, 0.15->0.35, retrying the DIFFERENT
  non-gSDE "marginal underuse" class -- one leg chronically at duty
  0.03-0.07 on an otherwise-healthy base-family heading walker, not
  the closed gSDE LEGPARK-SKATE pathology) landed: **CANARY FAIL -
  MECHANISM (INERT-DOSE, reconfirmed at 2.3x the prior dose)**. Direct
  parent-matched comparison (`headset-base-s0c1-acq1`'s own gate
  report vs this child, identical eval conditions): walk/det
  `gait_valid` 0/6 both, leg[4] sacrificed in ALL 6 episodes both,
  duty 0.04-0.06 (child) vs 0.03-0.07 (parent) -- statistically
  indistinguishable; walk_startjitter/det is if anything WORSE on the
  child (duty 0.01-0.03, swing_count down to 7-28/20s vs the parent's
  own baseline range). Video (`walk_det_*_sheet.png`,
  `walk_startjitter_det_2_sheet.png`) shows the identical single-leg
  hitched/tucked pose every sampled frame on both. This despite
  `env/walk_duty_gate_factor` genuinely declining in training
  (1.0->0.56, NOT saturated/gamed -- real pricing pressure, unlike the
  original 0.15-floor dose which stayed pinned 0.9-1.0 the whole run)
  and `ep_rew_mean` rising every quarter (27->62->114->124) -- i.e.
  the 08-21 "rising reward" signal IS present here, same shape as the
  gSDE `dgatefix` batch that earned a 40M continuation two entries
  above. **Read together with that continuation's own outcome
  (`sde-s2-c2-dgatefix-cont40m`, immediately above in this same file):
  factor decline + rising reward at a canary checkpoint did NOT
  predict eventual repair there either -- the factor MONOTONICALLY
  RE-SATURATED by 40M with the sacrifice unchanged.** Given (a) this
  child shows literally zero measurable delta from its own parent on
  every det-mode metric (a true null result, not partial progress),
  and (b) the one precedent for granting "more budget" on this exact
  factor-declining/reward-rising shape already played out negatively
  at full budget, this closes "raise `duty_gate_floor` magnitude
  alone" as a repair lever for the marginal-underuse class too (now
  2/2 doses inert: 0.15 never applied real pressure, 0.35 applies real
  training-time pressure but zero transfers to the deterministic
  policy). Root-cause read: `policy_std` is already at its
  end-of-schedule floor (0.135 rad, matching `--log-std-final=-2.0`)
  at 2M, yet stochastic-mode leg-4 duty (0.16-0.23) still diverges
  sharply from deterministic-mode duty (0.04-0.06) -- the training-time
  factor is computed on noisy rollout actions and is satisfied by
  noise-driven duty upticks that never need to move the policy MEAN,
  because the mean's alternative use of that leg apparently costs more
  elsewhere (speed/energy) than accepting the residual penalty. A real
  fix needs to price something the mean itself must satisfy (e.g. a
  much harder floor combined with an explicit per-leg exploration
  anneal so late-training noise stops masking the mean's own duty),
  not a bigger version of the same windowed-average floor -- this is a
  NEW mechanism+bank design question, not a relaunch of this lever. No
  new arm launched off this finding this cycle (sibling
  `headset-base-irr-dgate2-c1`, the irr-timing/1g composition retry of
  the identical dose, was still genuinely computing remotely on
  train-4 at this cycle's end -- registered via `ops.sh evalpending
  add`; read it before drawing the n=2 picture, though this entry's
  own parent-matched null result is already conclusive for the
  base/heading-only cell on its own). Evidence: `logs/ckpt_eval/
  cw_walkscratch_easy0905_headset_base_{s0c1_dgate2_c1,s0c1_acq1}_gate/
  report.json`, `logs/experiments/cw-walkscratch-easy0905-headset-
  base-s0c1-dgate2-c1/wandb_history.csv`, W&B `j41igzz5`.

  UPDATE 09-05 ~19:2x — **`walk_duty_gate` is now CLOSED end-to-end
  on the base/non-gSDE family too, matching gSDE's earlier closure.**
  The one untried provenance variant, baking the strong floor
  (`duty_gate_floor=0.35`, `walk_duty_gate=1.0`) in from a LIGHTLY
  TRAINED 2M checkpoint (`headset-base-s0c1-dgfresh`, warm-started
  from `base_s0_c1.zip` before the leg-4 habit could fully entrench,
  as opposed to retrofitting onto the 40M-entrenched `s0c1-acq1`
  checkpoint) landed CANARY FAIL - MECHANISM: `env/walk_duty_gate_
  factor` genuinely declined 1.0->0.63 (real pricing) but harness
  leg-4 duty in `walk_startjitter/det` stayed statistically
  unchanged vs the undosed twin's own report (0.02-0.07 vs
  0.02-0.05), same leg sacrificed 6/6 both. Combined with the
  entrenched-checkpoint retrofit closure (2/2 FAIL at this same
  dose) and the from-scratch-full-freeze closure (3/3 FAIL, a
  different pathology), **every checkpoint-provenance case (fresh,
  early, entrenched) x every dose (0.15, 0.35) of `walk_duty_gate`
  is now FAIL on this family** — do not fund any further
  `walk_duty_gate`-class arm on ANY lineage; the marginal
  leg-favoritism pathology needs a genuinely new mechanism (explicit
  per-leg swing-count/utilization reward, bank-proven fresh, or a
  structural exploration-anneal change) before further spend.
  Evidence: `ops.sh review cw-walkscratch-easy0905-headset-base-
  s0c1-dgfresh`, `logs/ckpt_eval/cw_walkscratch_easy0905_headset_
  base_s0c1_dgfresh_gate/report.json` vs `..._headset_base_s0c1_
  gate/report.json`, W&B `8q0axo9n`.

  UPDATE 09-05 ~19:2x — the medium-heading-set (5-way) 40M
  acquisition run on the base(1g) family, `headset-base-medhead-
  acq1`, is ACQ FAIL: clears speed (fwd 1.9-2.6m/20s, ~0.09-0.13
  m/s) and falls (0/24 terminations) cleanly, reward still climbing
  every quarter (-279->398), but `gait_valid` is only 10/24 overall
  (det-mode majority sacrifices leg 1 or 4: walk/det 1/6,
  walk_startjitter/det 1/6) — well under the majority bar this
  campaign adopted. `direction_err_mean_deg` is also uniformly poor
  (22-60deg, 0/24 "success") even on the original {0,+-45} subset
  the earlier `fullhead-c1` canary tracked cleanly. This is the
  THIRD confirmation (after `s0c1-acq1`, `irr-acq1`) that the base
  (1g) family's leg-1/4 favoritism hardens into an outright gait
  failure under ANY added axis beyond flat/small-heading, while the
  halfgrav(0.5g) sibling family has cleared the irr-timing axis
  cleanly (its own medhead-acq1 read landed later this same cycle,
  see below). Working hypothesis: the pathology is gravity-linked
  (heavier per-step load at 1g makes the marginal leg's cost
  asymmetry harder to overcome), not heading-set-specific — flagged
  for the next design pass rather than another same-recipe 40M
  continuation on this lineage. Evidence: `logs/ckpt_eval/
  cw_walkscratch_easy0905_headset_base_medhead_acq1_gate/
  report.json`, W&B `8dtoak13`.

  UPDATE 09-05 ~19:2x — `headset-halfgrav-medhead-acq1` (the 0.5g
  sibling of the FAIL above, same rung/budget) landed **ACQ PASS**:
  `gait_valid` 22/24 (walk/det 6/6, walk/sto 6/6, walk_startjitter/sto
  6/6, walk_startjitter/det 4/6 — meets the majority bar exactly; the
  2 flagged episodes carry leg-4 duty 0.08-0.09, borderline-not-
  chronic, unlike the base sibling's 0.02-0.07-every-episode near-zero
  pattern), 0/24 falls, slip_per_m med 2.10-2.87 (at/under the 2.9
  band in 3/4 scenarios). This is the FIRST acquisition-scale PASS of
  the medhead rung on either gravity cell, confirming (2nd axis after
  irr-timing) that the gravity-linked-robustness-gap hypothesis holds:
  halfgrav clears every added generalization axis this campaign has
  tried, base does not. A root-cause-driven follow-up on the base
  cell (keep exploration noise alive longer alongside `walk_duty_gate`
  — `--log-std-final` -2.0->-1.2, otherwise identical to the just-
  closed `s0c1-dgfresh`) was launched same cycle:
  `headset-base-s0c1-dgnoise-c1` (2M canary, `train-1`, VERIFIED
  RUNNING). Evidence: `logs/ckpt_eval/cw_walkscratch_easy0905_
  headset_halfgrav_medhead_acq1_gate/report.json`, W&B `dejrlkhv`.

  UPDATE 09-05 ~20:4x — `headset-base-medhead2-acq1` (the base
  family's SECOND independent seed at the medhead rung, warm-started
  from a different champion than the FAIL above) is ALSO **ACQ FAIL**:
  8/24 gait_valid total (walk/det 0/6 leg 1 or 4 sacrificed every
  episode, walk/sto 6/6, walk_startjitter/det 0/6, walk_startjitter/
  sto 2/6), well under the majority bar; frame strip confirms one leg
  held rigid the whole clip. Reward is still climbing (quarters -238,
  -79,133,366) but per this same family's own established precedent
  (this is now the FOURTH base-family seed/champion — `s0c1-acq1`,
  `irr-acq1`, `medhead-acq1`, now `medhead2-acq1` — to entrench the
  identical leg-1/4 pathology at 40M budget) rising reward is not
  treated as license to continue; the base(1g)+medhead rung reads
  structurally closed pending a genuinely new per-leg-utilization
  mechanism (duty_gate/noise levers already closed separately, see
  above). Evidence: `logs/ckpt_eval/cw_walkscratch_easy0905_headset_
  base_medhead2_acq1_gate/report.json`, W&B `47j1zemx`.

  UPDATE 09-05 ~20:4x — `headset-halfgrav-medhead2-acq1` (the
  halfgrav family's 2nd medhead seed, sibling of the PASS above) reads
  **CONTINUE, not FAIL/PASS**: walk/det clears the gate's own >=4/6
  bar (4/6) but walk_startjitter/det only hits 2/6 (16/24 total).
  Unlike the base family's hard 0.0-0.02 chronic park, the flagged
  legs' duty_cycle in the failing episodes is borderline (0.06-0.11,
  matching the FIRST seed's own accepted-as-PASS 0.08-0.09 range) and
  which leg gets flagged varies episode-to-episode rather than one
  leg parked every time; `ep_rew_mean` is genuinely still climbing
  (quarters -401,-419,-183,+30, net upward in the last ~10M steps)
  with `env/v_along_cmd_m_s` stable/not collapsing — matching this
  gate's own explicit CONTINUE clause. Launched a same-recipe 40M
  continuation from this exact checkpoint,
  `headset-halfgrav-medhead2-acq1-cont40m` (`--init-from-source`,
  VERIFIED RUNNING `train-0`) to let the marginal gait resolve before
  re-judging the halfgrav medhead rung's 2nd-seed status; do not fund
  a further continuation past this one on reward-climbing alone if it
  reads marginal again. Evidence: `logs/ckpt_eval/
  cw_walkscratch_easy0905_headset_halfgrav_medhead2_acq1_gate/
  report.json`, W&B `xa9a26bm`.

  UPDATE 09-05 ~20:2x — that noise-revival follow-up,
  `headset-base-s0c1-dgnoise-c1`, landed **CANARY FAIL - MECHANISM**,
  closing the "keep exploration noise alive longer" companion lever
  too. On the pre-registered gated mode `walk_startjitter/det`, leg-4
  duty is statistically IDENTICAL across the undosed twin
  [0.04,0.05,0.05,0.02,0.05,0.02], `dgfresh` (duty_gate, low noise)
  [0.07,0.06,0.06,0.04,0.06,0.02], and `dgnoise-c1` (duty_gate + high
  noise, `policy_std` read back 0.254 confirming the dose landed)
  [0.06,0.05,0.05,0.02,0.06,0.02] — `gait_valid` 0/6 all three, same
  leg sacrificed every episode, frame strip shows the identical
  planted/dragging leg. No regression: `walk/det`/`walk/sto`/
  `walk_startjitter/sto` all stayed 6/6 valid, 0/24 falls. Root cause:
  reviving exploration noise keeps the training-time factor mobile
  (as `dgfresh` already showed) but never reaches the eval-time
  DETERMINISTIC policy mean, which is what actually walks the gate —
  noise around the mean isn't the same as moving the mean. **Both
  named cheap companion levers (bake-in-early, revive-noise) for
  `walk_duty_gate` are now closed on the base/non-gSDE family too,
  matching gSDE's identical fate — no further duty_gate-class or
  noise-schedule-class arm on this marginal-leg-favoritism question.**
  The isolating control `headset-base-s0c1-noiseonly-c1` (noise
  alone, no duty_gate) was still computing at this update; read it
  before concluding noise contributes nothing at all on its own.
  Evidence: `logs/ckpt_eval/cw_walkscratch_easy0905_headset_base_
  s0c1_dgnoise_c1_gate/report.json` vs `..._dgfresh_gate/`,
  `..._s0c1_gate/`, W&B `6b1c6hy4`.

  UPDATE 09-05 ~20:2x — `headset-base-s0c1-noiseonly-c1` (the noise-
  alone isolating control, no `walk_duty_gate`) landed **CANARY FAIL
  - MECHANISM, completing the full 2x2 {duty_gate on/off} x {noise
  low/high} grid.** Leg-4 duty on `walk_startjitter/det`
  [0.06,0.05,0.04,0.02,0.05,0.02] (med ~0.045) is statistically
  IDENTICAL to the undosed `s0c1` baseline (med ~0.045) AND to
  `dgnoise-c1` (duty_gate+noise, med ~0.05); `gait_valid` 0/6, leg
  [4] sacrificed every episode; `policy_std` reads back 0.254,
  matching `dgnoise-c1`'s own readback exactly (the dose landed
  identically in both — this is a genuine null, not underdosing). No
  regression: walk/det, walk/sto, walk_startjitter/sto all 6/6,
  0/24 falls. Full grid: s0c1 (off/low) ~0.045, dgfresh (on/low)
  ~0.06, dgnoise-c1 (on/high) ~0.05, noiseonly-c1 (off/high) ~0.045
  — **noise alone reproduces the undosed baseline exactly (zero
  effect on its own)**, and duty_gate's own small solo bump does not
  survive combination with noise. `walk_duty_gate` and plain
  exploration-noise scheduling are now BOTH fully refuted, every
  combination, on the base/non-gSDE family (matching the already-
  closed gSDE family) — no further duty_gate-class or noise-schedule-
  class arm anywhere in the headset-base family; a genuinely new
  per-leg-utilization mechanism (hard minimum-duty/minimum-swing-count
  price, not a training-time completion score gameable by noise or a
  rare token swing) needs its own design+bank pass before further
  spend on this axis. Evidence: `logs/ckpt_eval/
  cw_walkscratch_easy0905_headset_base_s0c1_noiseonly_c1_gate/
  report.json`, W&B `xyz4gzvh`.

## Known Tooling Gotchas
- A run's gate podeval can go silently ORPHANED (09-05,
  `headset-base-s0c1-acq1`): the prestage `pullckpt` step can finish
  while `eval_checkpoint` is still computing on the run's own pod; if
  a DIFFERENT concurrent cycle's drain then reuses that same pod for
  its NEXT training launch, the harness keeps computing fine (spare
  CPU, no conflict with the new GPU trainer) but the local supervisor
  that was meant to poll+copy it back is gone, so `logs/ckpt_eval/
  ..._gate/` never appears though nothing crashed. `ops.sh podeval
  <run>` correctly reports the pass `already RUNNING` and won't
  duplicate it, but that alone does not re-attach a poller — follow
  with `ops.sh pollreap <run> [interval_s] [max_min]` (backgrounded)
  to wait for the remote pass and sync it back.
- Recurrent checkpoints must use `rl_move.sim.gru_policy.RecurrentPredictor`;
  raw per-tick `model.predict(obs)` resets hidden state.
- `eval_checkpoint.py`'s `--stochastic` pass never resampled a gSDE
  checkpoint's exploration matrix between episodes (SB3's
  `model.predict()` only samples fresh gSDE noise via
  `collect_rollouts` during TRAINING, never inside `predict()` itself)
  -- so every "sto" episode of a gSDE checkpoint reused ONE frozen
  noise draw for the whole eval process. In any goal mode with no
  per-episode init randomization (plain fixed-forward `walk`, not
  `walk_startjitter`), that made every sto episode bit-identical to
  the others (confirmed 09-05: `sde-s3-c1b`'s `walk_sto_{0..5}.mp4`
  shared one MD5; `walk_startjitter_sto_*`, which DOES randomize the
  start pose, varied normally). This silently turned every gSDE "sto"
  panel across the whole `sde`/`sdehalfgrav`/`sdehalfgrav-remcost`
  09-05 easy-sim cohort into an n=1 noise-draw report dressed up as
  n=6 -- re-read any "6/6 sto fail" claim for those families as "one
  noise draw failed," not "robust failure across draws." Fixed
  09-05 (`_maybe_reset_gsde_noise` in `eval_checkpoint.py`, called at
  the top of every `run_episode`): resamples once per episode for any
  `use_sde=True` model (direct or through a wrapper's inner `.model`,
  e.g. `Rot60Policy`); bit-exact no-op for the non-gSDE default.
  4 new tests, `test_eval_checkpoint_gsde_reset_noise.py`. Any
  PRE-FIX gSDE sto read (every sde/sdehalfgrav gate before this
  commit) should be treated as informationally thin on stochastic
  robustness specifically -- their det-pass gait_valid/sacrificed-leg
  findings are unaffected (deterministic mode never uses gSDE noise).
- Some post-08-24 100 Hz evals before the `pod_eval.py` fixes may have
  wrong timeout/slew-contract evidence; re-run suspicious gates.
- Train pods have non-uniform `/dev/shm`; route obs-heavy launches to
  4.0G pods or let `_check_shm_budget` refuse them.
- Pre-09-02 checkpoints lack the `joint_frame` stamp and get rejected
  by `--init-from`/respec; fleet backfilled via
  `rl_move.sim.stamp_legacy_checkpoint` (bit-exact) — re-run on any
  `joint_frame=None` ckpt, don't relax the check.
- `--activation-fn`/`--use-sde` + a plain `--init-from` warm start is a
  hard `SystemExit` in `train_ppo_mjx.py` (PPO.load already restores
  the checkpoint's own activation/gSDE; the CLI flags only apply to
  from-scratch/transplant builds). Dies in ~2s, `wandb` reports
  `exit_code 0`/`runtime 0` — looks like a clean tiny run, not a crash,
  unless you check for zero logged steps. `respec --init-from-source`
  clones the WHOLE source arg vector including these flags — do not
  use it to continue a gSDE-family checkpoint. Fix: respec from a
  non-gSDE sibling (matching seed) with `--arg='--activation-fn='`
  (blank) + `--arg='--init-from=<ckpt>'` only (09-05, easy0905
  sde-s1-c1/sde-s2-c1 both hit this; sde-s1-c2/sde-s2-c2 fixed).
  **The "non-gSDE sibling" MUST itself never carry a bare `--use-sde`
  flag** — respec'ing from another gSDE arm (e.g. `sde-s1` to continue
  `sde-s0`) and blanking only `--activation-fn` leaves `--use-sde`
  in the cloned vector and re-triggers the SAME SystemExit (recurred
  09-05: `sde-s0-c2` respec'd from `sde-s1`, died in <1s). Always
  respec from the matching-seed `base-*` arm, never from any `sde-*`
  or `sdehalfgrav-*` arm, when building a gSDE-checkpoint continuation.
  **Scope is bigger than gSDE**: ANY non-blank `--activation-fn` (incl.
  plain `elu`) on top of a plain `--init-from` trips the SAME guard —
  `headset-halfgrav-c1` died this way 09-05 (elu, no gSDE at all).
  Always blank `--activation-fn=` on every `--init-from`/
  `--init-from-source` continuation, gSDE or not.
- **`respec` has NO flag-removal primitive** (09-05,
  `sdehalfgrav-remcost-{s0,s1}-gg`): `--arg` can only set/add a flag's
  VALUE or append a missing bare flag — it cannot strip a bare flag
  (e.g. `--use-sde`) the SOURCE run already carries. Two failure modes
  found back-to-back building a gait-gate continuation of the
  `sdehalfgrav-remcost` arms (source carries `--use-sde --activation-fn
  elu`, itself correct since remcost was a from-scratch launch, no
  `--init-from`): (1) plain `respec --from <src>` with no
  `--init-from-source` at all silently queues a FRESH-SCRATCH clone —
  no crash, no error, `wandb` looks like a completely normal run
  (caught here only via `ops.sh procs` showing no `--init-from` in the
  live cmdline); (2) adding `--init-from-source` reproduces the
  documented SystemExit gotcha above, because `--use-sde`/`elu` ride
  along uneditable. **Fix**: when the SOURCE itself is a from-scratch
  gSDE/non-default-activation launch (not itself a clean `--init-from`
  continuation), don't use `respec` for the follow-up at all — pull
  the source's own `extra_args` from the ledger, hand-strip `--use-sde`
  (+ its paired `--sde-sample-freq <n>`) and blank `--activation-fn`
  in a plain Python list, append the new `--cfg-set`s + a fresh
  `--init-from <ckpt>.zip`, then submit via
  `launch_run.py backlog add ... -- <that arg list>` (which accepts a
  fully explicit vector, bypassing clone-and-patch entirely). Always
  confirm post-launch with `ops.sh procs <pod>` that the live cmdline
  has `--init-from` and no `--use-sde`, not just the ledger fields.
- **`respec --from <src>` without `--init-from-source` silently inherits
  the SOURCE's own `--init-from` value verbatim, not the source's own
  trained OUTPUT checkpoint** (09-05, confirmed on the `walk_duty_gate`
  4-arm mechanism-health batch): cloning `sde-s1-c2`'s arg vector for
  `sde-s1-dg1` carried over c2's own `--init-from
  .../ppo_goal_cw_walkscratch_easy0905_sde_s1.zip` (c2's PARENT, the
  original pre-LEGPARK 2M canary) unchanged — nothing in a plain clone
  points at c2's own output (`sde_s1_c2.zip`). `sde-s1-dg1` therefore
  trained duty_gate from an early undifferentiated checkpoint, not a
  cure of the entrenched LEGPARK-SKATE policy its own hypothesis/parent
  field claimed to test. Confirmed on the sibling `sde-s2-dg1` too
  (init-from = `sde_s2.zip`, its grandparent). **Strictly worse** when
  the source itself carries NO `--init-from` at all (e.g. a from-scratch
  gSDE launch like `sdehalfgrav-remcost-{s0,s1}`): the clone then has NO
  `--init-from` either, so `sdehalfgrav-remcost-{s0,s1}-dg1` are running
  FULLY FRESH-FROM-SCRATCH, not continuing the LEGPARK checkpoint — an
  exact recurrence of the earlier-documented "silently queues a
  fresh-scratch clone" gotcha (see the `respec` flag-removal entry
  above), this time via the plain-clone path instead of the
  `--init-from-source` path. **Always verify a respec'd continuation's
  ACTUAL `--init-from` in the ledger `command`/`extra_args` (or live
  `ps`), never assume the note text or `parent` field describes the
  real checkpoint** — either use `--init-from-source` (rewrites
  `--init-from` to the source's own output) or, if the source's own
  vector needs editing anyway (gSDE/non-default-activation sources),
  hand-build the arg vector via `backlog add` with an explicit
  `--init-from <src's own output>.zip`. Read any already-launched
  `*-dg1` result with this in mind before trusting its "does duty_gate
  cure an entrenched checkpoint" framing — `sde-s1-dg1`'s own PASS is
  real evidence duty_gate escapes LEGPARK from an early checkpoint, but
  is NOT yet evidence it cures an already-entrenched skate policy.
- `launch_run.py respec` defaults `--steps` to the SOURCE run's own
  step count, not the intended budget. Respec'ing a 40M continuation
  `--from` a 2M-CANARY-scale sibling (e.g. `base-s0`, the original
  canary, instead of `base-s0-c1`, its 40M acquisition continuation)
  silently trains only 2M steps — no crash, no error, just the wrong
  budget (09-05: `sde-s0-c3` did this, caught by checkup after it
  finished at 2M; fixed as `sde-s0-c4` with an explicit `--steps
  40000000`). Always pass `--steps` explicitly on a respec whose
  source lineage might include a canary-scale entry; never rely on
  "default: same as source."
- Same class again (09-05, `fullhead-widen2-c2`): a "2nd seed" of a
  curriculum arm can silently warm-start from the WRONG sibling's
  checkpoint if the launching cycle names the wrong `--init-from` in
  a hand-built `backlog add` vector — the notes text said "the 2nd-seed
  medhead2 champion" but the actual `--init-from` pointed at
  `medhead2_c1.zip` (a 2M CANARY) instead of `medhead2_acq1.zip` (the
  matching 40M champion `widen2-c1` used). Always diff the ACTUAL
  `--init-from` value in the ledger `command`/`extra_args` against
  what a sibling arm used before reading a "2nd seed" result as a
  clean recipe replication — a checkpoint-maturity confound produces
  a real-looking but uninterpretable divergence (here: 16x worse slip)
  that has nothing to do with the recipe being tested.

## Walkcurr Reward Mechanisms (per-leg utilization)
- `reward.walk_swing_gate` (09-05, built + bank-proved this cycle,
  `test_walk_swing_gate_*` in `test_task_semantics.py`, 4/4 green,
  default 0 = off/bit-exact): the 6th structural repair attempt for
  the base(1g)-family chronic leg-favoritism pathology, after
  `walk_gait_gate`+`k_step_event` (CLOSED 6/6 FAIL — a rare token
  swing every several seconds keeps a recency-decay score near 1.0
  without a real gait forming) and `walk_duty_gate` (CLOSED
  9/9 FAIL across every provenance x dose — a fully planted OR
  high-frequency in-place-vibrating stance clears a trailing
  contact-DUTY floor more cheaply than any real gait, since a planted
  foot's duty is trivially 1.0) both closed end-to-end earlier the
  same day. `walk_swing_gate` keeps `walk_gait_gate`'s stride-filtered
  qualifying-swing definition (liftoff -> >=2 ticks airborne ->
  touchdown with XY stride >= `gait_gate_stride_mm`, so a chattering/
  vibrating non-displacing "swing" never counts — closes the
  duty_gate exploit by construction) but replaces the recency-decay
  score with a trailing-window COUNT (`swing_gate_min_count`,
  default 2, within `swing_gate_window_s`, default 4.0) — a leg
  stepping once every several seconds cannot clear a >=2-per-window
  count bar the way it cleared a >=1-per-(window+fade) recency floor,
  closing the gait_gate exploit by construction. MIN over support
  legs, same as every prior anti-sacrifice gate in this file. First
  canary batch launched same cycle (not yet verdicted): fresh-provenance
  `headset-base-s0c1-swinggate-fresh` + three entrenched-checkpoint
  retrofits (`swinggate-fix` on `s0c1_acq1`, `medhead-swinggate-fix`
  on `medhead_acq1`, `irr-swinggate-fix` on `irr_acq1`) — read these
  before funding further swing_gate variants.

## Real Robot Boundary
- The robot is operator-owned. No physical motion without an explicit
  current-turn operator ask.
- For web/control code only, use HTTP/dev-loop helpers:
  `make robot-check`, `robot-unit-check`, `robot-status`, `robot-deploy`.

## Startup And Status
- Orchestrator dashboard: `https://hexapod.cwd1f0-new-cluster.coreweave.app`.
- Startup packet: `STATUS.md`, this file, `RL_PLAN.md`, the relevant
  `rl_docs/tracks/<track>/STATUS.md`, `RESEARCH_RULES.md`,
  `RUN_INTERPRETATION_RULES.md`, and `rl_docs/COMMANDS.md`.
- Budgets: `STATUS.md` <=100 lines, track STATUS <=120,
  `RL_PLAN.md` <=150, this file <=80. Long audits go to `archive/`.
