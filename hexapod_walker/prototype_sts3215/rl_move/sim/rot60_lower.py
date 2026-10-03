"""Sector-aware composition wrapper for the `lower` (stance-descent)
role — walkcurr, 2026-10-03 heading-sign forensics -> scoped fix (see
`rl_docs/tracks/walkcurr/lowerrole_fulldir_headingsign_forensics_
2026-10-03/SUMMARY.md`).

WHY THIS EXISTS: the full-direction composed-lifecycle panel
(`lifecycle_fulldir_holdonly100s3_panel`, sharpened the same day) found
the rise->walk->lower composition's `lower_ok` collapses off-axis in a
clean HEADING-SIGN pattern, not a generic off-axis gradient — every
NEGATIVE heading is bad (12-25%) regardless of magnitude, every
POSITIVE heading (and 180) is good-to-perfect (38-100%). The trip
signature differs the same way: negative-heading failures are
UNIVERSALLY joint 7 (L2_pitch) or joint 16 (L5_pitch) — the exact real-
leg pair every over_current forensics doc this week has already named
as this lineage's one discovered stable terminal stance — while
positive-heading failures are joint-diverse. The leading explanation:
the WALK role is rotation-EQUIVARIANT by construction (`rot60.py`,
physics-proven) — it tracks a +/-30 deg wedge and a `Rot60Policy`
wrapper relabels legs to reach the full circle, zero retrain. The
`lower` role was trained with NO heading/sector context at all
(`lower_hold_only_frac=1.0` curriculum starts near final height, no
walk precursor, always in the one fixed real-world orientation the sim
resets to) and — ordinary SAC symmetry-breaking, no explicit
permutation-equivariance constraint on the network — converged on a
FIXED REAL-LEG preference (trusting/unloading real legs L2+L5
specifically) that has no reason to line up with the walk-exit state
left behind at every sector, because a +k-sector walk and a -k-sector
walk are NOT mirror images of each other (rot60 is a rotation group,
not a reflection group).

THE FIX (composition/eval-code only, ZERO RETRAIN, reuses the already-
trained `lower` checkpoint exactly as-is): at the walk->lower handoff,
read the walk role's own final `Rot60Policy.k` (already computed,
already the exact sector the walk role used for its whole drive) and
apply the SAME relabeling to the `lower` role's own observation/action
— so whatever fixed real-leg habit the lower role learned in ITS OWN
(unrotated, k=0) training frame gets consistently re-mapped onto
whichever real legs are sector-appropriate for THIS episode's heading,
instead of being applied blindly in fixed real-leg space regardless of
heading.

DISCOVERY THAT MADE THIS A THIN WRAPPER, NOT A NEW TRANSFORM: the
registered `lower`-role recipe
(`cfg_recipe_stance50hz_rlonly_lowerrole_scratch_sac_drramp.py`) trains
on `SimHexapodJointGoalEnv` (`joint_task.py`) — the RAW-JOINT-ACTION
goal task, NOT the body-IK `SimHexapodGoalEnv` a first read of
`goal_task.py` suggests. Its own docstring says so explicitly: "Same
observations (modulo prev-action width)... the only change is the
action space: 18 channels... one per joint" — i.e. EXACTLY the WALK
role's own per-joint action contract rot60.py already canonicalizes,
not a 6-wide body-offset action at all. Checked directly against the
real checkpoint
(`ppo_goal_cw_stance50hz_rlonly_lowerrole_scratch_sac_s3_drramp_
holdonly100_acq1.zip`): ``observation_space.shape == (68,)`` = q_rel18
+ qd18 + tilt2 + gyro3 + prev_action18 + goal9 — this is BIT-FOR-BIT
`rot60.FRAME_WALK`'s own 72-wide layout with its trailing 4-wide
vx/vy-ref/meas command slice (indices 68:72, which the walk-only
`SimHexapodJointWalkEnv` subclass adds, `SimHexapodJointGoalEnv` does
not) dropped. Every slice rot60.py already transforms (q_rel/qd by
`leg_perm`, tilt/goal-ref by `tilt_rotate`, gyro xy by `rot2`, goal
one-hot by `one_hot_perm`) lines up EXACTLY, so this module is a thin
pad/truncate shim around `rot60.frame_transform` /
`rot60.action_from_canonical` — NOT a re-derivation of the transform
math, which would risk silently drifting from rot60.py's own
test-proven (`test_rot60.py`, including the raw-MuJoCo-dynamics
equivariance check) implementation. Zero-padding the dropped
vx/vy-ref/meas slice before calling `frame_transform` is inert (each
slice is transformed independently, reading only its own input; a
rotated zero vector is still zero) and the padding is discarded again
on the way out.

Unlike the WALK role, the `lower` role has NO velocity command in its
own (68-wide) obs to re-derive a sector from per tick (its goal is a
height/attitude ramp, not a heading) — so `Rot60LowerPolicy` fixes k
ONCE at construction (read from the walk role's own final
`Rot60Policy.k` at the walk->lower handoff) rather than calling
`rot60.sector_from_cmd` every step the way `Rot60Policy` does.

Zero behavior change for anything that doesn't construct
``Rot60LowerPolicy``: this module is new, additive, imported nowhere
by default.
"""
from __future__ import annotations

