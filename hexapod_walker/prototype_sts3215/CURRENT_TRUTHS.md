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
  qvel-based `safety.walk_idle_terminate_s` termination. Do not fund
  more bare-sde 40M budget without this fix (or an equivalent);
  `cw-walkscratch-easy0905-sde-idleterm-{s0,s1}` (09-05, 2M canaries)
  is the first probe. Separately: `reward.walk_gait_gate` and
  `reward.k_walk_move_current` were tried against a related
  leg-sacrifice/rigid-tripod-lock exploit on the joystick track's
  harder full-DR `joyfullcurr13` curriculum (RL_LOG 08-25) and BOTH
  were CLOSED (made the fall rate worse, at every dose/architecture
  tried) — do not relaunch either lever here without accounting for
  that prior closure.

## Known Tooling Gotchas
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
