"""Shared high-step tripod gait preset for robot and MuJoCo demos."""
from __future__ import annotations

from dataclasses import dataclass, replace


@dataclass(frozen=True)
class DemoTripodPreset:
    period_s: float = 1.80
    lift_mm: float = 40.0
    ramp_s: float = 0.85
    stride_scale: float = 0.55
    max_vx_mm_s: float = 30.0
    max_vy_mm_s: float = 18.0
    max_omega_rad_s: float = 0.35

    @property
    def lift_m(self) -> float:
        return self.lift_mm * 0.001

    @property
    def max_vx_mps(self) -> float:
        return self.max_vx_mm_s * 0.001

    @property
    def max_vy_mps(self) -> float:
        return self.max_vy_mm_s * 0.001

    def tripod_kwargs(self) -> dict[str, float]:
        return {
            "period": self.period_s,
            "lift": self.lift_m,
            "ramp": self.ramp_s,
            "stride_scale": self.stride_scale,
        }

    def play_row(self, tag: str | None = None) -> dict[str, float | str]:
        label = tag or (
            f"high-step {self.period_s:.2f}s/{self.lift_mm:.0f}mm/"
            f"stride {self.stride_scale:.2f}"
        )
        return {
            "period": self.period_s,
            "lift_mm": self.lift_mm,
            "ramp": self.ramp_s,
            "stride_scale": self.stride_scale,
            "cruise": self.max_vx_mps,
            "omega": self.max_omega_rad_s,
            "tag": label,
        }


DEFAULT_DEMO_TRIPOD = DemoTripodPreset()

DEMO_TRIPOD_LIMITS = {
    "period_s": (0.75, 3.00),
    "lift_mm": (10.0, 50.0),
    "ramp_s": (0.10, 2.50),
    "stride_scale": (0.30, 1.20),
    "max_vx_mm_s": (10.0, 60.0),
    "max_vy_mm_s": (5.0, 40.0),
    "max_omega_rad_s": (0.05, 0.60),
}

_ALIASES = {
    "period": "period_s",
    "period_s": "period_s",
    "lift": "lift_mm",
    "lift_mm": "lift_mm",
    "ramp": "ramp_s",
    "ramp_s": "ramp_s",
    "stride": "stride_scale",
    "stride_scale": "stride_scale",
    "vx": "max_vx_mm_s",
    "max_vx": "max_vx_mm_s",
    "max_vx_mm_s": "max_vx_mm_s",
    "vy": "max_vy_mm_s",
    "max_vy": "max_vy_mm_s",
    "max_vy_mm_s": "max_vy_mm_s",
    "omega": "max_omega_rad_s",
    "max_omega": "max_omega_rad_s",
    "max_omega_rad_s": "max_omega_rad_s",
}


def _clamp(key: str, value: float) -> float:
    lo, hi = DEMO_TRIPOD_LIMITS[key]
    return max(lo, min(hi, float(value)))


def tune_demo_tripod(
        preset: DemoTripodPreset,
        updates: dict[str, float]) -> DemoTripodPreset:
    vals: dict[str, float] = {}
    for raw_key, raw_value in updates.items():
        key = _ALIASES.get(str(raw_key).strip())
        if key is None:
            raise ValueError(f"unknown tripod tune field {raw_key!r}")
        vals[key] = _clamp(key, float(raw_value))
    return replace(preset, **vals)


def parse_demo_tripod_tune_tokens(tokens: list[str]) -> dict[str, float]:
    out: dict[str, float] = {}
    for tok in tokens:
        if "=" not in tok:
            raise ValueError("expected key=value")
        key, value = tok.split("=", 1)
        key = key.strip()
        if not key:
            raise ValueError("empty tune key")
        try:
            out[key] = float(value)
        except ValueError as exc:
            raise ValueError(f"bad value for {key}") from exc
    return out


def format_demo_tripod(preset: DemoTripodPreset) -> str:
    return (
        f"period={preset.period_s:.2f}s "
        f"lift={preset.lift_mm:.0f}mm "
        f"stride={preset.stride_scale:.2f} "
        f"ramp={preset.ramp_s:.2f}s "
        f"vx={preset.max_vx_mm_s:.0f}mm/s "
        f"vy={preset.max_vy_mm_s:.0f}mm/s "
        f"omega={preset.max_omega_rad_s:.2f}rad/s"
    )
