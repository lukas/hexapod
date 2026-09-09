"""Absolute-deadline control loop scheduler."""
from __future__ import annotations

import time
from collections import deque
from dataclasses import dataclass, field
from math import isfinite
from typing import Callable


class CadenceStats:
    """Observe tick starts, including waits and work after stage timers stop.

    This is passive telemetry: it never sleeps or changes the control clock.
    Totals cover the run; percentile storage is bounded to the latest window.
    """

    def __init__(self, period_s: float, *, grace_s: float = 0.0,
                 window_size: int = 1000):
        if not isfinite(period_s) or period_s <= 0:
            raise ValueError("period_s must be finite and positive")
        if not isfinite(grace_s) or grace_s < 0 or window_size < 1:
            raise ValueError("invalid cadence grace or window size")
        self.period_s = period_s
        self.grace_s = grace_s
        self.previous_start = None
        self.last_period_s = None
        self.intervals = 0
        self.elapsed_s = 0.0
        self.max_period_s = 0.0
        self.late_intervals = 0
        self._recent = deque(maxlen=window_size)

    def observe(self, started_at: float) -> None:
        if not isfinite(started_at):
            return
        if self.previous_start is None:
            self.previous_start = started_at
            return
        period = started_at - self.previous_start
        if period <= 0:
            return
        self.previous_start = started_at
        self.last_period_s = period
        self.intervals += 1
        self.elapsed_s += period
        self.max_period_s = max(self.max_period_s, period)
        self.late_intervals += period > self.period_s + self.grace_s + 1e-9
        self._recent.append(period)

    @property
    def measured_hz(self) -> float | None:
        return self.intervals / self.elapsed_s if self.intervals else None

    def summary(self) -> dict:
        recent = sorted(self._recent)

        def percentile_ms(fraction):
            if not recent:
                return None
            pos = (len(recent) - 1) * fraction
            lo = int(pos)
            hi = min(lo + 1, len(recent) - 1)
            return round((recent[lo] + (recent[hi] - recent[lo])
                          * (pos - lo)) * 1000.0, 3)

        return {
            "target_hz": round(1.0 / self.period_s, 3),
            "measured_hz": (round(self.measured_hz, 3)
                            if self.intervals else None),
            "intervals": self.intervals,
            "mean_period_ms": (round(self.elapsed_s / self.intervals * 1000, 3)
                               if self.intervals else None),
            "max_period_ms": (round(self.max_period_s * 1000, 3)
                              if self.intervals else None),
            "late_intervals": self.late_intervals,
            "late_grace_ms": round(self.grace_s * 1000, 3),
            "recent_intervals": len(recent),
            "recent_p95_period_ms": percentile_ms(0.95),
            "recent_p99_period_ms": percentile_ms(0.99),
        }


@dataclass
class TickTiming:
    actual_dt: float = 0.0
    work_s: float = 0.0
    overrun: bool = False
    tick_index: int = 0


@dataclass
class LoopStats:
    ticks: int = 0
    overruns: int = 0
    sum_dt: float = 0.0
    max_dt: float = 0.0
    max_work: float = 0.0
    last: TickTiming = field(default_factory=TickTiming)


class ControlLoop:
    """Call ``work()`` every ``1/hz`` seconds against absolute deadlines."""

    def __init__(self, hz: float = 50.0):
        self.period = 1.0 / float(hz)
        self.stats = LoopStats()
        self._t_next: float | None = None
        self._t_prev: float | None = None
        self._running = False

    def reset(self) -> None:
        self.stats = LoopStats()
        self._t_next = None
        self._t_prev = None

    def run(self, work: Callable[[TickTiming], None], *,
            duration_s: float | None = None,
            max_ticks: int | None = None,
            should_stop: Callable[[], bool] | None = None) -> LoopStats:
        self._running = True
        t0 = time.monotonic()
        self._t_next = t0
        self._t_prev = None
        n = 0
        while self._running:
            if duration_s is not None and (time.monotonic() - t0) >= duration_s:
                break
            if max_ticks is not None and n >= max_ticks:
                break
            if should_stop is not None and should_stop():
                break

            self._t_next += self.period
            t_start = time.monotonic()
            actual_dt = 0.0 if self._t_prev is None else (t_start - self._t_prev)
            self._t_prev = t_start

            tick = TickTiming(actual_dt=actual_dt, tick_index=n)
            work(tick)
            work_s = time.monotonic() - t_start
            tick.work_s = work_s

            remaining = self._t_next - time.monotonic()
            if remaining > 0:
                time.sleep(remaining)
                tick.overrun = False
            else:
                tick.overrun = True
                self.stats.overruns += 1
                # Resync deadline so one slow tick does not cascade forever.
                self._t_next = time.monotonic()

            self.stats.ticks += 1
            self.stats.sum_dt += actual_dt
            self.stats.max_dt = max(self.stats.max_dt, actual_dt)
            self.stats.max_work = max(self.stats.max_work, work_s)
            self.stats.last = tick
            n += 1

        self._running = False
        return self.stats

    def stop(self) -> None:
        self._running = False