import numpy as np

from .rot60 import FRAME_WALK, N_LEGS, action_from_canonical, frame_transform

LOWER_FRAME_WIDTH = 68   # SimHexapodJointGoalEnv's own obs width (no
                         # obs.*_sense extras): rot60.FRAME_WALK minus
                         # its trailing 4-wide vref/vmeas command slice


def lower_obs_transform(obs: np.ndarray, k: int) -> np.ndarray:
    """Real-frame `lower` obs (width 68) -> canonical frame (sector k).

    Pads to `rot60.FRAME_WALK` width, reuses `rot60.frame_transform`
    verbatim, truncates back. k=0 is an exact no-op (copy, inherited
    from `frame_transform`'s own k=0 fast path).
    """
    obs = np.asarray(obs, dtype=np.float32)
    if obs.shape[-1] != LOWER_FRAME_WIDTH:
        raise ValueError(
            f"rot60_lower supports the lower-role obs width "
            f"{LOWER_FRAME_WIDTH} only (SimHexapodJointGoalEnv with no "
            f"obs.*_sense extras); got {obs.shape[-1]}")
    padded = np.zeros(FRAME_WALK, dtype=np.float32)
    padded[:LOWER_FRAME_WIDTH] = obs
    canon = frame_transform(padded, k)
    return canon[:LOWER_FRAME_WIDTH].copy()


# The action is the SAME 18-wide per-joint contract the walk role uses
# (joint_task.py: "18 channels in [-1, 1], one per joint" — see module
# docstring), so the inverse map is `rot60.action_from_canonical`
# unchanged; no new function needed here.
lower_action_from_canonical = action_from_canonical


class Rot60LowerPolicy:
    """SB3-predict-compatible wrapper for the `lower` role: sector k is
    FIXED for the whole wrapped episode (read ONCE from the walk
    role's own final ``Rot60Policy.k`` at the walk->lower handoff —
    unlike the walk role, `lower` has no velocity command in its own
    obs to re-derive a sector from per tick).

    Model-agnostic by construction (same contract as
    ``rot60.Rot60Policy``): only ever calls ``model.predict(...)``, so
    it composes with an SB3 model or a plain-numpy export runtime
    alike, and passes through any other attribute callers inspect
    (``observation_space``, ``meta``, ...).
    """

    def __init__(self, model, k: int):
        self.model = model
        self.k = int(k) % N_LEGS

    def __getattr__(self, name):
        return getattr(self.model, name)

    def reset(self):
        # k is fixed for the whole episode by design -- NOT reset here
        # (contrast rot60.Rot60Policy.reset, which zeros a per-episode
        # sector state the walk role re-derives every tick).
        inner_reset = getattr(self.model, "reset", None)
        if inner_reset is not None:
            inner_reset()

    def predict(self, obs, deterministic: bool = True, **kw):
        obs = np.asarray(obs)
        squeeze = obs.ndim == 1
        rows = obs[None, :] if squeeze else obs
        acts = []
        for row in rows:
            canon = lower_obs_transform(row, self.k)
            a, _ = self.model.predict(canon, deterministic=deterministic,
                                      **kw)
            acts.append(lower_action_from_canonical(a, self.k))
        out = np.asarray(acts)
        return (out[0] if squeeze else out), None
