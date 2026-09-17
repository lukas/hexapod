"""SimHexapodJointGoalEnv — the goal task with RAW JOINT actions.

Same observations (modulo prev-action width), goals, rewards, safety
layer and servo model as ``SimHexapodGoalEnv``; the only change is the
action space: 18 channels in [-1, 1], one per joint, mapped to an
ABSOLUTE joint target across the full hardware axis range:

    q_target[j] = center(axis) + a[j] * half_range(axis)

with (lo, hi) from ``AXIS_LIMITS_DEG`` (yaw ±35°, hip −80..30°, knee
−20..150°). a = 0 therefore commands the mid-range pose, and every
reachable pose is expressible — including the flat zero pose and the
plant, which the body-IK action space can only reach through the curl
ratchet. The SafetyLayer's per-tick rate limit (max_delta_q_deg) and
axis clipping still apply downstream, exactly as they would on
hardware, so "raw" never means "unfiltered".

There is no IK and no foot anchoring here: the policy owns foot
placement. That makes the task harder to explore (18 dims vs 6) but
removes the structural ceiling the IK imposes on gait discovery.

A policy trained on the body-IK task cannot be loaded directly (both
obs and action widths change); use BC distillation to warm-start
(see ``distill_joint_policy.py``).
"""
from __future__ import annotations

import numpy as np

from rl_move.config import cfg_get
from rl_move.env import (GOAL_DIM, current_sense_obs_dim,
                          height_err_sense_obs_dim,
                          height_vel_sense_obs_dim)
from rl_move.robot_state import DEG2RAD, N_JOINTS
from rl_move.safety import AXIS_LIMITS_DEG

from .goal_task import SimHexapodGoalEnv
from .sim_env import N_OBS

try:
    import gymnasium as _gym
except Exception:  # pragma: no cover
    _gym = None

# Per-joint affine map [-1,1] -> radians, from the hardware axis limits.
_CENTER_RAD = np.array([
    (AXIS_LIMITS_DEG[j % 3][0] + AXIS_LIMITS_DEG[j % 3][1]) * 0.5 * DEG2RAD
    for j in range(N_JOINTS)])
_HALF_RAD = np.array([
    (AXIS_LIMITS_DEG[j % 3][1] - AXIS_LIMITS_DEG[j % 3][0]) * 0.5 * DEG2RAD
    for j in range(N_JOINTS)])


def action_to_q_rad(action: np.ndarray) -> np.ndarray:
    """Map a clipped [-1,1]^18 action to absolute joint targets (rad)."""
    return _CENTER_RAD + np.asarray(action, dtype=float) * _HALF_RAD


def q_rad_to_action(q_rad: np.ndarray) -> np.ndarray:
    """Inverse map (used by the BC distillation to label joint targets)."""
    return np.clip((np.asarray(q_rad, dtype=float) - _CENTER_RAD)
                   / _HALF_RAD, -1.0, 1.0)


