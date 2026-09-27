"""Idle guard: a robot nobody is talking to must not stand or strain forever.

Lukas, 2026-09-27: "if it's standing with no command for 20 minutes it sits, and
if it's drawing current with no motion or requests for more than an hour it limps
the motors."  (Same day the robot was found standing since the previous evening
with two hips at 55 C.)

Pure state machine; the servo watchdog feeds it one sample per read and runs the
actions it returns.  Time comes from the caller (testable).

  sample: armed, busy (a demo/job thread owns the bus), rl_active (an RL drive
          session is open -- its heartbeats are requests anyway), standing
          (classifier verdict, None = unknown), positions {joint: deg},
          total_current_a, last_request_mono (any POST the web service received).

  "sit"  : armed, not busy, not rl_active, standing, no request for sit_after_s
           -> the owner plays STEP down.  One attempt, then a cool-off; if the
           robot still reads standing after that it is NOT retried (a sit that
           fails is a lockout, not a loop) -- the limp rule still applies.
  "limp" : armed, not busy, not rl_active, no motion, total current above the
           floor, no request AND no motion for limp_after_s -> the owner
           releases torque gently (static_strain_release).  This can lower a
           standing robot uncontrolled; Lukas asked for exactly that as the
           last resort.

"No motion" is judged from POSITIONS (every joint moved < move_deg since the
previous sample), not the speed register: at rest the STS3215 speed reads up to
~30 deg/s of noise (measured 2026-09-27) while positions sit within 0.5 deg.
"""
from __future__ import annotations

import os

SIT_AFTER_S = float(os.environ.get("HEXAPOD_IDLE_SIT_S", "1200"))          # 20 min; 0 disables
LIMP_AFTER_S = float(os.environ.get("HEXAPOD_IDLE_LIMP_S", "3600"))        # 60 min; 0 disables
LIMP_CURRENT_A = float(os.environ.get("HEXAPOD_IDLE_LIMP_CURRENT_A", "0.15"))  # total; belly-down at zero reads ~0
SIT_COOLOFF_S = 300.0
MOVE_DEG = 1.0


class IdleGuard:
    def __init__(self, *, sit_after_s: float = SIT_AFTER_S, limp_after_s: float = LIMP_AFTER_S,
                 limp_current_a: float = LIMP_CURRENT_A, cooloff_s: float = SIT_COOLOFF_S,
                 move_deg: float = MOVE_DEG) -> None:
        self.sit_after_s = float(sit_after_s)
        self.limp_after_s = float(limp_after_s)
        self.limp_current_a = float(limp_current_a)
        self.cooloff_s = float(cooloff_s)
        self.move_deg = float(move_deg)
        self._prev_pos: dict[int, float] | None = None
        self._last_motion: float | None = None
        self._sit_at: float | None = None       # when the last sit was requested
        self._sit_lockout = False               # sit attempted and the robot still stands
        self._limped = False
        self.state: dict = {"enabled": self.sit_after_s > 0 or self.limp_after_s > 0}

    # -- helpers
    def _moved(self, positions: dict[int, float] | None, now: float) -> bool:
        if not positions:
            return False
        if self._prev_pos is None:
            self._prev_pos = dict(positions); self._last_motion = now
            return True
        moved = any(abs(float(positions[j]) - float(self._prev_pos[j])) >= self.move_deg
                    for j in positions if j in self._prev_pos)
        self._prev_pos = dict(positions)
        if moved:
            self._last_motion = now
        return moved

    def observe(self, now: float, *, armed: bool, busy: bool, rl_active: bool, standing: bool | None,
                positions: dict[int, float] | None, total_current_a: float,
                last_request_mono: float | None) -> str | None:
        moved = self._moved(positions, now)
        if self._last_motion is None:
            self._last_motion = now
        since_req = None if last_request_mono is None else max(0.0, now - last_request_mono)
        since_motion = max(0.0, now - self._last_motion)
        external = bool(busy or rl_active)
        if external or not armed:
            # someone is driving, or nothing to protect: reset the sit cycle
            self._sit_at = None; self._sit_lockout = False
            if not armed:
                self._limped = False
        action = None
        idle_s = since_req if since_req is not None else since_motion   # no request ever seen -> motion clock
        if armed and not external and since_req is not None:
            if (self.sit_after_s > 0 and standing and since_req >= self.sit_after_s
                    and not self._sit_lockout
                    and (self._sit_at is None or now - self._sit_at >= self.cooloff_s)):
                if self._sit_at is not None:
                    # cool-off elapsed and it still stands: one attempt only
                    self._sit_lockout = True
                else:
                    self._sit_at = now
                    action = "sit"
            if (action is None and self.limp_after_s > 0 and not self._limped and not moved
                    and since_req >= self.limp_after_s and since_motion >= self.limp_after_s
                    and float(total_current_a) > self.limp_current_a):
                self._limped = True
                action = "limp"
        self.state = {
            "enabled": self.sit_after_s > 0 or self.limp_after_s > 0,
            "sit_after_s": self.sit_after_s, "limp_after_s": self.limp_after_s,
            "limp_current_a": self.limp_current_a,
            "since_request_s": None if since_req is None else round(since_req, 1),
            "since_motion_s": round(since_motion, 1),
            "armed": bool(armed), "external_control": external, "standing": standing,
            "total_current_a": round(float(total_current_a), 3),
            "sit_requested_s_ago": None if self._sit_at is None else round(now - self._sit_at, 1),
            "sit_lockout": self._sit_lockout, "limped": self._limped,
            "last_action": action or self.state.get("last_action"),
        }
        return action
