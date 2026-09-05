"""command_envelope.py — opt-in measured-feasibility command governor.

todaypolicy hardware-delivery item (operator MCP note
fb_20260905T071610_749846, 09-05): the Sep-3 hardware walk ran the
frozen 100 Hz policy open-loop against stepped joystick requests and
achieved 19.5 mm/s vs the sim's 34.6-43.9 — and every prior standwalk
combined-tick lever (yaw-arm scale, per-leg amplify, selective omega
boost, group duty skew — all in ``hexapod_core.tripod_gait``) reshaped
the GAIT for a fixed demand and was refuted zero-training. This module
is the genuinely different mechanism the note asks for: it governs the
COMMAND (vx, vy, wz) handed to the (unchanged) scripted gait, using
measured joint-slew feasibility fed back from the executed loop:

  1. **Continuous, rate-limited applied commands**: the applied
     (vx, vy, wz) slews toward the requested values at a bounded rate,
     so stepped joystick requests, stop/restart, and sign reversals
     never hit the gait as discontinuities (the legacy path relies on
     ``TripodGait``'s internal tau=0.15 smoothing of an instantaneous
     set_velocity step — that smoothing stays; this bounds the INPUT).
  2. **Measured-saturation authority governor**: each tick the caller
     reports the fraction of joint cells whose per-tick slew demand
     saturated the ``safety.max_delta_q_deg`` clip on the PREVIOUS
     executed tick (the same |desired - cmd| > max_dq - 1e-4 statistic
     ``probe_joint_tracking.py`` scores). When that measured
     saturation exceeds ``sat_target``, a scalar authority g in
     [authority_floor, 1] shrinks; when the loop is feasible again, g
     recovers toward 1. Authority scales the SIMULTANEOUS demand: in
     ``shared`` mode all axes shrink together (preserves the requested
     path curvature vx/wz, slows traversal); in ``yaw_priority`` mode
     only the translation axes shrink (the 09-04 per-leg analysis
     showed vx's cross term is what amplifies 3 legs past the clip on
     combined ticks, so shedding translation demand is the axis-
     targeted way to buy yaw feasibility back).
  4. **Time-sliced demand (``mode='time_slice'``, 09-05 follow-up,
     hardware_delivery STATUS Next#3) — BUILT, TESTED, REFUTED.**
     Instead of continuously scaling both axes down together, alternate
     FULL-amplitude pure-turn and pure-translation bursts within a
     combined-demand period (each burst is, by construction, the
     un-degraded single-axis command). Measured on the same
     scripted-gait suite at 3 turn-duty doses
     (`logs/ckpt_eval/command_envelope_timeslice_09-05/summary.json`,
     `combo_ccw`/`combo_cw`, seed 0/1 identical): turn_duty=0.3 is
     DOMINATED by plain ``baseline`` (worse progress_ratio 0.32 vs
     0.37 AND worse yaw_ratio 0.14 vs 0.24 — the 0.48 s burst at that
     duty is shorter than the envelope's own 0.5 s worst-case
     rate-limit ramp, so it never even reaches the sub-command
     amplitude); turn_duty=0.7 is DOMINATED by ``yaw_priority`` (worse
     progress_ratio 0.13 vs 0.17 AND worse yaw_ratio 0.37 vs 0.42,
     plus ~2x the per-achieved-meter slip); turn_duty=0.5 ties
     ``shared`` on both axes (no win). Matches the a-priori argument:
     the measured vx-authority -> yaw_ratio curve (1.0->0.24,
     0.35->0.42, 0->0.54) is CONCAVE, so any point obtained by time-
     averaging two extremes sits on or below the chord under that
     curve — continuous authority scaling is provably at least as
     good. Kept as a tested, opt-in mode (never wired into anything
     default) so the negative result is reproducible; do not re-derive
     this from scratch or re-attempt without a genuinely different
     per-burst mechanism (e.g. per-burst durations tuned individually
     per scenario, not a fixed duty fraction).

HONESTY CONTRACT (from the same operator note): requested and applied
commands are separate, both are preserved by the caller, and all
scoring is against the ORIGINAL requests — throttling or parking can
never fake success. This module only computes; it never rewrites the
requested history.

DEFAULT-OFF: ``EnvelopeConfig.enabled`` defaults to False and a
disabled ``CommandEnvelope.step`` returns the requested tuple
unchanged (identity, no internal-state side effects on the applied
path) — bit-exact with the legacy direct ``set_velocity`` path. No
shared training/eval code imports this module; it is opt-in via
``eval_command_envelope.py`` only. Safety limits
(``safety.max_delta_q_deg``, motor limits, control rates) are never
touched — the governor works strictly BELOW them, shaping demand.

Pure stdlib/dataclass math (no MuJoCo/numpy import) so the complete
feedback law is unit-testable in microseconds:
``rl_move/tests/test_command_envelope.py``.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field


def _clip(v: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, v))


@dataclass
class EnvelopeConfig:
    """Tunables for the measured-feasibility command governor.

    Defaults were chosen from MEASURED scripted-teacher saturation on
    the mesh/100 Hz model (logs/ckpt_eval/joint_tracking_cap29_
    scripted_09-03.json): pure-turn clip_sat_frac_all ~0.245, combined
    ~0.419. ``sat_target=0.30`` sits above the pure-command band (so
    pure translations/turns are never throttled by feedback noise) and
    below the combined-tick band (so genuinely infeasible simultaneous
    demand IS governed). The rate limits reach the contract speeds
    (0.08 m/s, 0.25 rad/s) from zero in ~0.5 s — same order as
    TripodGait's own tau=0.15 smoothing settles, so the envelope
    shapes transitions without dominating them.
    """
    enabled: bool = False
    # Applied-command slew limits (units/second).
    vx_rate: float = 0.16    # m/s per s  -> 0 -> 0.08 in 0.5 s
    vy_rate: float = 0.16
    wz_rate: float = 0.50    # rad/s per s -> 0 -> 0.25 in 0.5 s
    # Measured-saturation feedback governor.
    sat_target: float = 0.30    # tolerated saturated-cell fraction/tick
    gain_down: float = 4.0      # authority shrink per unit excess sat (1/s)
    gain_up: float = 0.5        # authority recovery toward 1.0 (1/s)
    authority_floor: float = 0.35  # never throttle demand below this
    # 'shared': scale vx/vy/wz together (preserves curvature).
    # 'yaw_priority': scale only translation; yaw demand passes intact.
    # 'time_slice': alternate FULL-amplitude pure-turn and pure-walk
    # bursts within a combined-demand period instead of continuously
    # scaling both axes down together (see module docstring item 4).
    mode: str = "shared"
    # Governor acts only when translation AND yaw are simultaneously
    # requested (the measured-infeasible regime); pure commands always
    # run at full authority. Rate limiting applies regardless.
    combined_only: bool = True
    eps_cmd: float = 1e-6
    # time_slice tunables (ignored by shared/yaw_priority). Period is
    # split turn_duty/1-turn_duty between a yaw-only burst (vx=vy=0,
    # full wz) and a translation-only burst (full vx/vy, wz=0). Default
    # period (1.6 s) gives each half >= 0.3 s of full-amplitude dwell
    # after the envelope's own 0.5 s worst-case rate-limit ramp
    # (0.08 m/s @ 0.16 m/s^2 / 0.25 rad/s @ 0.50 rad/s^2) so a burst
    # actually reaches the sub-command amplitude before switching back.
    slice_period_s: float = 1.6
    turn_duty: float = 0.5


@dataclass
class EnvelopeOutput:
    """One tick of governor output. ``requested`` is echoed verbatim so
    artifact writers can never lose the original demand."""
    requested: tuple[float, float, float]
    applied: tuple[float, float, float]
    target: tuple[float, float, float]
    authority: float
    governing: bool  # feedback law active this tick (combined demand)
    in_turn_slice: bool = False  # time_slice telemetry only; always
                                 # False in shared/yaw_priority modes.


class CommandEnvelope:
    def __init__(self, cfg: EnvelopeConfig | None = None):
        self.cfg = cfg or EnvelopeConfig()
        self.reset()

    def reset(self) -> None:
        self._applied = [0.0, 0.0, 0.0]
        self._authority = 1.0
        self._slice_t = 0.0

    @property
    def authority(self) -> float:
        return self._authority

    def step(self, dt: float, requested: tuple[float, float, float],
             measured_sat_frac: float | None) -> EnvelopeOutput:
        """Advance one control tick.

        ``measured_sat_frac``: fraction (0..1) of joint cells whose
        slew demand saturated the safety clip on the PREVIOUS executed
        tick (None on the first tick / when no measurement exists —
        treated as feasible). One-tick-delayed feedback is the point:
        this is the complete measured loop, not a model prediction.
        """
        c = self.cfg
        vx_r, vy_r, wz_r = (float(requested[0]), float(requested[1]),
                            float(requested[2]))
        if not c.enabled:
            # Identity passthrough — bit-exact legacy behavior.
            return EnvelopeOutput(requested=(vx_r, vy_r, wz_r),
                                  applied=(vx_r, vy_r, wz_r),
                                  target=(vx_r, vy_r, wz_r),
                                  authority=1.0, governing=False)
        dt = max(float(dt), 0.0)
        translation = math.hypot(vx_r, vy_r)
        combined = translation > c.eps_cmd and abs(wz_r) > c.eps_cmd
        governing = combined or not c.combined_only

        in_turn_slice = False
        if c.mode == "time_slice":
            # Bypasses the continuous authority feedback by design: each
            # burst already restricts demand to a single axis (a "pure"
            # sub-command), which the measured data shows runs near full
            # authority on its own (module docstring item 4) — no
            # additional scaling is layered on top. The phase clock only
            # advances while governing so entering/leaving a combined
            # period always resumes at the start of a turn-burst.
            if governing:
                self._slice_t = (self._slice_t + dt) % max(c.slice_period_s, 1e-9)
            else:
                self._slice_t = 0.0
            turn_window = c.turn_duty * c.slice_period_s
            in_turn_slice = governing and (self._slice_t < turn_window)
            self._authority = 1.0
            if governing:
                target = ((0.0, 0.0, wz_r) if in_turn_slice
                          else (vx_r, vy_r, 0.0))
            else:
                target = (vx_r, vy_r, wz_r)
            g = 1.0
        else:
            sat = (float(measured_sat_frac) if measured_sat_frac is not None
                   else 0.0)
            if governing and sat > c.sat_target:
                self._authority -= c.gain_down * (sat - c.sat_target) * dt
            else:
                self._authority += c.gain_up * (1.0 - self._authority) * dt
            self._authority = _clip(self._authority, c.authority_floor, 1.0)

            g = self._authority if governing else 1.0
            if c.mode == "yaw_priority":
                target = (vx_r * g, vy_r * g, wz_r)
            else:  # shared
                target = (vx_r * g, vy_r * g, wz_r * g)

        rates = (c.vx_rate, c.vy_rate, c.wz_rate)
        applied = []
        for i in range(3):
            step_max = rates[i] * dt
            delta = _clip(target[i] - self._applied[i], -step_max, step_max)
            applied.append(self._applied[i] + delta)
        self._applied = applied
        return EnvelopeOutput(requested=(vx_r, vy_r, wz_r),
                              applied=tuple(applied),
                              target=target,
                              authority=g, governing=governing,
                              in_turn_slice=in_turn_slice)