class SimHexapodJointGoalEnv(SimHexapodGoalEnv):
    """Goal-conditioned twin with raw 18-joint actions (obs 59 + 9)."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.n_act = N_JOINTS
        self._prev_action = np.zeros(self.n_act, dtype=float)
        if _gym is not None:
            self.action_space = _gym.spaces.Box(
                -1.0, 1.0, shape=(self.n_act,), dtype=np.float32)
            self.observation_space = self._obs_space_box(
                N_OBS - 6 + self.n_act + GOAL_DIM
                + current_sense_obs_dim(self.cfg)
                + height_err_sense_obs_dim(self.cfg)
                + height_vel_sense_obs_dim(self.cfg))
        # Action-centering bias (2026-08-24, walkcurr rung-1 dig-in:
        # cw-walkcurr-pf-fwd6-hgt2-pdw05 triage). Root cause found by
        # direct probe (zero action, no policy, no reward at all): the
        # RAW joint action's a=0 point maps to the hardware AXIS
        # MID-RANGE (hip=-25deg, knee=65deg — see `_CENTER_RAD` above),
        # which is NOT anywhere near the settled standing pose q_nom
        # measures at reset (hip~16deg, knee~85deg, matching
        # WALK_PLANT=(20,80) in the semantics bank). Stepping this env
        # with a constant all-zero action (no policy, no learning)
        # sinks the chassis -110mm over 2s while roll/pitch stay
        # EXACTLY 0 the whole time — bit-for-bit the "belly_sit"
        # signature (height_err_end_mm ~110-116mm, level attitude)
        # that every RND / height-gate / park-duty-fix rung-1 arm has
        # converged to, independent of reward mechanism. A freshly
        # initialized (and, per the 08-23 dig-ins, a long-undertrained)
        # policy's mean output sits near 0, so every one of those 20+
        # arms was reproducing this ACTION-SPACE artifact, not a
        # reward-shaped local optimum. This lever lets a recipe shift
        # the zero point toward a real stance WITHOUT changing the
        # mapping's slope (so the full hardware range stays reachable)
        # or any other env's behavior: cfg
        # goal.joint_action_bias_{yaw,hip,knee}_deg, each default 0.0
        # (bit-exact legacy — _act_to_q below reduces to the original
        # one-liner whenever the bias vector is exactly zero).
        #
        # RESTORED 2026-09-02 (orchestrator): deleted by merge 66c4af30
        # ("Merge local main hardware and vision work")'s joint_task.py
        # conflict resolution — content-verified against 631d7f4c, no
        # replacement code was substituted, and every current
        # goal.joint_action_bias_*/goal.joint_action_box_* consumer is
        # in the (retired) walkcurr lineage, so this restore is
        # bit-exact for every live launch (all keys default 0.0 = OFF).
        bias_deg = np.array([
            0.0,   # yaw bias: never a live knob (no run ever set it)
            float(cfg_get(self.cfg, "goal", "joint_action_bias_hip_deg",
                          default=0.0)),
            float(cfg_get(self.cfg, "goal", "joint_action_bias_knee_deg",
                          default=0.0)),
        ] * 6)
        self._joint_action_bias = np.clip(
            bias_deg * DEG2RAD / _HALF_RAD, -1.0, 1.0)
        self._joint_action_bias_active = bool(
            np.any(self._joint_action_bias != 0.0))
        # TURN-IN-PLACE YAW STEERING BIAS (2026-09-17, walkyaw 21st
        # mechanism class). CURRENT_TRUTHS.md's `tkn2` closure (20
        # independently-tried classes: income pricing, termination
        # risk, 4x RND, curriculum exposure, self-distillation, kernel-
        # neutrality, command-difficulty easing, warm-start-vs-scratch,
        # obs-pad-transplant) names the next honest lever as "a
        # genuinely different architecture/observation/ACTION-SPACE
        # redesign, not a further dose" — every closed class left
        # `env/walk_wz` pinned at the noise floor while ep_len_mean/
        # reward visibly rose (a pure RL discovery/credit-assignment
        # failure; `probe_turn_authority.py --policy scripted` clears
        # wz_med=+-0.098 rad/s on the IDENTICAL cfg/DR/plant, so the
        # turn is mechanically reachable, PPO's exploration just never
        # stumbles onto — or never gets credited for — the coordinated
        # 6-leg gait a scripted controller reaches trivially). None of
        # those 20 classes ever touched the RAW ACTION's own steering
        # symmetry: on a turn-in-place tick a fresh policy's near-zero
        # mean output has EQUAL probability of twisting the body either
        # way, so the EXPECTED net rotation is a coin flip uncorrelated
        # with the commanded sign — no persistent "lean this way"
        # signal for PPO's advantage estimator to climb on, unlike
        # hold/rise's own cured defect above (`joint_action_bias_*`)
        # where the zero action's CENTER was simply in the wrong place.
        # `goal.walk_turn_yaw_bias_deg` (default 0.0 = OFF, bit-exact
        # legacy) adds a small CONSTANT per-tick offset to every leg's
        # yaw-joint TARGET, ONLY on genuine turn-in-place ticks
        # (identical gating to `reward.walk_turn_kernel_neutral`/
        # `walk_turn_freeze_charge`: hypot(vx_ref,vy_ref)<=1e-3 and
        # abs(wz_ref)>1e-3), signed by sign(wz_ref) — information the
        # policy's own observation ALREADY carries (`_yaw_cmd` appends
        # wz_ref/WZ_SCALE to the obs tail), so this injects no NEW
        # task knowledge, only re-wires it as a symmetry-breaking DC
        # offset in JOINT-ANGLE space (applied in `_act_to_q` below,
        # after whichever of box/bias/legacy decode already ran, so
        # its physical size is the same few degrees regardless of
        # which action-space branch is active). It is a CONSTANT, not
        # a trajectory/schedule/gait: no time-varying phase, no
        # per-leg sequencing, no dependence on any demonstration/
        # teacher/scripted controller — the policy still owns 100% of
        # swing/stance TIMING and every other joint, exactly mirroring
        # the (already rl_only-accepted) hip/knee action-centering
        # fix's own numeric-calibration character. Flagged as an
        # explicit assume-and-go provenance judgment in
        # OPERATOR_QUESTIONS.md (command-conditioned, not static, so a
        # stricter reading is possible) — default OFF, isolated to
        # this one key, trivial to strike from any lineage if the
        # operator rules otherwise. See test_walk_turn_yaw_bias.py.
        self._turn_yaw_bias_deg = float(cfg_get(
            self.cfg, "goal", "walk_turn_yaw_bias_deg", default=0.0))
        # Action BOX (2026-08-30, operator literature ruling for the
        # walkcurr final wave — Smith/Kostrikov/Levine 2022 "Walk in
        # the Park" ablation: a TIGHT symmetric action box around the
        # standing stance is CRUCIAL for from-scratch discovery; Rudin
        # 2021 legged_gym likewise learns residuals around a standing
        # pose). Where the BIAS above only moves the a=0 point (slope
        # unchanged, full hardware range still reachable at |a|=1),
        # the BOX also shrinks the slope: with any
        # goal.joint_action_box_{yaw,hip,knee}_deg > 0, the mapping
        # becomes q = clip(stance_center + a * box_rad, axis_lo,
        # axis_hi), where stance_center is the bias-shifted a=0 pose
        # (the settled stance when the bias keys are set, the hardware
        # mid-range otherwise). A per-joint-class HALF-WIDTH in
        # degrees; a class left at 0 while the box is active is FROZEN
        # at its center (a deliberate search-space bound). All keys
        # default 0.0 = OFF = bit-exact legacy (_act_to_q falls
        # through to the bias/legacy path).
        box_deg = np.array([
            float(cfg_get(self.cfg, "goal", "joint_action_box_yaw_deg",
                          default=0.0)),
            float(cfg_get(self.cfg, "goal", "joint_action_box_hip_deg",
                          default=0.0)),
            float(cfg_get(self.cfg, "goal", "joint_action_box_knee_deg",
                          default=0.0)),
        ] * 6)
        self._joint_action_box_active = bool(np.any(box_deg > 0.0))
        if self._joint_action_box_active:
            self._joint_action_box_rad = np.maximum(box_deg, 0.0) * DEG2RAD
            self._joint_action_box_center = action_to_q_rad(
                self._joint_action_bias)
            self._joint_action_box_axis_lo = _CENTER_RAD - _HALF_RAD
            self._joint_action_box_axis_hi = _CENTER_RAD + _HALF_RAD
        # Cartesian FOOT-PLACEMENT action decode (2026-09-08, walkcurr
        # foot-placement mechanism — operator focus note 20260908T0403;
        # the named remaining structural lever after the slip-pricing
        # family, DR-band, torsional-friction and clip-controllability
        # closures). With any goal.walk_cart_foot_box_{x,y,z}_m > 0 the
        # SAME 18 actions are reinterpreted per leg as a Cartesian foot
        # target around the a=0 stance-foot point (identical to the
        # bias/box decode's a=0 pose) and turned into logical joint
        # targets by analytic per-leg IK derived from THIS env's loaded
        # model; SafetyLayer/servo/reward untouched. All keys default
        # 0.0 = OFF = bit-exact legacy (_act_to_q never enters the
        # branch). See rl_move/sim/cart_foot_decode.py.
        cart_box_m = np.array([
            float(cfg_get(self.cfg, "goal", "walk_cart_foot_box_x_m",
                          default=0.0)),
            float(cfg_get(self.cfg, "goal", "walk_cart_foot_box_y_m",
                          default=0.0)),
            float(cfg_get(self.cfg, "goal", "walk_cart_foot_box_z_m",
                          default=0.0)),
        ])
        self._cart_foot_active = bool(np.any(cart_box_m > 0.0))
        if self._cart_foot_active:
            from .cart_foot_decode import CartFootDecoder
            center_q = (self._joint_action_box_center
                        if self._joint_action_box_active
                        else action_to_q_rad(self._joint_action_bias))
            self._cart_foot = CartFootDecoder(
                self.model, center_q, cart_box_m)

    def _act_to_q(self, clipped: np.ndarray):
        if self._cart_foot_active:
            q = self._cart_foot.decode(np.asarray(clipped, dtype=float))
            # Cartesian foot-placement decode has no per-joint-axis
            # meaning for `clipped` (x/y/z per leg, not yaw/hip/knee),
            # so the turn-yaw-bias block below (joint-angle space) is
            # skipped for this branch — no live recipe combines them.
            return q, True, ""
        if self._joint_action_box_active:
            q = np.clip(
                self._joint_action_box_center
                + np.asarray(clipped, dtype=float)
                * self._joint_action_box_rad,
                self._joint_action_box_axis_lo,
                self._joint_action_box_axis_hi)
        else:
            if self._joint_action_bias_active:
                clipped = np.clip(clipped + self._joint_action_bias,
                                   -1.0, 1.0)
            q = action_to_q_rad(clipped)
        if self._turn_yaw_bias_deg > 0.0 and getattr(self, "_yaw_cmd",
                                                       False):
            goal = self._current_goal()
            if goal is not None:
                vx = float(getattr(goal, "vx_ref", 0.0))
                vy = float(getattr(goal, "vy_ref", 0.0))
                wz = float(getattr(goal, "wz_ref", 0.0))
                if np.hypot(vx, vy) <= 1e-3 and abs(wz) > 1e-3:
                    sign = 1.0 if wz > 0.0 else -1.0
                    delta = sign * self._turn_yaw_bias_deg * DEG2RAD
                    q = np.asarray(q, dtype=float).copy()
                    q[0::3] = np.clip(
                        q[0::3] + delta,
                        _CENTER_RAD[0::3] - _HALF_RAD[0::3],
                        _CENTER_RAD[0::3] + _HALF_RAD[0::3])
        return q, True, ""
