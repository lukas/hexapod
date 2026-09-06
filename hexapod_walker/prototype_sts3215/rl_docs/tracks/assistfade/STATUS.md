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
1. Design rung 2 (anchor fade FROM RANDOM WEIGHTS, `bc_anchor_coef`
   annealed to zero only after det walking passes — NOT rung 1's
   persistent-anchor-then-drop-to-zero shape, which is what just
   failed 3/3). This is a NEW mechanism (an annealing schedule, not a
   fixed coefficient) and OWES the full intermediate-state semantics
   bank (weight shift, one useful lift, one forward placement, one
   support transition, two steps then fall, static stand, clean gait)
   BEFORE any launch — build/prove it as its own cycle's work, not a
   reason to sit idle.
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
