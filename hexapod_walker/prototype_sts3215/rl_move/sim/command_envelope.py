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
    mode: str = "shared"
    # Governor acts only when translation AND yaw are simultaneously
    # requested (the measured-infeasible regime); pure commands always
    # run at full authority. Rate limiting applies regardless.
    combined_only: bool = True
    eps_cmd: float = 1e-6


@dataclass
class EnvelopeOutput:
    """One tick of governor output. ``requested`` is echoed verbatim so
    artifact writers can never lose the original demand."""
    requested: tuple[float, float, float]
    applied: tuple[float, float, float]
    target: tuple[float, float, float]
    authority: float
    governing: bool  # feedback law active this tick (combined demand)


class CommandEnvelope:
    def __init__(self, cfg: EnvelopeConfig | None = None):
        self.cfg = cfg or EnvelopeConfig()
        self.reset()

    def reset(self) -> None:
        self._applied = [0.0, 0.0, 0.0]
        self._authority = 1.0

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
        sat = float(measured_sat_frac) if measured_sat_frac is not None else 0.0
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
                              authority=g, governing=governing)
