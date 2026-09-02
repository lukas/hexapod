"""Level front/rear quadruped crawl with the middle legs tucked.

This is a Drive-tab diagnostic gait, not an RL policy. It keeps the chassis
level, lifts the middle pair (legs 1 and 4) into a conservative tuck, then
crawls on the front/rear four legs with the same world-pinned no-slip engine
as ``NoSlipGait``.
"""
from __future__ import annotations

from .noslip_gait import NoSlipGait

MIDDLE_LEGS = (1, 4)
ACTIVE_LEGS = (0, 2, 3, 5)
TUCK_DEG = (0.0, -62.0, 112.0)


def _smoothstep(x: float) -> float:
    x = max(0.0, min(1.0, float(x)))
    return x * x * (3.0 - 2.0 * x)


class MiddleTuckQuadGait(NoSlipGait):
    """Crawl on the front/rear four legs while holding the middle pair up.

    The first scheduled "swing" is the middle pair. Because ``desired_deg``
    overrides those two legs with a tuck ramp, startup becomes:

      all feet down -> middle pair tucks -> front/rear crawl begins

    After that the active feet swing one at a time, so at least three of the
    four active support legs remain planted.
    """

    MAX_VX = 0.030
    MAX_VY = 0.020
    MAX_OMEGA = 0.20
    STRIDE_MAX = 0.090
    YAW_STEP_MAX = 0.22

    QUAD_GROUPS = ((1, 4), (0,), (3,), (2,), (5,))
    QUAD_CRAWL_KW = dict(period=10.0, lift=0.030, shift_frac=0.02,
                         swing_frac=0.16, alpha=1.0, groups=QUAD_GROUPS)

    def __init__(self, *, tuck_deg=TUCK_DEG, tuck_ramp_s: float = 1.6,
                 **kw):
        super().__init__(**{**self.QUAD_CRAWL_KW, **kw})
        self.tuck_deg = tuple(float(v) for v in tuck_deg)
        self.tuck_ramp_s = max(float(tuck_ramp_s), 0.1)
        self._tuck_elapsed = 0.0
        self._tuck_last_t: float | None = None

    @classmethod
    def crawl(cls, **kw) -> "MiddleTuckQuadGait":
        return cls(**kw)

    def reset_phase(self, *, phase: float = 0.0, t: float = 0.0) -> None:
        super().reset_phase(phase=phase, t=t)
        self._tuck_elapsed = 0.0
        self._tuck_last_t = t if t else None

    def desired_deg(self, t: float) -> list[float]:
        if self._tuck_last_t is None:
            self._tuck_last_t = t
        dt = max(0.0, float(t) - self._tuck_last_t)
        self._tuck_last_t = float(t)
        self._tuck_elapsed += dt

        out = super().desired_deg(t)
        u = _smoothstep(self._tuck_elapsed / self.tuck_ramp_s)
        plant = (0.0, self.plant_hip_deg, self.plant_knee_deg)
        for leg in MIDDLE_LEGS:
            off = 3 * leg
            out[off:off + 3] = [
                plant[j] + u * (self.tuck_deg[j] - plant[j])
                for j in range(3)
            ]
        return out
