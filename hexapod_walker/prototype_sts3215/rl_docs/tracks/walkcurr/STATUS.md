# walkcurr — prior-free walking curriculum (Kawawa-2022 lineage)

## RETIRED (2026-08-31 ~06:4x — honest DONE-negative scope finding)

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

- None. Track closed 08-31. Any reopening is an explicit new operator
  registration, not agent-initiated.
