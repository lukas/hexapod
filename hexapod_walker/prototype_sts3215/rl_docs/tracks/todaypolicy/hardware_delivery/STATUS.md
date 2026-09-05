# todaypolicy / hardware_delivery — measured controller delivery

Last updated: 2026-09-05 ~08:0x UTC. Reopened per operator MCP note
`fb_20260905T071610_749846` (Codex, implementing Lukas's request):
smooth hardware walking via measured-controller work. Division of
labor per that note:

- **Local Codex owns** (do not duplicate/edit until handoff):
  `linux_control/rl_policy.py`, `robot_state.py`,
  `run_rl_walk_trial.py` timing/freshness; C-MuJoCo deployed-transport
  replay + matched frozen-policy evaluator; Robot Lab
  external_guarded benchmark plans. Physical robot motion is
  operator/Codex-owned, NOT this repo's agents.
- **Orchestrator owns (this doc):** the opt-in command-envelope /
  measured-feedback controller candidate, NEW files only, CPU-only,
  zero PPO, scored against ORIGINAL requests.

## Goal

A deployable command-governing layer between joystick requests and
the scripted gait that (a) keeps applied commands continuous and
rate-limited, (b) governs simultaneous translation+yaw demand from
MEASURED joint slew feasibility (the executed loop's own
`safety.max_delta_q_deg` clip-saturation statistic, one-tick-delayed
feedback), and (c) can never fake success by throttling — requested
and applied are preserved separately and every score is vs the
original request.

## DONE 09-05: mechanism built + tested + paired CPU suite run

**New files (default-off, no shared-code edits at all):**
- `rl_move/sim/command_envelope.py` — `CommandEnvelope` governor.
  `EnvelopeConfig.enabled=False` default; disabled step is an identity
  passthrough (bit-exact legacy). Two governed modes: `shared` (one
  authority scalar on all axes, preserves curvature) and
  `yaw_priority` (sheds translation demand only; yaw passes intact).
  Rate limits 0.16 m/s² / 0.50 rad/s² (contract speeds from zero in
  ~0.5 s); feedback law: authority in [0.35, 1], shrinks
  4.0/s·(sat−0.30) when measured clip-saturation exceeds 0.30
  (between the measured pure-command ~0.245 and combined ~0.419
  bands, `joint_tracking_cap29_scripted_09-03.json`), recovers 0.5/s.
  Governs COMBINED (translation AND yaw) demand only; pure commands
  always run full authority. `safety.max_delta_q_deg`, motor limits,
  rates/frames: untouched.
- `rl_move/sim/eval_command_envelope.py` — paired scripted-gait
  evaluator on the live mesh/100 Hz env (same `make_env`/`WALK_PLANT`
  as `probe_turn_authority`, `env.model_source=mesh control.hz=100`).
  10 scenarios × identical seeds × 3 arms
  (baseline/env_shared/env_yawpri): fwd/rev/lat, turn ccw/cw,
  combined vx=0.08 & wz=±0.25, stop/restart, fwd→rev reversal, yaw
  reversal. Artifacts keep requested vs applied traces separately
  (`traces/*.npz`) and score vs REQUESTED only.
- `rl_move/tests/test_command_envelope.py` — 12 tests (identity when
  disabled incl. under absurd feedback; per-tick continuity bounds on
  steps/stops/reversals; throttle+floor+recovery; combined-only
  gating; yaw-priority sheds translation only; scoring is vs
  requested — a perfectly-tracked throttled command still scores the
  miss; parking scores 0 progress). All pass.

**Result artifacts:** `logs/ckpt_eval/command_envelope_v1_09-05/`
(summary.json + 60 trace npz). Zero falls in all 60 rollouts;
support_lt3_frac = 0.0 everywhere; contact_mean ~3.3.

### Honest read (paired, vs baseline, seed-deterministic)

NOTE: with `randomize=False`/DR-0 and the goal traj overwritten by
the script, rollouts are fully deterministic — seeds 0/1 are
identical, so this is n=1 per cell by construction (fine for a
scripted mechanism screen; DR/stochastic replication is a next step
if the candidate goes anywhere).

**Combined ticks (vx=0.08, wz=±0.25) — the target regime:**

| metric | baseline | env_shared | env_yawpri |
|---|---|---|---|
| yaw_ratio (achieved/requested) | 0.24 | 0.25 | **0.42** |
| wz achieved med (rad/s) | 0.070 | 0.080 | **0.168** |
| course_err_final (deg, 10 s) | ~109 | ~108 | **~83** |
| progress_ratio (vs requested vx) | 0.372 | 0.239 | 0.166 |
| vx authority applied | 1.0 | 0.48 | 0.35 (floor) |
| slip_per_cmd_m | 0.42 | 0.41 | 0.40 |
| sat_frac_mean | 0.416 | 0.302 | 0.382 |

- **`env_shared` REFUTED**: hits its saturation target (0.30) but
  yaw tracking does not improve (0.24→0.25) while progress drops 36%.
  Cross-confirms the standwalk finding that UNIFORM demand scaling
  trades achieved motion 1:1 against clip relief — no free win.
- **`env_yawpri` is a real candidate WITH A NAMED COST**: shedding
  only translation demand (to the 0.35 floor) recovers 2.4× the real
  yaw rate on combined ticks, both signs symmetric, 26° better
  10-s course — at −55% forward progress vs the request. This is the
  first lever in the whole 09-03..09-05 combined-tick family that
  moves REAL wz at all (every gait-reshaping lever was refuted); it
  works because it changes the demanded translation itself, i.e. the
  vx cross-term that amplifies 3 legs past the slew clip.

**Pure/transition scenarios (baseline fidelity):** envelope arms are
never governed here (combined-only gate); only the rate-limit ramp
differs. Costs are small and mechanical: fwd/rev/lat progress_ratio
−0.9..−1.2 pp (ramp-in); stop_restart −2.3 pp; fwd→rev reversal
−5.3 pp (1 s traverse through zero instead of an instant flip);
yaw-reversal course_err 1.9°→8.8° (the 0.5 s wz traverse ≈7° of yaw).
In exchange, applied-command discontinuities go from 0.08 m/s /
0.25 rad/s instantaneous steps to bounded 0.0016 / 0.005 per tick —
the property the hardware transport (97 overruns/192 ticks, stale-qd
feedback) is expected to care about; that hypothesis is testable only
in Codex's matched transport replay, not here.

### Ruling for the bundle

Baseline (`todaypolicy-mlpsf-tuck-v1`, scripted-gait demand path) is
RETAINED as primary: the demo script never issues wz, and on
translation-only demand the envelope only adds ramp cost. The
envelope is a named, tested, opt-in module for the turn-capable
delivery: `env_yawpri` when combined-command course fidelity matters
more than speed-made-good; `env_shared` should not be used.

## Next

1. [Codex-owned] Integrate `CommandEnvelope` evaluation into the
   deployed-transport replay once it lands; the interesting question
   is whether rate-limited applied commands reduce hardware
   overrun/staleness sensitivity (untestable in this clean-sim suite).
2. Optional here: a `sat_target`/floor dose sweep for `env_yawpri`
   (progress↔yaw Pareto), and DR-on stochastic replication (n≥3),
   ONLY if the transport replay shows the mechanism matters on the
   deployed loop.
3. Specific next mechanism if yaw authority itself remains the
   blocker: schedule combined demand in TIME (alternate short
   pure-turn/pure-walk bursts within the request envelope) — the
   measured pure-turn yaw_ratio 0.54 vs combined 0.24 gap says
   time-slicing beats simultaneous demand at fixed slew budget.

## Boundaries

- No physical robot access from this track (unchanged).
- `standwalk`'s single-policy goal is unchanged; this is delivery
  glue, not the monolithic policy.
- Do not edit Codex-owned files listed at top until the handoff.
