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

## Next
1. Triage the rung-1 pair on the ignition gate (video first).
2. On pass: hardening rung (speed band 0.04-0.08) + rung-2 anchor-fade
   design (random init, `bc_anchor_coef` annealed to zero only after
   det walking passes) — rung 2 is a NEW mechanism (anchor schedule)
   and OWES the full intermediate-state semantics bank (weight shift,
   one useful lift, one forward placement, one support transition,
   two steps then fall, static stand, clean gait) BEFORE launch.
3. On fail: retreat per the doc (slower fade / tighter residuals).

## WAITING-ON
- (none) — simulation only; never touch the physical robot.
