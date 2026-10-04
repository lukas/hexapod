"""TwoStageLowerPolicy: a deterministic-tick-count handoff between a
`lower`-role DESCENT checkpoint and a separately-trained terminal-HOLD
specialist, for `eval_lifecycle_handoff_rlonly.py --lower-specialist`.

Mechanism: the only way to honestly evaluate whether a dedicated
terminal-hold specialist (trained from-scratch on `goal.lower_term_bank`
+ `goal.lower_term_start_frac=1.0` -- see goal_task.py's GoalGenerator
docstring) actually helps the converged 2-leg(L2+L5) terminal-support
habit (`lowerrole_terminal_support_forensics_2026-10-02/SUMMARY.md`) is
to drive the REAL composed episode with the baseline champion handling
the real descent (it already does this competently, ~72-76%
`lower_ok`) and hand off to the specialist only once the commanded ramp
has provably finished -- the specialist never needs to practice
descent, matching exactly what its own training distribution teaches
it (closing the gap that made `goal.lower_hold_only_frac=1.0` fail: that
mechanism asked ONE policy to do the whole episode including a descent
it never trained on; this wrapper never asks the specialist to
descend). The switch is a FIXED TICK COUNT (not a live height-
convergence check) so this wrapper needs no env access at all --
goal_task.py's own `lower` schedule is deterministic wall-clock
(`lower_hold_s` dwell + `lower_ramp_s` ramp, both fixed per recipe), so
the ramp's completion tick is known in advance from the recipe alone.

Pure external orchestration of two already-trained policies -- no
env/reward code touched, carries zero risk to shared training-time
defaults, exactly the same "role-selection plumbing, not a scripted
motion role" category as rot60_lower.Rot60LowerPolicy."""
from __future__ import annotations


class TwoStageLowerPolicy:
    def __init__(self, base, specialist, switch_tick: int):
        if switch_tick < 0:
            raise ValueError("switch_tick must be >= 0")
        self.base = base
        self.specialist = specialist
        self.switch_tick = int(switch_tick)
        self._t = 0

    @property
    def observation_space(self):
        # Both roles observe the SAME task/env contract (goal-mix
        # lower=1.0, joint_goal) by construction -- assert instead of
        # silently trusting it so a mismatched specialist checkpoint
        # fails loudly at construction, not mid-episode.
        base_space = self.base.observation_space
        spec_space = self.specialist.observation_space
        if tuple(base_space.shape) != tuple(spec_space.shape):
            raise ValueError(
                "TwoStageLowerPolicy: base/specialist obs widths "
                f"differ ({base_space.shape} vs {spec_space.shape}) "
                "-- they must share the same obs contract")
        return base_space

    def reset(self) -> None:
        self._t = 0
        if hasattr(self.base, "reset"):
            self.base.reset()
        if hasattr(self.specialist, "reset"):
            self.specialist.reset()

    def predict(self, obs, deterministic: bool = True):
        model = (self.specialist if self._t >= self.switch_tick
                 else self.base)
        action, state = model.predict(obs, deterministic=deterministic)
        self._t += 1
        return action, state
