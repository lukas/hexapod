# walkcurr — prior-free walking curriculum (Kawawa-2022 lineage)

## REOPENED (BOUNDED) 2026-09-05 — operator easy-sim teacher-free pilot

Operator focus note 09-05 authorizes ONE bounded pilot cohort on easy
simulation physics (explicit departure from hardware realism, isolated
to this cohort): `cw-walkscratch-easy0905-{base-s0,base-s1,sde-s0,
halfgrav-s0}`. Full recipe, what-is-new table, literature basis,
pre-launch proof (test_walkscratch_easy_pilot.py 13/13 on the
committed 4.81 kg mesh twin), canary/acquisition gates, and boundaries:
`rl_docs/tracks/walkcurr/EASY_PILOT_20260905.md`.

- Now: 4x 2M canary arms launched 09-05 (this cycle).
- Next (pre-registered): each HEALTHY canary continues +18M from ITS
  OWN checkpoint (respec --from <arm> --arg='--init-from=<own ckpt>',
  same cfg; 80M initial total across 4 lineages). No walking at 2M is
  NOT a canary failure — stop only for nonfinite training, ineffective
  actions, implementation failure, or a proven exploit. Do NOT expand
  into another unbounded sweep; do NOT retire the question off these
  small pilots alone.
- Acquisition milestone (own-physics, NOT the old DONE): 20 s held-out
  fixed-forward, >=0.03 m/s median net forward, 0 falls in 12 det
  episodes, six-leg lift/place on video, no belly drag; report sto.
- halfgrav is evaluated at its own gravity first; full-gravity is a
  later diagnostic, never an automatic promotion.
- Boundaries: no teacher/BC/phase/motion prior (rule (a) holds), no
  hardware claims from easy physics, defaults untouched (new keys
  goal.walk_cmd_hold_s/walk_cmd_ramp_s default-preserving).

## RETIRED for real-physics prior-free discovery (2026-08-31 ~06:4x — honest DONE-negative scope finding)

Both pre-committed final-wave seeds now read park-stand/no-gait at
150M: `cw-walkcurr-litrep-box-s0` (FAIL, 08-31 ~02:5x) and
`cw-walkcurr-litrep-box-s1` (FAIL, this cycle) — identical
fingerprint both seeds: det walk 0/6 gait_valid, progress_ratio med
0.01-0.02 (bar 0.35), 2-3 sacrificed legs, `env/walk_speed` plateaued
0.011-0.014 m/s the entire 150M budget (never clears the 0.02
static-floor litmus), `env/reward_walk` flat ~0.06-0.11 after the
first noisy step, frame strips on both showing a textbook static
stand (zero net travel, identical pose frame-to-frame). Per the
operator's own 08-30 pre-commitment ("if this wave also lands
park-stand/no-gait, RETIRE walkcurr as an honest DONE-negative scope
finding"): **this track is RETIRED.**

Plain English: 15+ independently designed non-BC mechanism/
architecture/reset-diversity/action-space classes across the whole
campaign (14 pre-08-30 classes tallied in
`OPERATOR_QUESTIONS.md` q_20260824T0233Z + this final
literature-informed action-box wave, 2 seeds, 100-150M each) all
converge on the same static-stand/quiver-to-over_current local
optimum under a from-scratch/prior-free PPO diet on this sim/reward
stack. The scope finding is that prior-free discovery alone does not
escape the initial-standing basin at this budget scale on this
hardware model — not that hexapod walking itself is unreachable: the
`joystick`/`standwalk` tracks' BC-anchored/teacher-distilled lineages
already walk (`stotight45-seed13`, `cw-walkteach-*`). No further
walkcurr rung-1/litrep-style/population-sweep arms will be launched
by the agent fleet. `STATUS.md` and `rl_move/orchestrator/tracks.json`
updated the same cycle.

Evidence: `logs/ckpt_eval/cw_walkcurr_litrep_box_s0_gate/`,
`cw_walkcurr_litrep_box_s1_gate/report.json`; RL_LOG 08-31 lines;
full campaign journal (every rung, every mechanism/architecture class,
every population-sweep arm, 08-23 -> 08-31) preserved verbatim in
`archive/walkcurr_STATUS_journal_2026-08-30_trim.md` +
`archive/walkcurr_STATUS_journal_2026-08-31_pre_retire_trim.md`.

## Goal (DONE gate — UNMET, track retired before reaching it)

A prior-free policy passes a held-out C-env contextual walking panel
(fixed forward + heading set + irregular direction changes) with zero
falls, directions actually followed, low slip/m, all-six-leg gait
validity, on video. Speed obedience is secondary throughout.

## Binding track rules (operator, 08-23 — historical record)

- **Walk-only diet**: every rung trained with `goal.walk_pure=1`.
- **Bank before launch**: WALKCURR_PF/WALKCURR_SV ranking banks in
  `test_task_semantics.py` proved before any reward-mechanism launch.
- **Rule (a)**: no gait clock, no BC teacher, no motion prior,
  including at init (BC-kickstart ruled OUT OF BOUNDS 08-29,
  q_20260824T0233Z).
- **Triage rule**: reward trend AND walk-eval trend logged together;
  reward rising while walk eval flat/down = MISALIGNED, stop same-
  recipe sweeps and audit first.

## Key facts (kept for any future reopening)

- The RAW kawawa2022 reward stack was bank-REFUTED 08-23: park (+387)
  out-earned clean walking (+325) under the walk goal alone.
- Harsh SLIPWALK doses (idle 20 / loadslip 6 / gait_gate) refuted for
  from-scratch discovery (8 statue arms).
- Every non-BC mechanism/architecture/reset-diversity lever tried
  (14 classes pre-08-30) plus the final operator-ruled literature
  action-box wave (tight joint box + plain velocity reward + clamped
  over-current, 2 seeds x 150M) converge on the same static-stand
  basin — see archived journal for the full per-arm evidence trail.

## WAITING-ON

- None. Real-physics line stays closed (08-31); the ONLY live work is
  the bounded 09-05 easy-sim pilot cohort above (operator focus note
  09-05 = the explicit operator reopening this file required).
