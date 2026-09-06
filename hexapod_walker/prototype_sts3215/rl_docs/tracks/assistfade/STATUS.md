# assistfade — pragmatic assistance-removal walking curriculum

Registered: 2026-09-06 (operator directive 2026-09-03/09-05,
`rl_docs/EASIER_WALKING_CURRICULUM.md`, merged as PR #1 / eb736371).
Scope: real mesh/100 Hz physics. "From scratch" = random network
weights, NOT prior-free. This track exists precisely so that
`walkcurr`'s honest prior-free negative result (retired 08-31) is
never rewritten or weakened — and so nobody launches another raw-joint
reward-dose or architecture sweep to relitigate it.

## Goal
Work the assistance-removal ladder (curriculum doc §"Assistance-removal
ladder"): run only the FIRST UNPROVEN rung; advance on a behavioral
pass, retreat one rung (toward more assistance) on a clear aligned
failure. Ignition gate per rung (both seeds, det held-out video/eval):
sustained forward translation full episode, repeated alternating
support transitions, all six legs participating (no permanently
planted/unloaded leg), zero falls/terminations, progress_ratio >=
0.35. Slip/current recorded, not gated at ignition. After ignition:
harden ONE dimension at a time (speed band, fixed headings, command
changes/stops, yaw, then DR/pushes).

## Ledger audit — what is already proven (2026-09-06, do not duplicate)
- **Rung 0 (proven endpoint, mesh/100 Hz): PROVEN, do not rerun.**
  - Scripted-tripod BC clone
    `ppo_goal_cw_walkteach_scripted_allhead_bc1_std25.zip`
    (bc_init_gait, 180 eps/270k pairs mesh/100 Hz harvest, holdout act
    err 0.0034) passed the pre-RL CLONE DIRECTION GATE: all 8 headings
    0 falls, prog_m>0, completion 0.374-0.393 on the teacher band
    (`logs/ckpt_eval/walkteach_scripted_allhead_bc1_panel/`, RL_LOG
    08-30 16:2x).
  - Persistent-BC-anchor RL on that clone PASSES at scale:
    `cw-walkteach-scripted-allhead-canary{,-s1}-r1` (2/2 CANARY PASS)
    -> `cw-walkteach-scripted-allhead-acq12m{,-s1}` (2/2 PASS, 5/5
    clauses, slip/m <= 2.9 teacher band, zero falls det+sto).
- **Rung 1 on PRIMITIVE/25 Hz (evidence, NOT mesh proof):**
  `cw-amp-m2-bcinit-sec5-noamp` (seed 7) + `-seed1` (08-22, pre-mesh-
  flip): BC init + task-only PPO (zero AMP/BC/imitation), fixed fwd
  0.08 m/s, DR-0, 2M — both PASS (gait_valid 6/6 det+sto, real net
  travel, no crouch collapse). Families do not transfer; this
  motivates but does not prove rung 1 on mesh.
- **Rung 1 on MESH/100 Hz: UNPROVEN as of 2026-09-06.** Ledger swept:
  every mesh-era walk run that inits from a BC clone carries an
  ongoing `train.bc_anchor_*` stack (rung 0); the anchor-free mesh
  init-from runs (joyfullcurr13/15/16 lineage) are a different scope
  (full-DR joystick curriculum, hist/tf obs) and FAILED for reasons
  already verdicted there. No exact rung-1 equivalent exists.
- easy0905 (`walkcurr` current campaign) is teacher-free on EASY
  physics — different question, different track; no overlap.

## Now
- **09-06 ~16:3x this cycle (triaged the `-lsd2` pair the ~15:4x entry
  below launched; both FAIL - IGNORES-BAND again, but this time
  root-caused with real probe evidence instead of another guess):**
  Both seeds: gait/falls/progress stay clean (gait_valid 6/6 all 4
  modes, 0 falls, prog med 0.49-0.61(s0)/0.46-0.55(s1) >= 0.35 bar),
  `log_std` genuinely moved this time (confirmed in
  `wandb_history.csv`: -2.0 at step 0 -> ~-2.98 by 7.8M, a real anneal,
  unlike the `-v2` pair's zero-movement bug) — yet achieved
  `speed_mean_m_s` STILL clusters flat (s0 0.037-0.048, s1 0.036-0.043)
  across the same 0.035-0.067 m/s commanded band. This REFUTES the
  `-lsd2` launch hypothesis (zero-exploration schedule bug) cleanly:
  exploration was real, the pathology persisted anyway.
  **Root-caused further instead of guessing again**: built
  `reward.walk_kernel_sigma_v_m_s` (new cfg, default-off, bit-exact,
  2 new bank tests, `test_task_semantics.py`) to test the doc's own
  guessed next step ("an explicit speed-tracking reward term") —
  specifically whether the Gaussian kernel's fixed `SIGMA_V=0.05 m/s`
  width (comparable to the ENTIRE hardened 0.04-0.08 band) was
  flattening the gradient. A standalone rollout probe (command-matched
  gait vs a scripted habitual-fixed-speed twin — the exact pathology
  seen on video/harness) shows the matched-vs-mismatch return gap
  stays FLAT at ~20-24% across every sigma from 0.05 down to 0.01
  (narrower does NOT widen it, slightly narrows it at the tightest
  width) — **this rules out kernel width as the mechanism.** The
  already-active `walk_kernel_prog_gate`/`k_walk_prog` terms already
  supply a real, sizeable (~20-24% return) incentive to track command
  speed; the reward is not silently flat. PPO simply has not converted
  an already-large real gradient into a stride-length change within
  8M steps, starting from a checkpoint entrenched by 10M+ prior steps
  of single-fixed-speed training. Also notes: the `amp` track's
  `walk_phase_speed_scale` clock-only-coupling lever was independently
  CLOSED for a related pathology (RL_LOG 08-23: "CLOCK-ONLY COUPLING
  IS INSUFFICIENT" — faster legs, same body speed, no command
  correlation, slip doubles) — do not relaunch that lever here
  unpaired with a stride-amplitude fix. **Refill**: launched
  `cw-assistfade-rung2-harden-speedband-{s0,s1}-explore2` (respec from
  each seed's SAME entrenched base checkpoint, `--warm-log-std-
  override=-1.3` — std~0.27 at launch, roughly double `-lsd2`'s -2.0/
  std~0.135 — the one remaining untested single-axis lever: bigger
  exploration MAGNITUDE, not a reward-shape change). Both VERIFIED
  RUNNING (train-0/train-1). **Both finished training within this same
  cycle** (fast: n-envs=3072 on an idle GPU, ~5-7 min wall time) —
  `-s1-explore2` ran the full 8M budget clean (`canary/hold_a/b=1` at
  the end); `-s0-explore2` AUTO-STOPPED early at 4.37M via its own
  canary regression guard (`protected skill(s) ['hold'] failed 3
  consecutive probes`) — the bigger std~0.27 noise may be destabilizing
  the `hold` skill even though the target axis is walk speed-tracking,
  a live FAIL-COLLAPSE candidate per this pair's own pre-registered
  gate text, worth a close read once the held-out gate lands (kicked
  `podeval` for both on their own pods this cycle, registered via
  `evalpending`, left unverdicted for the next reader — do not
  poll/sleep on it). If this ALSO reads flat on speed-covariance,
  exploration magnitude is closed too (3/3: zero-boost, -2.0, -1.3)
  and the next cycle should escalate to a structural fix (a fresh
  non-phase-locked init, or a genuinely new explicit stride-amplitude
  reward term) rather than another log-std value. Evidence: `logs/ckpt_eval/
  cw_assistfade_rung2_harden_speedband_s{0,1}_lsd2_gate/report.json`,
  `logs/experiments/cw-assistfade-rung2-harden-speedband-s{0,1}-lsd2/
  wandb_history.csv` (`log_std_anneal/all/value`), `rl_move/tests/
  test_task_semantics.py::test_harden_speedband_sigma_v_*`, snapshot
  `exp/assistfade-speedband-sigma-calibration`, W&B `0yvoegf9`/
  `1rtyf5jc`, RL_LOG 09-06 16:36-16:37.

- **09-06 ~15:4x (prior cycle; verdicted the
  `-speedband-{s0,s1}-v2` pair the ~15:0x entry below flagged as live
  FAIL candidates, root-caused, and relaunched the repair pair):**
  Both **FAIL - IGNORES-BAND**: gait stays clean (gait_valid 6/6 every
  one of 4 modes, 0 falls/terminations, all 24 episodes both seeds)
  but achieved `speed_mean_m_s` does NOT track the per-episode
  commanded speed — s0 clusters 0.037-0.039 m/s, s1 reads a LITERAL
  constant 0.038 m/s in every single `walk/det` episode, regardless of
  `cmd_dist_m`/10s spanning 0.035-0.066 m/s (~2x range) both seeds;
  `walk/sto` also misses `progress_ratio>=0.35` (s0 med 0.29, s1 med
  0.30) because achieved speed can't reach the band's upper half. s1's
  reward is genuinely declining (932.3->862.9->757.4), a real
  regression, not the 08-21 rising-reward pattern; s0's is flat/
  plateaued (1327.3->1354.1), not a continue candidate either.
  **Root cause (not the doc's own guessed "needs a speed-tracking
  reward term"):** the progress reward already normalizes by `s_ref`
  (`r_prog=k_prog*min(along/s_ref,1.25)`, so matching command IS
  priced) but both continuations inherited the gatefix source's
  already-fully-annealed `log_std` (~-3.0, std 0.05) and re-applied
  `--log-std-final -3.0 --log-std-anneal-frac 1.0` on top of that —
  **zero exploration boost for the entire 8M budget**, so the policy
  never searched for a genuinely different cadence per command; it
  just replayed its single habitual gait. This matches the documented
  `--warm-log-std-override` precedent (~200 prior uses fleet-wide)
  for exactly this "warm-started fine-tune whose std barely moves"
  shape. **Relaunched the repair pair** (respec from each `-v2` run,
  unchanged everything else): `cw-assistfade-rung2-harden-speedband-
  {s0,s1}-lsd2` — adds `--warm-log-std-override=-2.0` (std~0.135 at
  launch, annealing back to the same -3.0 target over the same 8M
  steps: real exploration early, converged/deterministic by the end).
  Both VERIFIED RUNNING (train-4/train-7). Gate: same 4-mode held-out
  panel, PASS needs achieved speed to visibly covary with per-episode
  `cmd_dist_m` (not cluster within ~0.005 m/s across a >=0.02 m/s
  commanded spread) with gait/falls unchanged; FAIL-STILL-IGNORES if
  speed stays flat despite the exploration boost -> escalate to an
  explicit speed-tracking reward term (a new mechanism) next, since
  that would rule out the schedule explanation. Evidence: `logs/
  ckpt_eval/cw_assistfade_rung2_harden_speedband_{s0,s1}_v2_gate/
  report.json`, W&B `dydwknke`/`227unt2g`, RL_LOG 09-06 15:45.

- **09-06 ~15:0x this cycle (refill-only, no completions assigned per
  the prompt, but both hardening arms finished mid-cycle anyway):**
  `cw-assistfade-rung2-harden-speedband-{s0,s1}-v2` (the speed-band
  hardening arms launched at ~14:37 below) BOTH finished training with
  no gate eval started. Notable from W&B alone (not yet a verdict —
  gate reads kicked, unread): `-s0-v2` auto-stopped early at 6.74M of
  the planned 8M (reward quarters 301.6/974.1/1327.3/1354.1 —
  flattening, consistent with either a canary auto-stop or a natural
  plateau); `-s1-v2` ran the full 8M but its reward is DECLINING
  (932.3 -> 862.9 -> 757.4 across its last 3 quarters) — the same
  shape the rung-1 `-cont8m` budget-collapse runs showed before their
  gait was found destroyed. Kicked `podeval` for both on their own
  pods (train-4/train-7), registered via `evalpending`, left
  unverdicted — next reader should treat s1's declining-reward
  trend as a live FAIL-COLLAPSE candidate per this arm's own
  pre-registered gate (see `ops.sh entry`), not assume PASS from the
  early launch note alone.

- **09-06 ~14:1x this cycle (`-s1-reseed8m-gatefix` verdicted ACQ
  PASS, completing the pair): RUNG 2 (anchor fade from random
  actor-weight init) IS NOW A 2-SEED-CONFIRMED WORKING MECHANISM.**
  Both `cw-assistfade-rung2-anchorfade-{s0,s1}-reseed8m-gatefix`
  (the goal-mix-isolation-fix reruns from the ~13:2x entry below) PASS
  their identical pre-registered gate: `bc_anchor_anneal/gate_pass`
  latches at global_step ~1.03M on BOTH seeds (2nd in-training check),
  `train/bc_coef` ramps 3.0->0.0 by ~5.06M and holds at 0 through the
  rest of the 8M budget on both, and the post-anneal held-out det+sto
  gate eval (anchor at 0) clears gait_valid 24/24, 0 falls/
  terminations, sac=[] (no permanently planted leg) on ALL 4 modes for
  BOTH seeds — progress_ratio med 0.41-0.49 (s0) / 0.31-0.46 (s1)
  against the 0.35 ignition bar. Video (contact sheets + det frame
  strips, both seeds) shows continuous six-leg alternating-support
  cycling and clear forward translation. slip_per_m runs 2.83-3.82
  (s0) / 3.02-5.07 (s1) — above the mature 2.9 joystick band on both,
  expected/accepted at ignition per this doc's own rule, watch item
  for hardening (s1 runs softer). **Next**: graduate rung 2 to
  hardening — harden ONE dimension at a time per this doc's own
  ladder (speed band -> fixed headings -> command changes/stops ->
  yaw -> DR/pushes), starting from either seed's 8M checkpoint
  (`ppo_goal_cw_assistfade_rung2_anchorfade_{s0,s1}_reseed8m_gatefix.zip`).
  SKILLS.md updated (1 row, both seeds). Evidence:
  `logs/ckpt_eval/cw_assistfade_rung2_anchorfade_{s0,s1}_
  reseed8m_gatefix_gate/report.json`, `logs/experiments/
  cw-assistfade-rung2-anchorfade-{s0,s1}-reseed8m-gatefix/
  wandb_history.csv` (`bc_anchor_anneal/*`), W&B `m1wc03cy`/
  `11imredg`, RL_LOG 09-06 14:0x/14:12.

  **Refill (same cycle): launched the ladder's first hardening arm,
  speed band, both seeds — `cw-assistfade-rung2-harden-speedband-
  {s0,s1}-v2`** (respec from each seed's own 8M gatefix checkpoint,
  `--init-from-source`, 8M budget, DR-0, BC anchor EXPLICITLY off
  `train.bc_anchor_coef=0.0`/`bc_anchor_anneal_gate=0` — it already
  fully annealed and its demonstrations were recorded at the old
  single 0.06 m/s speed, so leaving it on would re-run the anneal and
  confound the speed-band question; widened `goal.walk_speed_min_m_s`/
  `max_m_s` from the fixed 0.06 point to a uniform 0.04-0.08 m/s
  per-episode band, still inside the previously-validated pinned-speed
  panel range). **Note (self-correction, same cycle):** the first
  `respec --now` attempt for both seeds (no `-v2` suffix) silently
  carried over the source run's un-zeroed `train.bc_anchor_coef=3.0`/
  `anneal_gate=1` — caught within ~2 min via a ledger cfg audit before
  any real training time was lost, killed both trainer PIDs, ledger
  entries marked KILLED with the mistake documented, and relaunched
  clean as `-v2` with the anchor cfg keys explicitly zeroed (verified
  both re-launches' extra_args before moving on). Both `-v2` arms
  VERIFIED RUNNING (train-4 `dydwknke`, train-7 `227unt2g`) with
  growing `global_step` confirmed post-launch. Gate: standard held-out
  det+sto (4 modes) clears gait_valid majority/0 falls/progress_ratio
  >=0.35 at the widened band AND per-episode achieved speed
  (`cmd_dist_m`/10s vs `speed_mean_m_s`) tracks the per-episode
  commanded value rather than clustering near the old 0.06 pace;
  FAIL-COLLAPSE retreats to a narrower band, FAIL-IGNORES-BAND flags
  a missing speed-tracking reward term. Next reader: triage these once
  finished (`ops.sh review cw-assistfade-rung2-harden-speedband-{s0,
  s1}-v2`).

- **09-06 ~13:2x this cycle: ROOT CAUSE FOUND AND FIXED — the anneal
  gate's "one level deeper" NaN mystery (~12:2x entry below) was a
  real code bug in the ignition-gate ASSAY, not a policy or
  distribution problem.** `train_ppo_mjx._BcAnchorAnnealGateCb._build()`
  constructs a dedicated MJX assay env but never isolates its goal
  generator to pure walk — unlike the main training venv (which gets
  a post-construction `set_goal_mix(args.goal_mix)` call) and unlike
  `goal.walk_pure` (construction-time isolation) — so every assay
  episode silently drew from `config.yaml`'s default multi-mode
  mixture (`p_hold`=0.10/`p_lean`=0.15/`p_track`=0.15/`p_unload`=0.20/
  `p_raise`=0.15/`p_rise`=0.35 PLUS this task's own `p_walk`=0.70
  default — walk was only ~39% of draws, not the recipe's intended
  100%). A non-walk draw has no `.vx` trajectory, so `cmd_dist`/
  `cmd_prog_m` never accumulate and `cmd_prog_frac` reads `nan` for
  that episode — `aggregate_walk_probe`'s plain-mean (BY DESIGN,
  matches `eval_task`'s own nan rules, see
  `test_aggregate_nan_rules_match_eval_task`) then poisons the WHOLE
  round to `nan` from a single such draw, regardless of the real fall
  rate — explaining why several rounds read `early_term_rate=0.00`
  with `prog=nan` (a healthy round, structurally unmeasurable).
  Root-caused via a standalone GPU repro (`MjxShardedVecEnv`, the
  exact rung-2 cfg, a trivial zero-action policy): 5-6/8 episodes nan
  with the bug, 0/8 nan after the fix, across 3 reseeded rounds.
  **This is NOT a policy failure**: both `-reseed8m` held-out gate
  reads (verdicted this cycle, FAIL - TOOLING) already show 0 falls,
  24/24 gait_valid, six-leg cycling at-or-near the 0.35 ignition bar
  UNDER THE STILL-STUCK ANCHOR (s1: progress_ratio 0.35-0.40 on all 4
  modes, clean pass on the gate's own clause (b); s0: 0.32-0.44,
  borderline on 2/4 modes) — the anneal never got a chance to fire,
  not because the policy couldn't earn it. Fixed: `_build()` now
  forces a full pure-walk isolation (zero every `p_<mode>`, then
  `p_walk=1.0`, via the VecEnv-safe `set_goal_mix` hook — the same
  isolation `eval_checkpoint.py`'s `ALL_MODES` per-mode forcing loop
  and `goal.walk_pure` already use). 2 new regression tests
  (`test_walkcurr_mjx.py`:
  `test_default_goal_mix_is_not_pure_walk_without_walk_pure_or_isolation`,
  `test_full_pure_walk_isolation_guarantees_a_walk_trajectory_every_reset`),
  137+21 existing tests green, snapshot `exp/bc-anchor-anneal-goalmix-fix`
  (landed via a concurrent cycle's snapshot sweep into commit
  `c4b54263`, confirmed pushed). **Relaunched both seeds from the SAME
  2M parent checkpoints with the fix in place**:
  `cw-assistfade-rung2-anchorfade-{s0,s1}-reseed8m-gatefix` (8M,
  `--allow-twin` since the config is byte-identical to the reseed8m
  pair — only the trainer code differs — VERIFIED RUNNING train-4/
  train-7). Expect the gate to latch within the first few 500k-step
  checks now that the assay actually measures pure-walk episodes;
  read those before attempting any further anneal-gate variant.
  Evidence: `/tmp/repro_cmd_dist.py` (standalone GPU repro, not
  committed — recreate from this note if needed), `ops.sh review
  cw-assistfade-rung2-anchorfade-{s0,s1}-reseed8m`, W&B `jekexee3`/
  `qsqewbb5`, RL_LOG 09-06 13:2x-13:3x.

- **09-06 ~12:2x this cycle (both `-reseed8m` seeds found ALREADY FINISHED, ahead of
  schedule -- ckpt pulled + gate eval kicked for both, backgrounded; NOT yet verdicted,
  but the training-log evidence alone already answers the reseed fix's own question and
  is worth recording now): the reseed fix (`train.bc_anchor_anneal_assay_reseed=1`)
  WORKS AS DESIGNED but does NOT unblock the anneal -- ROOT CAUSE IS ONE LEVEL DEEPER
  than the ~12:0x entry diagnosed.** Confirmed via `grep '[bc-anchor-anneal]'` on both
  pods' raw training logs (s0: 11 checks to auto-stop at 5.5M; s1: 15 checks, ran the
  full 8M): `early_term_rate` (the "falls" figure) now genuinely VARIES round to round
  (0.00/0.12/0.25/0.38, both seeds) instead of being pinned at 0.125 forever -- the
  reseed IS drawing independent configs, exactly as designed. **But `cmd_prog_frac`
  (the progress clause) reads NaN on EVERY SINGLE round of BOTH seeds, 26/26 combined
  checks, INCLUDING every round where `early_term_rate=0.00` (s0 @3.0M; s1 @3.0M/5.5M/
  7.0M/7.5M) -- i.e. progress is NaN even when literally zero probe episodes fell.**
  This rules out the ~12:0x diagnosis's implicit assumption (that NaN was purely a
  downstream symptom of `failed_probe_row()` on a fallen episode) -- read the actual
  code path: `walk_task.py`'s `cmd_prog_frac` is `nan` whenever `w["cmd_dist"] <= 0.01`
  (episode's own commanded-distance accumulator), a DIFFERENT and independent condition
  from the `early_term`/fall flag; `aggregate_walk_probe` (`walkcurr_cert.py`) then
  plain-means `cmd_prog_frac` across all 8 rows (not in `_NAN_OK`, unlike
  `cross_track_frac`/`wrong_way`/`stop_speed_*` which ARE nanmean'd) -- so a SINGLE
  episode with near-zero commanded distance poisons the whole round's aggregate to NaN
  even though the other 7 episodes walked fine. Rung 2's launch cfg is fixed-forward
  0.06 m/s with no stops/no park-starts, so it is not yet understood WHY any episode
  would end with `cmd_dist<=0.01` absent a fall -- next reader should instrument/log a
  single assay round's raw per-episode `cmd_dist` values (not just the aggregate) to
  find which episode index is empty and why (candidates: the assay's `goal.walk_probe=1.0`
  override interacting with `episode-seconds=10` in a way that truncates the command
  window before any distance accrues, or a race between `env.seed()` and `flush_reset_
  pools()` leaving one sub-env's goal trajectory unset for its first episode). **One
  candidate already RULED OUT this cycle**: a bounded CPU repro
  (`SimHexapodJointWalkEnv`, identical cfg incl. `walk_yaw_cmd=1`/`walk_phase_run_on_yaw=1`/
  `walk_yaw_zero_frac=1.0`, 16 seeds, random small-action policy, full 1000-tick/10s
  episodes) NEVER produced a NaN `cmd_prog_frac` — every trunc episode (full horizon)
  and every early term (random-policy falls, all at tick 261) read a finite value,
  including on falls. So the goal-trajectory construction itself is not the defect in
  isolation; the NaN is specific to either (a) the ACTUAL trained/bc-anchored
  deterministic policy's action pattern (possible occasional NaN/degenerate action under
  strong `bc_anchor_coef=3` + tiny `std=0.05`), or (b) something MJX/`MjxShardedVecEnv`-
  pool-specific that the CPU single-env repro cannot reach (`env.flush_reset_pools()`/
  sharded pool reuse has no CPU-env equivalent tested here). Next step needs either the
  real checkpoint run through the CPU env (feasible, no GPU needed — load the `.zip`
  policy and call `.predict(deterministic=True)` instead of random actions) or an
  instrumented GPU-side print of the MJX assay's raw per-env `cmd_dist`/`term` array
  before aggregation. Reproduction script left at (not committed, recreate if useful):
  a `SimHexapodJointWalkEnv` loop over seeds with the rung-2 cfg dict, printing
  `info["walk_probe"]["cmd_prog_frac"]` and `env._goal_traj.vx` per episode. **Second
  repro attempt (same cycle): loaded the ACTUAL `-s0-reseed8m` checkpoint
  (`PPO.load(..., device="cpu")`) and ran it deterministically in the same CPU env
  across 16 seeds — ALL 16 gave the IDENTICAL result (`cmd_prog_frac=0.2458`, 0 falls,
  full 1000-tick episodes), because with `dr_scale=0`/`randomize=False`/fixed speed+zero
  yaw the CPU episode has no seed-sensitive randomness left to vary at all.** No NaN, no
  variation. This rules out the checkpoint's weights/deterministic-action-pattern being
  inherently degenerate (a healthy, reproducible walk comes out every time in the CPU
  physics) and narrows the remaining candidate space to the MJX/warp GPU path itself —
  most likely `MjxShardedVecEnv`'s pool/shard reset mechanics (the CPU single-env test
  has no equivalent to reproduce), or a genuine MJX-vs-CPU-MuJoCo physics divergence
  under this exact policy that only manifests on the GPU backend. Next reproduction step
  needs either an MJX-backed (not CPU mujoco) single-shard construction with the same
  checkpoint, or GPU-side instrumentation of the live assay's raw per-env row dump. **Do not
  relaunch another anneal-gate arm on unmodified code — this is now proven code-level
  (26/26 checks across 2 independent seeds), not a training/seed variance question**;
  the ignition gate CANNOT latch until either (a) `cmd_prog_frac` moves to `_NAN_OK`
  (nanmean, matching the sibling command-conditional keys) if a legitimately
  unmeasurable-but-not-failed episode is expected, or (b) the root NaN source itself is
  fixed once found. Both `-reseed8m` runs otherwise behaved exactly like healthy rung-2
  training throughout (reward/canary telemetry unremarkable; `canary/hold_a/b=1`
  throughout both) -- this is purely an anneal-gate bookkeeping defect, not a policy
  regression. DIG-IN flagged for whichever cycle reads the held-out gate evals (kicked
  this cycle, backgrounded, ~1.5-2h): `-s0-reseed8m` AUTO-STOPPED again at 5.5M (walk_fwd
  3-consecutive-fail, same canary mechanism as `-cont8m`, but earlier — 5.5M vs the
  parent's ~7.9M); `-s1-reseed8m` ran the full 8M with no auto-stop. Evidence:
  `kubectl exec hexapod-mjx-train-{4,7} -- grep '\[bc-anchor-anneal\]'
  /tmp/train_cw-assistfade-rung2-anchorfade-{s0,s1}-reseed8m.log`, `rl_move/sim/
  walk_task.py` cmd_prog_frac definition, `rl_move/sim/walkcurr_cert.py`
  `aggregate_walk_probe`/`_NAN_OK`, W&B `jekexee3`/`qsqewbb5`.

- **09-06 ~12:0x (DIG-IN cycle, `-s0-cont8m` VERDICTED: ACQ FAIL - INFORMATIVE, assay
  deadlock root-caused; fix built + both seeds relaunched):** the held-out mesh gate eval
  landed and does NOT show collapse — gait_valid 24/24, 0 falls/terms, no sacrificed leg,
  six legs cycling on video — so the pre-registered FAIL-MECHANISM text is NOT met. But
  det prog med fell to 0.30 (parent 2M: 0.36–0.52; bar 0.35) while sto stayed 0.39–0.40
  with better slip (2.98 vs det 4.48): the deterministic MEAN is what regressed, matching
  the canary. ROOT CAUSE of the never-latching anneal (both seeds): the in-training assay
  is PINNED — `env.seed(828282)` before EVERY round, desync off, deterministic policy —
  so all rounds replay the SAME 8 configs; the persistent `early_term_rate=0.125`
  (s0: 10/11 rounds; s1: 15/15) is ONE hard init the anchored policy deterministically
  fails, not small-n noise (the 11:2x entry's "assay noise" read was wrong — parent 2M
  failed 2/8, later ckpts 1/8: policy-dependent falls). Double lock: that episode injects
  `failed_probe_row()` → `cmd_prog_frac=NaN` (plain-mean, not `_NAN_OK`) → the progress
  clause ALSO NaN-fails every round (`gate_cmd_prog_frac` absent from history, both
  seeds). Chicken-and-egg: the latch demands zero falls on a frozen probe set whose hard
  init the strong anchor (coef stuck 3.0) prevents the policy from fixing; continued
  anchored training then degrades pinned det behavior (canary walk_fwd 0/2 from ~3M new
  steps in s0, ~5M in s1). Per 08-21: misalignment to repair. FIX (snapshot
  `exp/cw-assistfade-rung2-anchorfade-reseed-fix`): `train.bc_anchor_anneal_assay_reseed`
  (default OFF, bit-exact; fresh pinned seed per assay round → independent draws; 9 tests
  green). RELAUNCHED both seeds from the PARENT 2M checkpoints (not the degraded cont8m
  ends): `cw-assistfade-rung2-anchorfade-{s0,s1}-reseed8m`, reseed=1, 8M, pre-registered
  gates incl. a FAIL-ASSAY-DISTRIBUTION clause if reseeded rounds still never latch.
  `-s1-cont8m` left unverdicted for its own triage cycle (evidence identical; cite this
  entry). Note for the "cont8m past its 2M canary is structurally unstable" question: at
  rung 2 the instability now has a concrete mechanism (stuck anchor + std anneal squeezing
  the det mean), distinct from rung-1's gait destruction.
- **09-06 ~11:5x this cycle (triage of `-s0-cont8m`, DIG-IN flagged, no verdict yet — held-out
  gate eval still computing on-pod, video-every=1/24-episode panels run 1.5-2h): both rung-2
  `-cont8m` continuations (`-s0-cont8m` train-8, `-s1-cont8m` train-9, the other a concurrent
  cycle's to verdict) independently AUTO-STOPPED via the fixed-seed canary regression guard —
  NOT a triage kill, the run's own `_make_canary_stop_callback` fired mid-training.** Plain
  English: `walk_fwd` was one of only two "protected" groups (the ones the 2M parent checkpoint
  passed 2/2 at launch — the other is `hold`); by the time each run reached ~5.7M
  (`-s0-cont8m`) / ~7.9M (`-s1-cont8m`) of the planned 8M new steps, `walk_fwd_a`/`walk_fwd_b`
  had failed 3 consecutive periodic probes (every ~1M steps) while `hold` stayed 2/2 throughout
  — training auto-stopped itself per its own regression guard
  (`canary/auto_stop=1`, log line `[canary] AUTO-STOP at 5,667,840: protected skill(s)
  ['walk_fwd'] failed 3 consecutive probes`, W&B `71d7y3v2`/matching for s1). The walk_fwd
  canary case is essentially the SAME distribution as this recipe's own training task (pinned
  hold-then-ramp-then-constant 0.06 m/s forward, mesh/100 Hz) — so a deterministic pinned probe
  regressing on the training task itself, while `ep_rew_mean` kept climbing every quarter
  (`-s0-cont8m` reward quarters 215.7/681.4/1188.6/1251.2, still rising at the point of
  auto-stop) is a real reward<->eval divergence signal, not noise: per-check history shows
  `walk_fwd_{a,b}` pass at the 2M checkpoint, a single early blip fail at 1M-new-steps, ANOTHER
  pass at 2M-new-steps, then a clean 0/0 fail from 3M-new-steps onward through auto-stop — looks
  like settling into a genuine regressed basin after ~3M steps, not one noisy sample. This is
  the THIRD cont8m-budget failure fingerprint in this campaign (rung-1's `-s1-cont8m` gait-
  destroyed-by-budget and `-s2-cont8m` wrong-direction-spin-by-budget were the first two) —
  worth asking, once both held-out reads land, whether "continue the SAME fixed-forward-only
  cont8m recipe past its 2M canary" is itself a structurally unstable move on this track,
  independent of which rung. DIG-IN reason for `-s0-cont8m`: the pre-registered ledger gate's
  own FAIL text ("the held-out gait collapses... at this budget") may already be met, but the
  held-out mesh gate eval (det+sto, per-leg gait metrics, video) was still computing at end of
  this cycle — verdict on that read, not the canary telemetry alone, per the video/gate-outranks-
  reward rule. If the gate eval instead shows a CLEAN six-leg gait despite the canary fail, that
  is a genuine gate-vs-canary disagreement needing its own root-cause (canary's pinned/short
  hold+ramp probe may not match the harness's 10s constant-command episodes). Evidence so far:
  `logs/experiments/cw-assistfade-rung2-anchorfade-{s0,s1}-cont8m/wandb_summary.json`
  (`canary_baseline`/`canary_protected`/`canary/*` keys), `wandb_history.csv` (per-check
  `canary/walk_fwd_{a,b}` timeline), on-pod
  `/tmp/train_cw-assistfade-rung2-anchorfade-s0-cont8m.log` (`grep '\[canary\]'`).
- **09-06 ~11:2x this cycle (refill-only, no completions assigned; found+verdicted the rung-2
  anchorfade canary pair a concurrent cycle had launched and left unread):** **both seeds CANARY
  PASS, and BEAT the ignition bar already at 2M under the still-strong anchor** — held-out gate
  eval 24/24 episodes gait_valid=true, 0 terminations, 0 sacrificed legs, six-leg cycling
  (duty 0.35-0.62, swing_count uniform 12/12), progress_ratio 0.35-0.52 across all 4 modes (bar
  0.35), slip/m 2.4-3.3 (near/at the 2.9 teacher band) — clearly better than rung-1's own BC-init
  canary comparison point (progress med 0.22) despite starting from RANDOM weights. The in-training
  anneal-gate assay (n=8 eps every 500k steps) never latched `ignition_gate_pass` in this 2M window
  (`bc_anchor_anneal/gate_pass`=0 every check, `gate_early_term_rate`=0.25 vs 0/24 in the larger
  held-out eval — small-n assay noise, not a real fall pattern) so `bc_anchor_coef` never annealed
  off 3.0 — exactly the CANARY gate's own "not yet annealed is fine at this budget" criterion.
  SKILLS.md updated (1 new entry, both seeds). **Refill:** launched `-cont8m` for both seeds
  (+8M each, 10M cumulative, `--init-from-source`, ACQ phase) — gives the periodic assay ~16 more
  checks to latch the gate and drive the anchor through its 4M-step anneal, then the real read is
  deterministic held-out behavior WITH the anchor at/near zero (the doc's actual downstream gate,
  not the still-strong-anchor mechanism-health check this cycle closed). VERIFIED RUNNING
  `-s0-cont8m` train-8, `-s1-cont8m` train-9. Housekeeping: an early respec attempt for `-s1-cont8m`
  timed out client-side and was mistakenly retried, producing a duplicate `-s1-cont8m-rr1` on
  train-2 running the identical recipe — caught via a live `kubectl exec ps` cross-check, killed
  immediately (`ops.sh killrun`), ledger marked KILLED with the duplicate explained; no information
  lost, `-s1-cont8m` (train-9) is the surviving run. Evidence: `logs/ckpt_eval/
  cw_assistfade_rung2_anchorfade_{s0,s1}_gate/report.json`, W&B `fd7gmi2z`/`70k66xu7`,
  `logs/experiments/cw-assistfade-rung2-anchorfade-{s0,s1}/wandb_history.csv`, `launch_run.py
  status`, RL_LOG 09-06 11:2x.
- **09-06 ~03:3x rung-1 first read (s1) + refill (keep-GPUs-training
  cycle, fb_20260906T031718_f01aa6):** `-s1` VERDICTED **CANARY PASS
  (mechanism health)** — task-only PPO from BC init did NOT destroy
  the gait at 2M: gait_valid 24/24 (all 4 modes), 0 falls/terms,
  sac=[] everywhere, six-leg cycling + level body on video
  (`logs/ckpt_eval/cw_assistfade_rung1_bcinit_taskonly_s1_gate/`).
  Shortfall is pure speed: det prog med 0.22 vs the 0.35 ignition bar
  (0.12 m/10 s at 0.06 m/s cmd); slip 8-12/m recorded. Per 08-21 +
  the gate's own "don't judge acquisition at 2M" scope this is
  continue-not-retreat. LAUNCHED: `-s1-cont8m` (+8M from own ckpt,
  acquisition phase, ignition bar judged at 10M total) and `-s2`
  (fresh-seed 2M canary — s0's training reward collapsed in Q4
  (96->23) while s1's stayed healthy; s2 disambiguates seed-vs-recipe
  before more acquisition spend). `-s0`'s gate eval was still running
  on train-4 (watcher prestage; a concurrent triage cycle owns its
  pollreap) — the JOINT rung-1 ignition read stays OPEN pending s0.
  No rung-2 launch until the joint read lands (doc: run only the
  first unproven rung); rung-2 anchor-fade still owes the full
  intermediate-state semantics bank before any launch.
- **09-06 ~03:4x JOINT RUNG-1 READ (s0 lands): NOT A PASS.** `-s0`
  VERDICTED **CANARY FAIL - MECHANISM — gait destroyed on this seed**:
  aggregate `gait_valid` 0/24 across all 4 modes, a chronic 2-leg
  (legs 0,1, the front-right/right-middle adjacent pair) sacrifice in
  nearly every episode (occasionally 3-4 legs), 2 safety terminations
  (over_current) under `walk_startjitter`, progress_ratio 0.08-0.20
  (worse than even s1's failing 0.13-0.25 band). Video confirms a
  near-stationary/quivering body, not s1's slower-but-real six-leg
  gait. Training reward Q4 collapsed 95.6->22.9 exactly where the
  gait failure concentrates (vs s1's healthier 167.8->108.6) — the
  reward-collapse flag that motivated launching `-s2` before this
  read landed was justified. **Joint rung-1 ignition gate is NOT MET**
  (requires both seeds; s1 alone read CANARY PASS mechanism-health,
  s0 reads FAIL gait-destroyed) — per the doc's own rule this is a
  RETREAT trigger, not a same-recipe retry. However: since `-s2`
  (fresh-seed 2M canary, seed-vs-recipe discriminator) and `-s1-cont8m`
  (+8M continuation of the healthy seed) were ALREADY launched before
  this read landed specifically to test whether s0's failure is a
  per-seed basin or a recipe-level defect, retreat is deferred one
  more data point: if `-s2` also shows gait destruction, rung 1 is
  recipe-unstable (>=2/3 seeds destroy the gait) and the doc's retreat
  (rung 2 slower anchor fade, or rung 3 tighter residuals) fires next
  cycle; if `-s2` reads healthy like s1, rung 1 is seed-sensitive but
  viable and a 3rd/4th seed or `-s1-cont8m`'s ignition-bar read at 10M
  decides advancement. Evidence: `logs/ckpt_eval/
  cw_assistfade_rung1_bcinit_taskonly_s0_gate/report.json`, W&B
  `vf3f9kbw`; RL_LOG 09-06 03:40.
- **Rung 1 canary pair LAUNCHED 2026-09-06:**
  `cw-assistfade-rung1-bcinit-taskonly-s0` / `-s1` (2M each, canary
  phase). Recipe = `cw-walkteach-scripted-allhead-canary-r1` byte-
  identical EXCEPT: all `train.bc_anchor_*` = 0 and
  `reward.walk_anchor_gate=0` (no ongoing BC/imitation of any kind);
  fixed forward only (`walk_heading_max_rad=0`, `walk_stop_frac=0`,
  `walk_park_start_frac=0`, resample no-op at 30 s > 10 s episodes);
  fixed 0.06 m/s (inside the clone's 0.06-0.10 training envelope, per
  the doc's 0.04-0.06 rung-1 band); 10 s episodes; same init
  (`..._bc1_std25.zip`), same log-std anneal to -3.0 (proven low
  walking-noise range), same bank-proven course-income reward stack
  (no new reward keys => no new mechanism bank owed; ordering check
  for the EXACT rung-1 cfg added to `rl_move/tests/
  test_task_semantics.py` ASSISTFADE_RUNG1 bank this cycle).
- Gate (pre-registered, ignition): see Goal. PASS on both seeds =>
  advance to first hardening dim (speed band) and queue rung 2
  (anchor fade from random weights). FAIL with gait destroyed =>
  rung 2 with SLOWER anchor fade, or rung 3 (tighter residual bounds)
  — explicitly NOT a reward-dose/architecture retry.

## Rung-1 seed panel state (09-06 ~04:4x)
- `s0` CANARY FAIL - MECHANISM (gait destroyed, 0/24 gv) — verdicted 03:40.
- `s1` CANARY PASS mechanism at 2M (24/24 gv, 0 falls, det prog 0.22 <
  0.35 bar) but its `-s1-cont8m` (+8M, 10M total) ignition read is
  **FAIL — gait destroyed by budget**: aggregate gait_valid 0/24 (all
  4 modes), EVERY episode now terminates over_current (24/24, vs 0/24
  at 2M), chronic 2-leg sacrifice (leg 4 airborne duty 0.02-0.08, leg
  5 permanently planted duty 0.98-1.0, every episode), video confirms
  near-static body + one leg dragging rigidly. Reward net-DECLINED
  (quarters 30.9/-234.1/-124.5/2.0, trough -300 around 3-4M) with
  terminations/over_current rising in lockstep (22-60 early ->
  85-147 late) — not the 08-21 rising-reward continuation case.
  Verdicted 04:38, W&B `nvpkarrc`.
- `s2` CANARY PASS mechanism at 2M (23/24 gv, 0 falls, six legs
  cycling on det strip, det prog med 0.23 < 0.35 bar; one
  startjitter/sto over_current term reported-not-gated per the 09-04
  uncalibrated-current ruling) → `s2-cont8m` RUNNING (train-8), the
  deciding data point.
- **Updated joint read: 2/3 seeds now show gait destruction (s0
  immediately at 2M, s1 after +8M budget) — trending toward a
  RECIPE-level ceiling/entrenchment, not seed noise, matching the
  same budget-driven leg-sacrifice attractor CURRENT_TRUTHS already
  logs across unrelated crossgrav/sde lineages this week.** Per the
  doc's own rule, do not launch a 4th same-recipe seed while
  `s2-cont8m` is still deciding; if `s2-cont8m` also destroys its
  gait, rung 1 is CLOSED (recipe-unstable, >=2/3 destroy) and the
  next cycle fires the doc's retreat (rung 2 slower anchor fade, or
  rung 3 tighter residuals) without further same-recipe spend.

## RUNG 1 CLOSED (09-06 ~05:0x) — 3/3 seeds fail at scale, retreat fires
`s2-cont8m` landed: gait_valid 6/6 all 4 modes (no leg sacrifice) but
progress_ratio NEGATIVE in all 24 episodes (-0.10 to -0.16),
direction_err_mean_deg 99-119° (spin/wrong-way, not a tracking miss),
slip_per_m 20-24 (7-8x the 2.9 band), video confirms a body that spins
in place while the heading arrow rotates through multiple directions.
Reward quarters 98.7/44.1/-4.8/-275.2 — clean decline, not the 08-21
rising-reward case. **Final rung-1 tally: 3/3 seeds fail at 8-10M
scale, each via a DIFFERENT fingerprint** (s0: immediate gait
destruction at 2M; s1-cont8m: chronic 2-leg sacrifice + 100%
over_current at 10M; s2-cont8m: clean six-leg gait but wrong-direction
spin + massive slip at 10M). This clears the doc's own >=2/3-destroy
retreat threshold decisively. **Rung 1 (BC init + task-only PPO, no
ongoing BC/AMP/imitation) is CLOSED on mesh/100Hz: do not fund a 4th
same-recipe seed or any same-recipe budget continuation.**

## Next
0. **SEMANTICS BANK GREEN 2026-09-06 ~10:2x (no training spend, code +
   tests only — this closes the last precondition item 1 below still
   listed as owed).** `test_task_semantics.py`'s
   `test_assistfade_rung2_*` (5 tests, `assistfade_rung2_returns`
   fixture) now pin the doc's seven named landmarks (`weight_shift`,
   `one_lift`, `one_placement`, `one_transition`, `two_steps_fall`,
   `static_stand`, `clean_gait`) under the UNCHANGED rung-1 reward
   stack (`ASSISTFADE_RUNG1_OVERRIDES` — rung 2 only changes the
   TRAINING side, `bc_anchor.py`'s own docstring: "the reward stack is
   UNTOUCHED"). All 5 green: no permanent-refusal landmark
   (`static_stand`) rivals any attempt; no fall-after-progress
   landmark (`two_steps_fall`) rivals a safe partial attempt or beats
   holding still; `clean_gait` remains the clear global optimum above
   every partial landmark. Two calibration findings worth reusing if
   this bank is ever revisited: (a) a naive first construction froze
   each partial landmark's pose and held it for the REMAINING ~13s of
   a 15s episode — that measures "stuck", not "progress", and scored
   WORSE than `static_stand` for every partial landmark (independently
   re-discovered twice this cycle, once by this session, once by a
   concurrent session that landed the fix — see file history); (b) the
   four partial landmarks cluster in a narrow band and do NOT form a
   strict internal staircase (`one_lift` can beat `one_placement`) —
   asserted as a band, not a fine ordering, per the bank's own
   evidence-over-assumption convention. **Rung-2 canary launch is now
   precondition-clear** (mechanism below + bank both green) but NOT
   YET LAUNCHED by any session as of this note — the next reader can
   launch it directly: 2 seeds, mesh/100Hz, `goal.walk_speed_*=0.06`
   fixed-forward (rung-1's exact command diet), RANDOM actor-weight
   init (no `--init-from-source`, unlike rung 1's BC-clone init — this
   is rung 2's whole point), `train.bc_anchor_coef` set to a genuinely
   STRONG initial value (rung 1's BC-clone init never needed a
   nonzero anchor; rung 2 has no precedent run to copy a dose from —
   pick something clearly dominant early, e.g. on the order of the
   rise-task anchor doses in `bc_anchor.py`, and say so in the launch
   notes since it is a fresh assume-and-go), `train.bc_anchor_anneal_
   gate=1` (+ `_steps/_check_every/_assay_episodes/_min_progress`, all
   built 09-06 ~09:3x), 2M-step canary budget (this is a genuinely new
   mechanism combination — canary first, never straight to ACQ).
1. **MECHANISM BUILT 2026-09-06 ~09:3x (no training spend, code +
   tests only).** Rung 2's "anneal the anchor smoothly to zero only
   after deterministic walking passes" needed a genuinely new
   mechanism (a gate-triggered anneal, not a fixed coefficient or a
   plain step-count schedule — a step-count-only anneal would repeat
   rung 1's exact failure of dropping the anchor before the RL side
   has anything to fall back on). Built, default-OFF, bit-exact when
   off:
   - `walkcurr_cert.IGNITION_GATE` / `ignition_gate_pass()`: a pure
     function pinning the curriculum doc's own named ignition
     criteria (no falls, six-leg participation via
     `contact_sw_per_s`/`foot_sw_min_per_s`, `cmd_prog_frac>=0.35`) —
     deliberately LOOSER than `WALKCURR_GATE`/`walkcurr_bucket_pass`
     (slip/roll/cross-track/direction are recorded, not gated, at
     ignition per the doc). 4 new unit tests
     (`test_walk_curriculum.py`), including one that explicitly checks
     ignition passes a sloppy-but-walking row `WALKCURR_GATE` would
     reject.
   - `bc_anchor.bc_anchor_anneal_value()`: a pure scheduler — holds
     the coefficient at its initial ("strong") value until a
     `pass_step` is latched (None = never yet, matching "initially"),
     then linearly ramps to 0 over `train.bc_anchor_anneal_steps`,
     then holds at 0. 4 new unit tests (holds pre-pass at any step
     magnitude, linear ramp arithmetic, holds at 0 post-ramp,
     monotonic non-increasing).
   - `attach_bc_anchor()` now reads
     `train.bc_anchor_anneal_gate/_steps/_check_every/
     _assay_episodes/_min_progress` (all inert unless
     `bc_anchor_anneal_gate>0`, which itself requires
     `bc_anchor_coef>0` — fails closed if there is nothing to anneal).
     3 new unit tests (default-off wiring, positive-coef requirement,
     cfg knobs round-trip).
   - `train_ppo_mjx.py`: a new `_BcAnchorAnnealGateCb`
     (gated on `model.bc_anneal_gate`, independent of
     `--walk-curriculum` — rung 2's launch cfg is a single fixed
     forward command, not a bucket ladder) that periodically builds a
     dedicated deterministic MJX assay env (same construction pattern
     as the walk-curriculum cert loop's own `_MjxWalkCurrCert._build`/
     `_assay`, `goal.walk_probe=1.0`, no bucket forcing), runs
     `train.bc_anchor_anneal_assay_episodes` det episodes, aggregates
     via the existing `aggregate_walk_probe`, and on the FIRST round
     that clears `ignition_gate_pass` latches that step and starts
     overwriting live `model.bc_coef` via `bc_anchor_anneal_value`
     every rollout start. Latching is permanent (a later regressed
     assay never re-arms the anchor). Import-checked
     (`python -c "import rl_move.sim.train_ppo_mjx"`), no dry-run
     harness exists to exercise the callback itself without spending
     GPU steps — that first real exercise is the eventual rung-2
     canary launch below, not this cycle.
   - Tests: `uv run pytest rl_move/tests/test_bc_anchor.py
     rl_move/tests/test_walk_curriculum.py rl_move/tests/
     test_walkcurr_mjx.py` — 191+19 = 210 passed, 0 failed (14 new
     tests added by this change).
   - Snapshot: see RL_LOG for the commit/tag.
   **Still owed before ANY rung-2 launch** (per the doc's own process
   requirement, unchanged by the mechanism build above): the full
   intermediate-state semantics bank (weight shift, one useful lift,
   one forward placement, one support transition, two steps then
   fall, static stand, clean gait) — an ordering check (à la
   `ASSISTFADE_RUNG1_OVERRIDES`/`assistfade_rung1_returns`) that the
   rung-2 reward stack scores those seven synthetic
   trajectories/action-sequences in the intended order under
   `attach_bc_anchor`'s strong-then-annealing regime. This is the
   next concrete piece of work (design the 7 synthetic states, reuse
   the rise/hold bank's synthetic-pose-generation helpers where
   possible since weight-shift/lift/placement look like posture-probe
   variants; support-transition/two-steps-then-fall/clean-gait need a
   rollout-based score like `ASSISTFADE_RUNG1`'s `_walk_rollout`) —
   NOT a design question needing an operator answer, a build task for
   whichever cycle picks this up next.
2. Alternative if rung 2's design proves harder to bank than expected:
   rung 3 (bounded residuals around the scripted tripod with a fading
   reference) is the doc's other named retreat target and may have a
   simpler semantics story (residual bounds shrink on a schedule
   rather than an anchor coefficient annealing) — worth a quick
   comparative design pass before committing to one.
3. Do NOT re-attempt rung 1 with a reward-dose or architecture tweak
   (doc-binding) — the failure modes (leg-sacrifice, wrong-direction
   spin) are both budget-driven entrenchment away from a healthy 2M
   canary, not an undertrained or misconfigured start.

## WAITING-ON
- (none) — simulation only; never touch the physical robot.
