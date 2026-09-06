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
