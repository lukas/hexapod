# todaypolicy / hardware_delivery — measured controller delivery

Last updated: 2026-09-05 ~09:1x UTC. **Next#3 (time-sliced demand)
BUILT, TESTED, REFUTED — zero PPO, real mesh/100 Hz physics.** Added
`CommandEnvelope.mode='time_slice'` (default-off, new dataclass fields
`slice_period_s`/`turn_duty`, `EnvelopeOutput.in_turn_slice` telemetry;
16/16 `test_command_envelope.py` green, 4 new tests) implementing
exactly the item-3 idea: alternate FULL-amplitude pure-turn/
pure-translation bursts within a combined-demand period instead of
continuously scaling both axes. Wired into `eval_command_envelope.py`
as 3 dose arms (`env_timeslice_d{30,50,70}`, turn_duty 0.3/0.5/0.7 of
a 1.6 s period) and ran the full 10-scenario x 2-seed paired suite
(`logs/ckpt_eval/command_envelope_timeslice_09-05/summary.json`).
Result on the target `combo_ccw`/`combo_cw` regime (seed0, seed1
identical — deterministic scripted teacher):

| arm | progress_ratio | yaw_ratio | course_err_final (deg) | slip_per_ach_m |
|---|---|---|---|---|
| baseline | 0.372 | 0.240 | -108.9 | 1.24 |
| env_shared | 0.239 | 0.246 | -108 | — |
| env_yawpri | 0.166 | 0.423 | -83 | — |
| env_timeslice_d30 | 0.317 | 0.135 | -124.0 | 1.50 |
| env_timeslice_d50 | 0.227 | 0.255 | -106.7 | 1.76 |
| env_timeslice_d70 | 0.128 | 0.372 | -90.0 | 2.15 |

d30 is DOMINATED by plain `baseline` (worse on both axes — its 0.48 s
burst is shorter than the envelope's own 0.5 s worst-case rate-limit
ramp, so it never reaches the sub-command amplitude before switching
back). d70 is DOMINATED by `env_yawpri` (worse progress AND worse yaw
AND ~2x the slip). d50 ties `env_shared` on both axes (no win, and is
itself no better than baseline on course_err). No duty tested beats
the existing continuous-authority arms on the Pareto front. This
matches the a-priori argument recorded in `command_envelope.py`'s
docstring: the measured vx-authority -> yaw_ratio relationship
(1.0->0.24, 0.35->0.42, 0->0.54) is CONCAVE, so time-averaging two
extremes can only land on or below the chord under that curve —
continuous scaling is provably at least as good as any fixed-duty
time-slice. **Ruling: time-slicing does not reopen the yaw-authority
question; `env_yawpri` stays the best real candidate at its named
-55% progress cost.** Mode kept (tested, opt-in, never wired into
anything default) so nobody re-derives this from scratch; do not
re-attempt without a genuinely different per-burst mechanism (e.g.
scenario-tuned burst durations, not a fixed duty fraction) — no such
mechanism is queued.

Previous update (09-05 ~08:0x), reopened per operator MCP note
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

## DONE 09-05: mechanism built + tested + paired CPU suite run (condensed; full detail in git history of this file)

**New files (default-off, no shared-code edits at all):**
`rl_move/sim/command_envelope.py` (`CommandEnvelope` governor, modes
`shared`/`yaw_priority`/`time_slice`, `EnvelopeConfig.enabled=False`
default = bit-exact identity passthrough), `rl_move/sim/
eval_command_envelope.py` (paired scripted-gait evaluator on the live
mesh/100 Hz env, 10 scenarios x seeds x arms, scores vs REQUESTED
only, traces kept separately), `rl_move/tests/test_command_envelope.py`
(16 tests green). Result artifacts:
`logs/ckpt_eval/command_envelope_v1_09-05/` (first 3 arms, 60
rollouts) and `..._timeslice_09-05/` (time_slice doses, 80 rollouts).
Zero falls across all 140 rollouts; `support_lt3_frac=0.0` everywhere.

**Combined ticks (vx=0.08, wz=±0.25) — the target regime — headline
numbers (progress_ratio / yaw_ratio / course_err_final_deg):**
baseline 0.372/0.24/-109, `env_shared` 0.239/0.25/-108 (REFUTED —
hits its own sat target but yaw doesn't improve, -36% progress for
nothing), `env_yawpri` 0.166/0.42/-83 (best real candidate, -55%
progress cost), `env_timeslice_d{30,50,70}` — see the Update at top
(all 3 doses dominated-by-or-tied-with the above, REFUTED).

**Pure/transition scenarios (baseline fidelity):** envelope arms are
never governed here (combined-only gate); only the rate-limit ramp
differs — small mechanical costs (fwd/rev/lat progress_ratio
−0.9..−1.2 pp; stop_restart −2.3 pp; fwd→rev reversal −5.3 pp;
yaw-reversal course_err 1.9°→8.8°). In exchange, applied-command
discontinuities go from instantaneous 0.08 m/s / 0.25 rad/s steps to
bounded 0.0016 / 0.005 per tick — untested-here hardware-transport
hypothesis, Codex's matched replay owns that read.

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
3. **CLOSED 09-05 (see Update above): time-sliced demand built,
   tested at 3 duty doses, REFUTED** — dominated by or tied with the
   existing continuous-authority arms at every dose, matching the
   concave vx-authority->yaw_ratio curve. Do not re-attempt a
   fixed-duty time-slice mechanism; `env_yawpri` remains the best real
   yaw-authority candidate. No further agent-doable next step on this
   sub-axis; a genuinely different per-burst mechanism (scenario-tuned
   burst durations) is not queued.

## Boundaries

- No physical robot access from this track (unchanged).
- `standwalk`'s single-policy goal is unchanged; this is delivery
  glue, not the monolithic policy.
- Do not edit Codex-owned files listed at top until the handoff.
