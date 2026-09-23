"""SimHexapodBalanceEnv — MuJoCo twin of the hardware ``HexapodBalanceEnv``.

Same 47-dim observation, 6-dim body-offset action, reward terms, safety
layer and fixed-foot body IK as the real env — only the "robot" is a
MuJoCo model driven through the fitted ``ServoProfile`` (latency +
profile speed + deadband) so a policy trained here sees hardware-like
actuation, not ideal position control.

Usage
-----
    from rl_move.sim.sim_env import SimHexapodBalanceEnv
    env = SimHexapodBalanceEnv(randomize=True, seed=0)
    obs, info = env.reset()
    obs, r, term, trunc, info = env.step(env.action_space.sample())
"""
from __future__ import annotations

import math
import time
from pathlib import Path
from typing import Any

import numpy as np

from hexapod_core.joint_frame import (
    joint_index, mujoco_rel_rad_to_robot_abs_rad,
    robot_abs_rad_to_mujoco_rel_rad,
)

_RL = Path(__file__).resolve().parents[1]
_PROTO = _RL.parent
_LINUX = _PROTO / "linux_control"

from rl_move.body_ik import FixedFootBodyIK, N_ACT, fk_all_feet
from rl_move.config import cfg_get, load_config
from rl_move.env import (build_obs, compute_reward, current_sense_obs_dim,
                          height_err_sense_obs_dim,
                          height_vel_sense_obs_dim, start_kind_of)
from rl_move.robot_state import (
    DEG2RAD, N_JOINTS, RAD2DEG, RobotState, over_current_reading,
)
from rl_move.safety import SafetyLayer, action_to_body_offset

from .domain_rand import (DomainRandomizer, EpisodeRandomization,
                           JointBacklash, stickslip_friction_mult)
from .deployed_transport import DeployedTransport
from .servo_model import (
    ServoProfile, SimServoParams, apply_params_to_model, build_model,
    joint_qpos_addrs, joint_qvel_addrs, lowest_collidable_z,
    position_actuator_ids, resolve_model_source,
)
from .struct_compliance import StructCompliance
from .leg_mount_flex import (
    addresses as leg_mount_flex_addresses,
    diagnostics as leg_mount_flex_diagnostics,
    from_cfg as leg_mount_flex_from_cfg,
)
from .joint_series_flex import (
    addresses as joint_series_flex_addresses,
    diagnostics as joint_series_flex_diagnostics,
    from_cfg as joint_series_flex_from_cfg,
)
from .command_indicator import draw_env_command_indicator
from .balance_helpers import (
    PLANT_SPEC, _load_robot_abs_q_npz, load_rise_ref, valid_plant,
)
from .balance_reset import (
    reset_gravity_ease, reset_mode_seq_and_goal, spawn_pose_q_start,
)
from .balance_reward_hold import (
    hold_minload_shortfall_reward, hold_still_gate_reward,
    transition_foot_drag_metric,
)
from .balance_terminations import (
    collapse_terminations, hold_minload_termination,
    terminal_settlement_reward, walk_idle_and_leg_duty_terminations,
)
from .balance_reward_posture import (
    end_posture_reward, posture_support_load_headroom_reward,
    stance_shaping_reward,
)
from .balance_reward_current import (
    current_penalties,
)
from .balance_reward_rise import (
    rise_curl_only_pretrain_reward, rise_curl_reward, rise_ref_track_reward,
    rise_scored_steps_reward,
)
from .balance_bc_anchor import (
    bc_anchor_target,
)

G0 = 9.80665
N_OBS = 47

# Transient per-leg foot-catch/stumble event (dr.foot_catch_force_n,
# see domain_rand.RandRanges + sim_env._update_foot_catch_state/
# _advance). Fixed physical constants, not swept doses -- only the
# peak force magnitude is a dr.* range.
FOOT_CATCH_LOAD_ON_N = 0.05     # touch reading counted as "planted"
FOOT_CATCH_DURATION_S = 0.12    # how long one triggered yank lasts
FOOT_CATCH_COOLDOWN_S = 0.30    # min gap between triggers on one leg
FOOT_CATCH_DOWN_FRAC = 0.5      # vertical component / horizontal peak


try:  # gymnasium is optional for pure scripted use
    import gymnasium as _gym
    _GymBase = _gym.Env
except Exception:  # pragma: no cover
    _gym = None
    _GymBase = object


def soften_contacts(model) -> None:
    """3x-softer foot/pad/belly solref (see the __init__ comment).

    Module-level so the batched MJX vec env can prepare its SHARED model
    with exactly the same contact softening the C env applies.
    """
    import mujoco
    for i in range(6):
        for gname in (f"L{i}_foot", f"L{i}_pad_col",
                      f"L{i}_yaw_servo_col"):
            fid = mujoco.mj_name2id(
                model, mujoco.mjtObj.mjOBJ_GEOM, gname)
            if fid >= 0:
                model.geom_solref[fid, 0] *= 3.0


def set_foot_ground_friction(model, mu_slide: float) -> None:
    """Set the foot–ground SLIDE friction to a calibrated value.

    cfg ``env.foot_friction_slide`` (0 = keep the XML default, foot
    μ=2.0 / floor μ=1.5 → pair μ=2.0). MuJoCo combines a contact
    pair's friction as the element-wise MAX of the two geoms, so the
    floor/terrain AND the foot/pad geoms must all move together —
    changing only the feet would leave the pair pinned at the floor's
    1.5. Calibrate with ``rl_move/sim/calibrate_slip.py`` against the
    tape-measured travel ratio (0.50–0.51, hardware_traces/
    tape_20260810_summary.json). DR's ``friction_scale`` still
    multiplies around this recentered value. Module-level so the MJX
    shared-model prep applies the identical mutation."""
    import mujoco
    names = ["floor", "terrain"]
    for i in range(6):
        names += [f"L{i}_foot", f"L{i}_pad_col"]
    for gname in names:
        gid = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_GEOM, gname)
        if gid >= 0:
            model.geom_friction[gid, 0] = float(mu_slide)


def set_foot_geom_radius(model, radius_m: float) -> None:
    """Reject unsafe in-place resizing of a compiled model.

    ``geom_size`` alone leaves MuJoCo's collision bounds/BVH stale.
    Use ``build_model(foot_geom_radius_m=...)`` or the private env cfg
    instead; those compile the contact geometry before creating MjData.
    Zero remains a no-op. Friction coefficients and body inertia remain
    unchanged by the supported construction path. Rolling coefficients
    already have length units, with no extra sphere-radius multiplier.
    """
    radius = float(radius_m)
    if not np.isfinite(radius) or radius < 0.0:
        raise ValueError("env.foot_geom_radius_m must be finite and >= 0")
    if radius != 0.0:
        raise ValueError("cannot resize a compiled model; use "
                         "build_model(foot_geom_radius_m=...) before MjData")


def leg_chassis_collision_from_cfg(cfg) -> bool:
    """cfg ``env.leg_chassis_collision`` (0 = off, the default) — the
    belly knife-edge contact axis (SIM.md known-gap 4, added 08-12).
    The masks must be rewritten in the XML BEFORE compile (MuJoCo
    precomputes the collidable pair set; runtime contype/conaffinity
    edits never register — verified 08-12 on 3.11), so this is a
    ``build_model(leg_chassis_collision=...)`` kwarg, not a model
    mutation. See servo_model.build_model for the bit plan."""
    if cfg is None:
        from rl_move.config import load_config
        cfg = load_config()
    return bool(int(cfg_get(cfg, "env", "leg_chassis_collision",
                            default=0)))


def _default_plant_deg() -> np.ndarray:
    """Canonical robot plant in the repository joint contract (robot_abs).

    2026-09-02 regression fix: the pre-2026-08-31 sim canonical stance was
    hip=20/knee=80 in MuJoCo's femur-RELATIVE knee convention (the value
    ``sim_gait_compat`` used to hand back after converting from this
    module's absolute-tibia hardware frame). The b7e7ea05 "unify joint
    coordinates" merge switched every internal TripodGait consumer in
    this file from the ``sim_gait_compat``-wrapped gait to the raw
    ``hexapod_core.tripod_gait`` (absolute-tibia) gait AND made this
    default plant a directly-robot_abs value, but kept the OLD numeric
    literal (80) instead of its robot_abs equivalent -- silently
    RELABELING a mujoco-relative number as an absolute-tibia one without
    converting it. knee_abs = knee_rel + hip = 80 + 20 = 100 is the
    value that reproduces the ORIGINAL physical stance
    (``_robot_abs_to_mujoco_rel`` only shifts the knee by hip, so
    robot_abs (20, 100) <-> mujoco_rel (20, 80), unchanged geometry).
    Measured regression before this fix (mesh/100Hz, `walk` mode,
    static-hold "park" episode, 8s/800 ticks): chassis height drifts
    +82mm above the reset-settled height (height_err_mm 0 -> 82,
    reward_height -436, reward_loadslip_excess -160, reward_drag -3,
    reward_current -80, total park reward -1168 vs the historical +90).
    After this fix (same probe): height_err_mm stays ~13mm, loadslip/drag
    go to 0, reward_current -3, total park reward +89 -- matches the
    pre-merge band. See OPERATOR_QUESTIONS.md 2026-09-02 ~23:xx and
    rl_docs/tracks/standwalk/STATUS.md for the full derivation
    (`test_course_income_semantics.py`'s 7 failures this unblocks).
    """
    try:
        from feetech_bus import load_plant_pose
        if load_plant_pose().get("learned"):
            from feetech_bus import standing_pose_degrees
            return np.asarray(standing_pose_degrees(), dtype=float)
    except Exception:
        pass
    return np.asarray([0.0, 20.0, 100.0] * 6, dtype=float)


class SimHexapodBalanceEnv(_GymBase):
    """Gymnasium env; obs/action/reward identical to the hardware env."""

    metadata = {"render_modes": ["rgb_array"]}
    # Extra per-episode attributes a task subclass needs included in the
    # batched MJX vec env's pooled reset-state snapshots (see
    # mjx_vec_env.py). Base env: none.
    MJX_SNAPSHOT_EXTRA: tuple = ()
    # Sliding friction during the reset slip-settle (see reset()): low
    # enough to relieve tangential preload from placement/geometry error,
    # high enough that the plant stance doesn't splay outward under load.
    SLIP_MU = 0.15

    def __init__(self, cfg: dict | None = None, *,
                 params: SimServoParams | None = None,
                 randomize: bool = False,
                 randomizer: DomainRandomizer | None = None,
                 dr_scale: float = 1.0,
                 plant_deg: np.ndarray | list[float] | None = None,
                 episode_seconds: float | None = None,
                 seed: int | None = None,
                 render_mode: str | None = None,
                 mesh_visuals: bool = True,
                 model=None):
        import mujoco
        self._mujoco = mujoco
        self.cfg = cfg if cfg is not None else load_config()
        self._leg_mount_flex = leg_mount_flex_from_cfg(self.cfg)
        self._joint_series_flex = joint_series_flex_from_cfg(self.cfg)
        self._struct_comp = StructCompliance.from_cfg(self.cfg)
        compliance_models = [
            name for name, enabled in (
                ("struct_comp", self._struct_comp is not None),
                ("leg_mount_flex", self._leg_mount_flex is not None),
                ("joint_series_flex", self._joint_series_flex is not None),
            ) if enabled
        ]
        if len(compliance_models) > 1:
            raise ValueError(
                f"{', '.join(compliance_models)} cannot both be enabled: "
                "the compliance models are mutually exclusive to avoid "
                "double-counting an uncalibrated effect")
        # bus.servo_params selects the fitted actuator set ("" = air fit,
        # "loaded" = 08-10 loaded bench fit); explicit params win.
        self.params = (params if params is not None
                       else SimServoParams.from_cfg(self.cfg))
        self.render_mode = render_mode
        self.rng = np.random.default_rng(seed)

        # In-run coefficient scheduler (2026-08-13, nobc gait line —
        # GAIT.md P3 lever 2 "annealed-up charge", the last unbuilt
        # lever after every fixed-coefficient / warm-start form closed).
        # Linearly ramps ONE cfg coefficient DURING a training run, by
        # GLOBAL env steps. Default OFF (sched.key unset) = bit-exact
        # legacy behavior: nothing is tracked, no cfg value is written.
        #   sched.key       dotted cfg path to drive, e.g.
        #                   "reward.k_drag_stance"
        #   sched.v0 / v1   value before t0 / after t1 (linear between)
        #   sched.t0_steps / t1_steps   GLOBAL env-step boundaries
        #   sched.n_envs    total parallel envs in the run — each env
        #                   converts its own tick count to global steps
        #                   as ticks * n_envs (exact for the synchronous
        #                   vec envs, which step every env every batch
        #                   tick). REQUIRED — no silent default, a
        #                   mis-clocked schedule is worse than a crash.
        # The clock is a per-process monotone tick counter. It is NOT
        # in mjx_host.SNAP_ATTRS on purpose: episode pool-restores must
        # never rewind it (the commit-65edba7 bug class). It restarts
        # at 0 on resume-from-checkpoint — scheduled runs should be
        # fresh single-process runs, note it in the spec. Eval-harness
        # envs built from the same cfg sit at tick ~0 and so read ~v0
        # for the scheduled key: judge scheduled runs on measured
        # behavior metrics (slip/gait/travel), not eval reward panels.
        self._sched_key = str(cfg_get(self.cfg, "sched", "key",
                                      default="") or "")
        self._sched_ticks = 0
        self._sched_value: float | None = None
        if self._sched_key:
            self._sched_path = tuple(self._sched_key.split("."))
            if len(self._sched_path) < 2:
                raise ValueError(
                    "sched.key must be a dotted cfg path "
                    f"(section.leaf), got {self._sched_key!r}")

            def _sched_req(leaf: str) -> float:
                v = cfg_get(self.cfg, "sched", leaf, default=None)
                if v is None:
                    raise ValueError(
                        f"sched.key is set but sched.{leaf} is missing "
                        "— the scheduler has no silent defaults")
                return float(v)

            self._sched_v0 = _sched_req("v0")
            self._sched_v1 = _sched_req("v1")
            self._sched_t0 = _sched_req("t0_steps")
            self._sched_t1 = _sched_req("t1_steps")
            self._sched_n = _sched_req("n_envs")
            if not (self._sched_t1 > self._sched_t0 >= 0.0):
                raise ValueError(
                    "sched requires t1_steps > t0_steps >= 0")
            if self._sched_n < 1.0:
                raise ValueError("sched.n_envs must be >= 1")

        # Physics easing (2026-08-13, GAIT.md P3 lever 3, nobc track):
        # ease.gravity_scale multiplies THIS EPISODE's gravity
        # magnitude. It is read from cfg at EVERY reset (see
        # _reset_begin) so the sched.* engine above — which writes its
        # target cfg path each tick — can anneal it across a run (eased
        # physics early, nominal by the end); within an episode physics
        # never changes.
        # Default (key unset / 1.0) is bit-exact legacy: no draw, no
        # mutation, no extra code path. Application point is the
        # episode's DR draw (_ep_rand) — the one object BOTH trainer
        # stacks consume (private model: EpisodeRand.apply_to_model;
        # batched MJX: ModelDrScratch.rows_for + tp_rows) — so easing
        # composes with DR (slope direction kept, |g| scaled) with NO
        # DomainRandomizer or per-world plumbing changes. This field
        # holds the randomize=False PRIVATE-model fallback used by
        # reset(); shared-model shims without DR raise instead
        # (per-world model fields are the only route to eased gravity
        # in the batched path).
        self._ease_g = 1.0

        # Temporal actor (plan §Architecture): obs.history_frames > 1
        # stacks the last K single-tick observations NEWEST-FIRST, so a
        # parent trained on width W transplants via --obs-pad-transplant
        # (its weights read frame 0 = the current tick; frames 1..K-1
        # start as zero columns). History is built ENV-SIDE so trainer,
        # eval harness, and the hardware bridge see the identical obs.
        self._hist_n = max(1, int(cfg_get(self.cfg, "obs",
                                          "history_frames", default=1)))
        self._hist_buf: list | None = None

        self.dt = 1.0 / float(cfg_get(self.cfg, "control", "hz", default=25))
        # Gyro-trust of the inline complementary attitude filter that
        # produces the training obs' roll/pitch "the way the hardware
        # computes it". Config-driven (sensing.attitude_alpha) so training
        # can reject the fore-aft surge accel; default 0.98 is bit-exact
        # with the pre-2026-09-20 hardcoded value. Same knob RobotState-
        # Estimator reads on hardware.
        self._attitude_alpha = float(
            cfg_get(self.cfg, "sensing", "attitude_alpha", default=0.98))
        self._deployed_transport = DeployedTransport.from_cfg(
            self.cfg, 1.0 / self.dt)
        ep_s = (episode_seconds if episode_seconds is not None
                else float(cfg_get(self.cfg, "episode", "seconds", default=5)))
        self.episode_steps = int(round(ep_s / self.dt))
        self.write_speed_deg_s = (
            float(cfg_get(self.cfg, "bus", "write_speed", default=400))
            * 360.0 / 4096.0)
        self.write_acc_units = float(
            cfg_get(self.cfg, "bus", "write_acc", default=20))

        # Servo current ESTIMATE model (see _read_state). Default "power":
        # the validated mechanical-power model (fitted 2026-09-19,
        # /tmp/gaitval) iq/18 + k*|torque*qvel|. Legacy "torque_proxy":
        # the pre-2026-09-19 min(|torque|*1.2, 3.0) rail image.
        self._current_model = str(cfg_get(
            self.cfg, "bus", "current_model", default="power")).lower()
        if self._current_model not in ("power", "torque_proxy"):
            raise ValueError(
                f"bus.current_model must be 'power' or 'torque_proxy', "
                f"got {self._current_model!r}")
        _iq_bus_a = float(cfg_get(
            self.cfg, "bus", "current_iq_bus_a", default=0.19))
        self._current_iq_joint = _iq_bus_a / N_JOINTS
        self._current_k_a_per_w = float(cfg_get(
            self.cfg, "bus", "current_k_a_per_w", default=0.02282))
        # Winding / load-stall current term (2026-09-21 reality-gap refit,
        # claude/sim-refit): the pure mechanical-power model reads ~0 A at a
        # stall (high torque, ~0 speed) and under-predicted this robot's
        # combo-walk mechanical current ~4x (real 0.32 vs sim 0.08 A bus
        # above idle) — the deficit sits on the load-bearing hip/knee that
        # ride the 2.2 N·m torque rail. STS3215 winding current flows
        # ~proportional to motor torque ABOVE the non-backdrivable gearbox's
        # free-hold capacity, so we add k_stall*relu(|torque|-thr):
        #   - thr keeps gentle holds/stance AND the validated scripted-gait
        #     fit (test_current_model.test_constants_reproduce_the_fit,
        #     /tmp/gaitval gaits 1-4/7/10) untouched — their |torque| rarely
        #     exceeds thr, so the term stays ~0 there and k_a_per_w is
        #     unchanged (0.02282);
        #   - it does NOT feed the over-current TRIP (that still rides the
        #     separate torque-proxy over_current_signal below), so a stall
        #     trips exactly as before.
        # Default 0.0 = OFF (bit-exact power model); config.yaml ships the
        # fitted 0.042 A/N·m @ 1.2 N·m.
        self._current_k_stall_a_per_nm = float(cfg_get(
            self.cfg, "bus", "current_k_stall_a_per_nm", default=0.0))
        self._current_stall_thr_nm = float(cfg_get(
            self.cfg, "bus", "current_stall_thr_nm", default=1.2))

        # Servo-profile RAMP-IN (2026-08-20, fast anti-skate option (b),
        # q_20260820T0830Z: the bcgait1_hard1 transplant dies zero-shot
        # under the raised 1500/80 profile at the V5 B0 precert, dose-
        # graded — the PROFILE DOSE itself destabilizes the walker
        # before any curriculum/penalty engages). When armed, the
        # TRAINER anneals the commanded write profile from a gentle
        # start (default = the fitted regime: 350 counts/s effective
        # cruise, acc 20, 1.5 deg/tick slew) to the cfg TARGET
        # (bus.write_speed / bus.write_acc / safety.max_delta_q_deg)
        # linearly over ``bus.profile_ramp_steps`` GLOBAL env steps.
        #   - Default (key absent/0) = OFF: no state, no new code path,
        #     bit-exact legacy behavior.
        #   - Armed but never applied = TARGET profile: construction
        #     never moves the dials, so eval_checkpoint / play / the
        #     periodic C-env evals judge checkpoints at the FULL dose
        #     even when the training cfg carries ramp keys. Only an
        #     explicit apply_profile_ramp_frac() call (train_ppo_mjx:
        #     frac 0 before the pre-PPO cert, then per rollout) moves
        #     the profile below target.
        #   - Fail-closed: a ramp whose target write_speed exceeds the
        #     resolved actuator velocity ceiling would be silently
        #     clamped (the exact silent-no-op class the 08-19
        #     servo_vel_max_counts_s override exists for) — raise at
        #     construction instead.
        self._profile_ramp: dict | None = None
        self._profile_ramp_dq_rad: float | None = None
        _ramp_steps = int(float(cfg_get(
            self.cfg, "bus", "profile_ramp_steps", default=0) or 0))
        if _ramp_steps > 0:
            _r_start_ws = float(cfg_get(
                self.cfg, "bus", "profile_ramp_start_write_speed",
                default=350.0))
            _r_start_acc = float(cfg_get(
                self.cfg, "bus", "profile_ramp_start_write_acc",
                default=20.0))
            _r_start_dq = float(cfg_get(
                self.cfg, "bus", "profile_ramp_start_max_delta_q_deg",
                default=1.5))
            _r_tgt_ws = float(cfg_get(self.cfg, "bus", "write_speed",
                                      default=400))
            _r_tgt_acc = float(cfg_get(self.cfg, "bus", "write_acc",
                                       default=20))
            _r_tgt_dq = float(cfg_get(self.cfg, "safety",
                                      "max_delta_q_deg", default=2.0))
            if min(_r_start_ws, _r_start_acc, _r_start_dq) <= 0.0:
                raise ValueError(
                    "bus.profile_ramp_start_* must all be > 0 (got "
                    f"write_speed={_r_start_ws}, acc={_r_start_acc}, "
                    f"max_delta_q_deg={_r_start_dq})")
            _ceil_counts = (float(self.params.per_joint(
                "vel_max_deg_s").min()) * 4096.0 / 360.0)
            if _r_tgt_ws > _ceil_counts + 1e-6:
                raise ValueError(
                    f"bus.profile_ramp_steps={_ramp_steps} targets "
                    f"write_speed={_r_tgt_ws:g} counts/s but the "
                    "resolved actuator velocity ceiling is "
                    f"{_ceil_counts:.0f} counts/s — the ramp would be "
                    "silently clamped; set bus.servo_vel_max_counts_s "
                    "(e.g. 'write_speed') so the profile ceiling "
                    "matches the target dose")
            self._profile_ramp = {
                "steps": _ramp_steps, "frac": 1.0,
                "start": (_r_start_ws, _r_start_acc, _r_start_dq),
                "target": (_r_tgt_ws, _r_tgt_acc, _r_tgt_dq),
            }

        # ``model``: a pre-built, fully PREPARED (contact-softened) MjModel
        # shared with other envs — the batched MJX vec env owns physics
        # and passes one model to all its per-env shims. A shared model
        # must never be mutated per episode, so the shim path runs with
        # model DR disabled. Default (None): private model, as always.
        self._owns_model = model is None
        _r_foot = float(cfg_get(self.cfg, "env", "foot_geom_radius_m",
                                default=0.0))
        if not np.isfinite(_r_foot) or _r_foot < 0.0:
            raise ValueError("env.foot_geom_radius_m must be finite and >= 0")
        if model is not None and _r_foot != 0.0:
            # Shared host prep must compile the radius before put_model and
            # shim construction. Never resize a shared model here. Reject
            # an old size-only prep rather than silently mixing physics.
            gids = [mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_GEOM, name)
                    for i in range(6) for name in (f"L{i}_foot", f"L{i}_pad_col")]
            gids = [gid for gid in gids if gid >= 0]
            if (not gids
                    or np.any(model.geom_type[gids] != mujoco.mjtGeom.mjGEOM_SPHERE)
                    or np.any(model.geom_size[gids, 0] != _r_foot)
                    or np.any(model.geom_rbound[gids] != _r_foot)
                    or np.any(model.geom_aabb[gids, 3:] != _r_foot)):
                raise ValueError("shared foot radius must be compiled with "
                                 "build_model(foot_geom_radius_m=...) before shims")
        # cfg env.model_source: mesh-family (corrected kinematics) or the
        # legacy primitive model — see servo_model.resolve_model_source.
        # Shared models arrive pre-built from the same cfg, so the resolved
        # source still describes them.
        self._model_source = resolve_model_source(self.cfg)
        if model is not None:
            # dr.walk_push_*: private-model envs apply the xfrc in
            # their own _advance loop; shared-model shims delegate to
            # the MJX stepper, whose tick takes the per-env push_nm
            # (the vec envs read _walk_push_torque_nm() per tick and
            # hand it over — plumbed 08-12 in mjx_backend/mjx_vec_env/
            # mjx_sharded_vec_env).
            self.model = model
        else:
            # Rough terrain (cfg env.terrain_amp > 0) reaches the private
            # C-env model here, so eval-harness / local-viewer episodes run
            # on the same ground the batched trainer used.
            _t_amp = float(cfg_get(self.cfg, "env", "terrain_amp",
                                   default=0.0))
            _t_seed = int(cfg_get(self.cfg, "env", "terrain_seed",
                                  default=0))
            self.model = build_model(
                fixed_base=False,
                flat_terrain=_t_amp <= 0.0,
                terrain_amp=_t_amp,
                terrain_seed=_t_seed,
                mesh_visuals=mesh_visuals,
                leg_chassis_collision=leg_chassis_collision_from_cfg(
                    self.cfg),
                source=self._model_source, foot_geom_radius_m=_r_foot,
                leg_mount_flex=self._leg_mount_flex,
                joint_series_flex=self._joint_series_flex)
        self.data = mujoco.MjData(self.model)
        self._substeps = max(1, int(round(self.dt / self.model.opt.timestep)))
        self._qadr = joint_qpos_addrs(self.model)
        self._vadr = joint_qvel_addrs(self.model)
        self._pos_act = position_actuator_ids(self.model)
        self._leg_mount_flex_addrs = leg_mount_flex_addresses(
            self.model, required=False)
        if ((self._leg_mount_flex is None)
                != (self._leg_mount_flex_addrs is None)):
            raise ValueError(
                "shared model leg-mount-flex topology does not match cfg")
        self._joint_series_flex_addrs = joint_series_flex_addresses(
            self.model, expected=self._joint_series_flex,
            required=False)
        if ((self._joint_series_flex is None)
                != (self._joint_series_flex_addrs is None)):
            raise ValueError(
                "shared model joint-series-flex topology does not match cfg")
        self._struct_comp_k: np.ndarray | None = None
        self._chassis_bid = mujoco.mj_name2id(
            self.model, mujoco.mjtObj.mjOBJ_BODY, "chassis")
        gid = mujoco.mj_name2id(
            self.model, mujoco.mjtObj.mjOBJ_SENSOR, "chassis_gyro")
        self._gyro_adr = self.model.sensor_adr[gid]
        # Foot touch sensors — the unload task's ground-truth leg load.
        self._touch_adr = []
        for i in range(6):
            sid = mujoco.mj_name2id(
                self.model, mujoco.mjtObj.mjOBJ_SENSOR, f"L{i}_foot_t")
            self._touch_adr.append(
                self.model.sensor_adr[sid] if sid >= 0 else -1)
        # Foot pad bodies + per-episode grounded-z reference, for the
        # stance-clearance penalty (see step()).
        self._pad_bids = [mujoco.mj_name2id(
            self.model, mujoco.mjtObj.mjOBJ_BODY, f"L{i}_pad")
            for i in range(6)]
        self._pad_z_ref: np.ndarray | None = None
        self._end_posture_from: int | None = None
        # Foot geoms + sites (constant across the model's lifetime) —
        # per-tick stick-slip friction modulation (dr.foot_stickslip_gain,
        # see domain_rand.stickslip_friction_mult / sim_env's
        # _apply_foot_stickslip). Both families define these names (see
        # mujoco_prototype.py / mesh_mujoco XML), so this is never -1 in
        # practice; guarded at use-site anyway (fail loud, not silent).
        self._stickslip_foot_gids = [mujoco.mj_name2id(
            self.model, mujoco.mjtObj.mjOBJ_GEOM, f"L{i}_foot")
            for i in range(6)]
        self._stickslip_foot_sids = [mujoco.mj_name2id(
            self.model, mujoco.mjtObj.mjOBJ_SITE, f"L{i}_foot_site")
            for i in range(6)]
        self._stickslip_gain = np.zeros(6, dtype=float)
        self._stickslip_vel_ref_mps = 0.02
        self._stickslip_base_mu = np.zeros(6, dtype=float)
        self._stickslip_prev_xy: np.ndarray | None = None
        self._stickslip_active = False

        # Transient per-leg foot-catch/stumble event (dr.foot_catch_
        # force_n / -group, see domain_rand.EpisodeRandomization and
        # sim_env._update_foot_catch_state / _advance). Reuses
        # ``_touch_adr`` and ``_pad_bids`` (both defined above) -- no
        # new geom/sensor lookups needed.
        self._foot_catch_owns_row = False
        self._foot_catch_prev_touch = np.ones(6, dtype=bool)
        self._foot_catch_end_s = np.full(6, -1.0, dtype=float)
        self._foot_catch_cooldown_until_s = np.zeros(6, dtype=float)

        # Soften the foot contacts: the CAD model's solref (0.01 s) is
        # near-rigid, so mm-scale randomized leg-length differences make
        # 2-3 "long" legs carry the whole robot (three-legged-stool) and
        # the stiff servos read 2-3 A standing still. Real rubber feet +
        # PLA leg flex compress ~1-2 mm and spread the load; ~3x softer
        # timeconst gives that. DR's contact_stiff_scale still varies it.
        # (A shared model arrives already softened — soften ONCE, or
        # every env would multiply solref by another 3x.)
        if self._owns_model:
            soften_contacts(self.model)
            # Calibrated foot–ground slide μ (0 = XML default). Applied
            # BEFORE the pristine copies so DR restores + rescales around
            # the calibrated value. Shared models arrive already prepared.
            _mu = float(cfg_get(self.cfg, "env", "foot_friction_slide",
                                default=0.0))
            if _mu > 0.0:
                set_foot_ground_friction(self.model, _mu)

        # Pristine copies for DR restore at every reset.
        self._base_body_mass = self.model.body_mass.copy()
        self._base_body_inertia = self.model.body_inertia.copy()
        self._base_body_ipos = self.model.body_ipos.copy()
        self._base_body_pos = self.model.body_pos.copy()
        self._base_geom_pos = self.model.geom_pos.copy()
        self._base_site_pos = self.model.site_pos.copy()
        self._base_geom_friction = self.model.geom_friction.copy()
        self._base_geom_solref = self.model.geom_solref.copy()
        self._base_gravity = self.model.opt.gravity.copy()

        if randomizer is not None:
            self.randomizer = randomizer
        elif randomize:
            self.randomizer = DomainRandomizer.from_params(
                self.params, scale=dr_scale)
        else:
            self.randomizer = None
        # cfg-driven DR range overrides: --cfg-set dr.<field>=v or "lo,hi".
        # ABSOLUTE values applied AFTER dr_scale scaling (an override is the
        # experiment's exact range, e.g. payload dr.mass_scale=1.0,1.5).
        # Unknown fields raise — a typo must fail the launch, not silently
        # train the default DR. Covers CPU and MJX stacks (the MJX host
        # applies this env's _ep_rand per world).
        if self.randomizer is not None:
            for _k, _v in (self.cfg.get("dr") or {}).items():
                if not hasattr(self.randomizer.ranges, _k):
                    raise ValueError(f"unknown DR override dr.{_k}")
                if isinstance(_v, str):
                    # String-typed fields (e.g. dr.joint_backlash_group)
                    # are a categorical name, not a "lo,hi" magnitude
                    # range -- pass through unparsed. Detected off the
                    # field's OWN current (default) value, so this never
                    # changes behavior for any pre-existing numeric
                    # override.
                    if not isinstance(
                            getattr(self.randomizer.ranges, _k), str):
                        _parts = tuple(float(x) for x in _v.split(","))
                        _v = _parts[0] if len(_parts) == 1 else _parts
                setattr(self.randomizer.ranges, _k, _v)
        # DR-STAGE RAMP (2026-09-08, staged-DR-breadth fresh-acquisition
        # design): env.dr_stage_ramp_steps > 0 arms a trainer-driven
        # curriculum that moves the EPISODE-RESET DR distribution from
        # the calibrated nominal sim (frac 0 — sensor-noise floors kept,
        # RandRanges.scaled semantics: probabilities ramp, per-event
        # doses do not) up to this run's FULL post-override ranges
        # (frac 1). Why it must exist: the --cfg-set dr.* overrides
        # above are ABSOLUTE, applied AFTER --dr-scale scaling, so
        # neither --dr-scale nor the walkcurr bucket ladder (which
        # re-applies the same absolute overrides per bucket) can ramp a
        # recipe that carries its DR matrix as explicit overrides.
        #   - Default (key absent/0) = OFF: no state, no new code path,
        #     bit-exact legacy behavior.
        #   - Armed but never applied = FULL ranges: construction never
        #     touches the randomizer, so eval_checkpoint / play / the
        #     periodic C-env evals judge checkpoints at the run's full
        #     DR even when the training cfg carries the ramp key. Only
        #     an explicit apply_dr_stage_frac() broadcast
        #     (train_ppo_mjx, per rollout) moves the resets below full.
        #   - Fail-closed: incompatible with goal.walk_curriculum (the
        #     bucket ladder rebuilds the randomizer per episode and owns
        #     the DR schedule) and with randomize=False (nothing to
        #     stage) — raise at construction, never silently no-op.
        self._dr_stage_full = None
        self._dr_stage_cache: dict = {}
        self._dr_stage_frac: float | None = None
        _drs_steps = int(float(cfg_get(
            self.cfg, "env", "dr_stage_ramp_steps", default=0) or 0))
        if _drs_steps > 0:
            if self.randomizer is None:
                raise ValueError(
                    "env.dr_stage_ramp_steps > 0 needs an active "
                    "DomainRandomizer (randomize=True); with DR off "
                    "there is nothing to stage")
            if float(cfg_get(self.cfg, "goal", "walk_curriculum",
                             default=0) or 0) > 0:
                raise ValueError(
                    "env.dr_stage_ramp_steps is incompatible with "
                    "goal.walk_curriculum — the bucket ladder rebuilds "
                    "the randomizer per episode and owns the DR "
                    "schedule; use the bucket dr fields instead")
            self._dr_stage_full = self.randomizer.ranges
        self._ep_rand: EpisodeRandomization | None = None
        self._reset_start_offset_rad: np.ndarray | None = None
        self._reset_start_bad_joints: list[int] = []

        self._plant_deg = (np.asarray(plant_deg, dtype=float).reshape(N_JOINTS)
                           if plant_deg is not None else _default_plant_deg())

        self.ik = FixedFootBodyIK(cfg=self.cfg)
        self.safety = SafetyLayer(self.cfg)
        if self._deployed_transport is not None:
            # Async hardware current dwell consumes physical frames, not
            # all repeated policy reads of a cached health value.
            trip_s = float(cfg_get(self.cfg, "safety",
                                   "over_current_trip_s", default=.8))
            self.safety._over_current_trip_ticks = max(
                1, int(round(trip_s * self._deployed_transport.snapshot.hz)))
        # Subclasses with a different action space (e.g. raw joint targets)
        # override n_act and _act_to_q; everything else is shared.
        self.n_act = N_ACT
        self._q_nom = np.zeros(N_JOINTS, dtype=float)
        self._prev_action = np.zeros(self.n_act, dtype=float)
        # Action two ticks ago, for the optional Δ²action smoothness term
        # (reward.k_action_accel). Unused unless that knob is on.
        self._prev_prev_action = np.zeros(self.n_act, dtype=float)
        self._cmd = np.zeros(N_JOINTS, dtype=float)
        self._profile: ServoProfile | None = None
        self._backlash: JointBacklash | None = None
        self._backlash_prev_force = np.zeros(N_JOINTS, dtype=float)
        self._step_i = 0
        self._episode = 0
        self._state: RobotState | None = None
        self._renderer = None
        self._goal_traj = None            # set by goal-conditioned subclass
        # Mode-sequencing state (goal.mode_seq) — populated per episode
        # in _reset_begin/_sample_mode_seq; None = feature off.
        self._seq_plan = None
        self._seq_idx = 0
        self._seq_stand_z = None
        self._seq_seg_end = None
        self._seq_pose_anchor = None
        self._seg_entry_step = 0
        # Canonical per-family segment frames (goal.mode_seq): the
        # settled plant / belly reference frames a FRESH episode of each
        # segment family would derive at reset (q_nom, _z0, pad-z ref).
        # Captured by a settle probe inside reset() (see
        # _seq_capture_frames) and installed at every mid-episode
        # switch — the trans-dagger2 kill (08-14) proved that carrying
        # the episode-reset q_nom across switches puts every later
        # segment's obs frame up to ~79 deg (knee, belly-vs-plant) off
        # the teachers' training distribution.
        self._seq_frames: dict | None = None
        self._imu_prev_v: np.ndarray | None = None
        self._imu_f_accum = np.zeros(3)
        self._imu_f_n = 0
        self._gyro_accum = np.zeros(3)
        self._gyro_n = 0
        self._att_rp: np.ndarray | None = None
        # Hardware-failure DR episode state (dr.cmd_drop_burst_len /
        # dr.imu_dropout_*, default OFF). Untouched unless the axis is on.
        self._cmd_dropping = False
        self._imu_dropping = False
        self._imu_drop_dead = False
        self._imu_hold_rp: tuple | None = None
        self._imu_hold_gyro: np.ndarray | None = None
        self._trip_cur_filt: np.ndarray | None = None
        self._tilt_ref0 = (0.0, 0.0)
        self._settle_lean = (0.0, 0.0)
        self._z0 = 0.0

        # Residual-blend GATED anneal (2026-09-09, assistfade rung 3
        # "blend-schedule fix" — rl_docs/tracks/assistfade/STATUS.md
        # 09-09 ~07:5x closure: 6/6 per-leg reward-shaping addons FAIL
        # on rung3's chronic single-leg sacrifice, all layered on the
        # SAME unchanged residual-fade base whose blend anneals UP on
        # a fixed step-count calendar (sched.key=goal.walk_residual_
        # blend) regardless of whether the policy is actually ready —
        # already-closed budget/schedule-SHAPE levers (stdslow,
        # latehandover, longbudget, 6 arms) show tweaking that
        # calendar's timing/slope doesn't help either. This is a
        # STRUCTURALLY different lever: don't anneal on a calendar at
        # all — hold the blend at a low value until a dedicated
        # ignition-quality assay of the policy's OWN unassisted output
        # passes (mirrors rung 2's already-proven train.bc_anchor_
        # anneal_gate contingent-anneal design, ported from an
        # anchor-LOSS coefficient to this action-space BLEND). Armed by
        # goal.walk_residual_anneal_gate>0 (default 0 = bit-exact off,
        # requires goal.walk_residual_gate>0 — fails closed, nothing to
        # anneal otherwise). Broadcast-driven like the other trainer
        # ramps (apply_residual_blend_frac, sim_env.py convention
        # shared with apply_drag_allow_frac/apply_term_penalty_frac/
        # etc in walk_task.py) rather than the self-clocked sched.*
        # engine, because the anneal START POINT depends on external
        # (assay) state the per-env tick clock cannot observe alone.
        # Armed-but-unbroadcast sits at the RAMP START (blend stays
        # LOW, matching "hold until proven ready" — the opposite
        # convention from the other ramps, which sit at TARGET when
        # unbroadcast, because those ramps loosen a safety-relevant
        # charge that must default to its validated value for any
        # eval/play path that never broadcasts; here the mechanism
        # itself (goal.walk_residual_gate) already defaults OFF for
        # any such path, and this ramp's only consumer is the training
        # loop's own callback, which always broadcasts frac=0 at
        # rollout 0 before any other value could be read).
        self._residual_blend_ramp: dict | None = None
        self._residual_blend_override: float | None = None
        _rba_gate = float(cfg_get(
            self.cfg, "goal", "walk_residual_anneal_gate",
            default=0.0) or 0.0) > 0.0
        if _rba_gate:
            if float(cfg_get(self.cfg, "goal", "walk_residual_gate",
                             default=0.0) or 0.0) <= 0.0:
                raise ValueError(
                    "goal.walk_residual_anneal_gate is set but goal."
                    "walk_residual_gate<=0 — there is no residual "
                    "blend mechanism armed to anneal, this flag would "
                    "silently no-op")
            _rba_start = float(cfg_get(
                self.cfg, "goal", "walk_residual_anneal_v0",
                default=0.05))
            _rba_target = float(np.clip(cfg_get(
                self.cfg, "goal", "walk_residual_blend", default=1.0),
                0.0, 1.0))
            if not 0.0 <= _rba_start <= _rba_target:
                raise ValueError(
                    "goal.walk_residual_anneal_v0 "
                    f"({_rba_start:g}) must be in [0, goal."
                    f"walk_residual_blend] ({_rba_target:g}) — the "
                    "gated anneal only ever RAISES the blend (more "
                    "raw-policy authority) from a low start toward "
                    "the cfg target, never the reverse")
            self._residual_blend_ramp = {
                "start": _rba_start, "target": _rba_target, "frac": 0.0,
            }
            self._residual_blend_override = _rba_start

        # Per-LEG refinement of the residual-anneal gate above
        # (2026-09-14, assistfade STATUS.md 09-09's own flagged-but-
        # untried candidate (b): "fade per-JOINT or per-LEG instead of
        # one global blend, so a leg that is still failing keeps more
        # scripted authority while others advance" — every reward-side
        # per-leg addon layered on the SAME single global blend scalar
        # was closed 6/6; this instead makes the blend ITSELF six
        # independent scalars, one per leg, each gated by that leg's
        # OWN ignition assay (walkcurr_cert.ignition_gate_pass_per_leg,
        # trainer-side). goal.walk_residual_perleg_gate>0 (default 0,
        # bit-exact off) requires the base anneal-gate above already
        # armed (fails closed — nothing to refine per-leg otherwise);
        # when armed, upgrades _residual_blend_override from a float
        # to a (6,) array (one entry per leg, mirror.py's N_LEGS
        # ordering: action index 3*leg+axis), all legs starting at the
        # SAME ramp start until apply_residual_blend_frac_perleg first
        # diverges them. See that method + the action-blend consumer
        # below (step()) for the array-vs-scalar broadcast contract.
        self._residual_perleg_gate = float(cfg_get(
            self.cfg, "goal", "walk_residual_perleg_gate",
            default=0.0) or 0.0) > 0.0
        if self._residual_perleg_gate:
            if not _rba_gate:
                raise ValueError(
                    "goal.walk_residual_perleg_gate is set but goal."
                    "walk_residual_anneal_gate<=0 — per-leg gating "
                    "refines the anneal-gate ramp; there is nothing "
                    "to refine if the base anneal-gate isn't armed")
            self._residual_blend_override = np.full(
                6, _rba_start, dtype=np.float64)

        # HOLD termination-grace CURRICULUM (2026-09-13, walkcurr
        # track — the sinkfence/holdlowstd joint refutation: 5/5
        # static-cfg-dose levers (base goal-mix, mixreweight exposure,
        # holdjitter start-offset, holdlowstd log-std-schedule, and a
        # TIGHTER static hold_max_height_drop_mm/hold_height_grace_s
        # envelope itself) converge on the identical "ride the
        # envelope to its bound" defect regardless of how wide or
        # tight that bound is fixed at. STATUS.md's own pre-registered
        # next escalation: "start wide, tighten with competence" — a
        # single STATIC envelope is either too loose (profitable long
        # sink, holdonly's 40mm/1.0s) or too tight (near-instant death
        # before any hold skill can form, sinkfence's 15mm/0.5s); ONLY
        # a schedule that starts at the loose value (so early
        # exploration survives long enough to see the plant income)
        # and tightens toward the validated tight target ONCE the
        # trainer's own rollout stream shows the policy already
        # surviving to truncation lets both regimes do their job in
        # sequence instead of at war with each other for the whole
        # run. Mirrors goal.walk_residual_anneal_gate's "gated ramp"
        # contract exactly (armed-but-unbroadcast sits at the LOOSE
        # START, not the target — the opposite convention from term_
        # penalty/drag_allow, which loosen a safety-relevant charge
        # and so must default to the validated value for any eval/play
        # path that never broadcasts; here the mechanism only ever
        # TIGHTENS a termination envelope, so sitting at the loose
        # start when unbroadcast is the safe/inert default — same
        # reasoning as residual_blend). Single source of truth:
        # safety.hold_grace_curriculum arms BOTH this env-side ramp
        # struct and the trainer-side gate callback below (train_ppo_
        # mjx.py) — no separate train.* on/off flag. The TARGET the
        # ramp tightens toward is whatever safety.hold_max_height_
        # drop_mm/hold_height_grace_s are already set to (the run's
        # own validated tight envelope); safety.hold_grace_start_*
        # name the loose starting point. Default 0 = off, bit-exact:
        # the HOLD-mode collapse check below falls straight back to
        # reading the two safety.* cfg leaves directly, unchanged.
        self._hold_grace_ramp: dict | None = None
        self._hold_grace_override_drop_mm: float | None = None
        self._hold_grace_override_grace_s: float | None = None
        _hg_gate = float(cfg_get(
            self.cfg, "safety", "hold_grace_curriculum",
            default=0.0) or 0.0) > 0.0
        if _hg_gate:
            _hg_target_drop = float(cfg_get(
                self.cfg, "safety", "hold_max_height_drop_mm",
                default=0.0))
            _hg_target_grace = float(cfg_get(
                self.cfg, "safety", "hold_height_grace_s", default=0.0))
            if _hg_target_drop <= 0.0:
                raise ValueError(
                    "safety.hold_grace_curriculum is set but safety."
                    "hold_max_height_drop_mm<=0 — there is no HOLD "
                    "termination envelope armed for this curriculum "
                    "to tighten toward")
            _hg_start_drop = float(cfg_get(
                self.cfg, "safety", "hold_grace_start_drop_mm",
                default=40.0))
            _hg_start_grace = float(cfg_get(
                self.cfg, "safety", "hold_grace_start_grace_s",
                default=1.0))
            if _hg_start_drop < _hg_target_drop:
                raise ValueError(
                    "safety.hold_grace_start_drop_mm "
                    f"({_hg_start_drop:g}) must be >= safety."
                    f"hold_max_height_drop_mm ({_hg_target_drop:g}) — "
                    "the curriculum only ever TIGHTENS the envelope "
                    "from a loose start, never loosens past the "
                    "validated target")
            if _hg_start_grace < _hg_target_grace:
                raise ValueError(
                    "safety.hold_grace_start_grace_s "
                    f"({_hg_start_grace:g}) must be >= safety."
                    f"hold_height_grace_s ({_hg_target_grace:g}) — "
                    "the curriculum only ever TIGHTENS the grace "
                    "window from a loose start, never loosens past "
                    "the validated target")
            self._hold_grace_ramp = {
                "start_drop": _hg_start_drop, "target_drop": _hg_target_drop,
                "start_grace": _hg_start_grace,
                "target_grace": _hg_target_grace, "frac": 0.0,
            }
            self._hold_grace_override_drop_mm = _hg_start_drop
            self._hold_grace_override_grace_s = _hg_start_grace

        if _gym is not None:
            self.observation_space = self._obs_space_box(
                N_OBS + current_sense_obs_dim(self.cfg)
                + height_err_sense_obs_dim(self.cfg)
                + height_vel_sense_obs_dim(self.cfg))
            self.action_space = _gym.spaces.Box(
                -1.0, 1.0, shape=(self.n_act,), dtype=np.float32)

    # ------------------------------------------------------------------
    # observation finalization: subclass augmentation + history stacking
    # ------------------------------------------------------------------

    def _obs_space_box(self, width: int):
        """Box obs space for a single-frame width, times history depth."""
        return _gym.spaces.Box(-np.inf, np.inf,
                               shape=(width * self._hist_n,),
                               dtype=np.float32)

    def _augment_obs(self, obs: np.ndarray, *,
                     reset: bool = False) -> np.ndarray:
        """Subclass hook: append extra per-tick dims (walk vel/phase).

        Runs BEFORE history stacking so appended dims are part of every
        stacked frame. Base env: identity.
        """
        return obs

    def _mujoco_to_logical_q(self, q_rad: np.ndarray) -> np.ndarray:
        """Convert the private MuJoCo hinge vector to the joint contract."""
        return mujoco_rel_rad_to_robot_abs_rad(q_rad)

    def _logical_to_mujoco_q(self, q_rad: np.ndarray) -> np.ndarray:
        """Convert the joint contract to the private MuJoCo hinge vector."""
        return robot_abs_rad_to_mujoco_rel_rad(q_rad)

    def _final_obs(self, obs: np.ndarray, *, reset: bool,
                   augment_reset: bool | None = None) -> np.ndarray:
        """Apply the augment hook, then the obs-history stack."""
        aug_reset = reset if augment_reset is None else bool(augment_reset)
        obs = self._augment_obs(obs, reset=aug_reset).astype(np.float32)
        if self._hist_n <= 1:
            return obs
        if reset or self._hist_buf is None:
            self._hist_buf = [obs.copy() for _ in range(self._hist_n)]
        else:
            self._hist_buf.pop()
            self._hist_buf.insert(0, obs.copy())
        # newest first: frame 0 is the current tick (transplant prefix).
        return np.concatenate(self._hist_buf).astype(np.float32)

    def _reset_history_probe_steps(self) -> int:
        """Controlled hold ticks used to seed a real observation history.

        The legacy reset repeats one final frame K times.  That erases the
        only dynamics available before the first policy action, precisely
        where a recovery policy needs to infer support/contact.  This
        opt-in probe keeps commanding the captured passive equilibrium and
        records K-1 additional sensor frames without advancing the episode
        clock or paying reward.  C MuJoCo and both MJX reset paths call the
        same two helpers.
        """
        enabled = float(cfg_get(self.cfg, "obs", "reset_history_probe",
                                default=0.0)) > 0.0
        return self._hist_n - 1 if enabled and self._hist_n > 1 else 0

    def _reset_history_probe_obs(self) -> np.ndarray:
        """Read one controlled reset-probe tick into the history stack."""
        self._state = self._read_state()
        goal = self._current_goal()
        return self._final_obs(
            build_obs(self.cfg, self._state, self._q_nom,
                      self._prev_action, goal=goal,
                      tilt_ref=self._tilt_ref0,
                      height_vel_mps=self._height_vel_mps),
            reset=False, augment_reset=True)

    # ------------------------------------------------------------------
    # state readout (sim → RobotState, with DR sensor corruption)
    # ------------------------------------------------------------------

    def _apply_imu_dropout(self, er, roll, pitch, gyro):
        """dr.imu_dropout_* -- model a frozen/dead IMU (the real MPU-6050
        sentinel-65534 failure). Two-state Markov: enter a dropout with
        er.imu_dropout_prob, stay each tick with prob (1 - 1/ticks); while
        dropped the obs roll/pitch/gyro FREEZE at the last healthy read or go
        DEAD (zero), chosen per dropout by er.imu_dropout_dead_frac. Only
        called when the axis is on (caller guards imu_dropout_ticks>0), so the
        default path is bit-exact."""
        if self._imu_hold_rp is None:
            self._imu_hold_rp = (float(roll), float(pitch))
            self._imu_hold_gyro = np.asarray(gyro, dtype=float).copy()
        ticks = max(float(er.imu_dropout_ticks), 1.0)
        if self._imu_dropping:
            dropped = True
            if self.rng.random() < (1.0 / ticks):
                self._imu_dropping = False
        else:
            dropped = self.rng.random() < er.imu_dropout_prob
            if dropped:
                self._imu_dropping = True
                self._imu_drop_dead = bool(
                    self.rng.random() < er.imu_dropout_dead_frac)
        if dropped:
            if self._imu_drop_dead:
                return 0.0, 0.0, np.zeros(3)
            r, pch = self._imu_hold_rp
            return r, pch, self._imu_hold_gyro
        self._imu_hold_rp = (float(roll), float(pitch))
        self._imu_hold_gyro = np.asarray(gyro, dtype=float).copy()
        return roll, pitch, gyro

    def _read_state(self) -> RobotState:
        mujoco = self._mujoco
        q = self.data.qpos[self._qadr].copy()
        qd = self.data.qvel[self._vadr].copy()
        torque = self.data.qfrc_actuator[self._vadr].copy()
        if self._struct_comp is not None and self._struct_comp_k is not None:
            q = self._struct_comp.reported_q(q, torque,
                                             k=self._struct_comp_k)
        q = self._mujoco_to_logical_q(q)
        qd = self._mujoco_to_logical_q(qd)

        # Attitude the way the hardware computes it: from the accelerometer
        # specific force f = a - g at the IMU's mounting point. Gravity may
        # be tilted (ground slope DR), the IMU frame rotated (mount
        # misalignment DR), and — because the IMU could be bolted anywhere
        # on the robot — the mounting point offset from the chassis center.
        # An off-center IMU picks up lever-arm acceleration whenever the
        # body rotates, corrupting the tilt estimate exactly during leans;
        # that corruption is the point of modeling it.
        er = self._ep_rand
        R = self.data.xmat[self._chassis_bid].reshape(3, 3).copy()
        mount = np.eye(3) if er is None else er.imu_mount_rot
        # Specific force averaged over the tick's physics substeps (see
        # _advance) — like a 1 kHz-sampled, low-passed MEMS accel read at
        # 25 Hz. FD across whole control ticks aliased servo dither into
        # ±10° phantom tilt spikes.
        if self._imu_f_n > 0:
            f_world = self._imu_f_accum / self._imu_f_n
        else:
            f_world = -np.asarray(self.model.opt.gravity, dtype=float)
        self._imu_f_accum[:] = 0.0
        self._imu_f_n = 0
        f_imu = (R @ mount).T @ f_world
        ax, ay, az = f_imu  # measures +g when level and static
        roll_acc = math.atan2(ay, az)
        pitch_acc = math.atan2(-ax, math.hypot(ay, az))
        if self._gyro_n > 0:
            gyro = self._gyro_accum / self._gyro_n
        else:
            gyro = self.data.sensordata[
                self._gyro_adr:self._gyro_adr + 3].copy()
        self._gyro_accum[:] = 0.0
        self._gyro_n = 0

        if er is not None:
            q = q + er.joint_zero_bias_rad
            q = q + self.rng.normal(0.0, er.encoder_noise_rad, N_JOINTS)
            roll_acc += (er.imu_bias_rad[0]
                         + self.rng.normal(0.0, er.tilt_noise_rad))
            pitch_acc += (er.imu_bias_rad[1]
                          + self.rng.normal(0.0, er.tilt_noise_rad))
            gyro = er.imu_mount_rot.T @ gyro  # gyro axes rotate with mount
            gyro = (gyro + er.gyro_bias_rad_s
                    + self.rng.normal(0.0, er.gyro_noise_rad_s, 3))

        # Complementary filter, same as the hardware estimator
        # (ComplementaryAttitude, default alpha=0.98): integrate gyro,
        # drift-correct slowly toward the accel tilt. Without it the raw
        # accel tilt sees the full lever-arm spikes of an off-center IMU
        # (±20° for one tick) — real firmware filters those out, so the
        # sim must too. alpha is config-driven (sensing.attitude_alpha) so
        # training matches whatever gyro-trust the deployed runner uses.
        alpha = self._attitude_alpha
        if self._deployed_transport is not None:
            # The acquired-frame hardware filter below owns integration.
            # Never integrate held observations once per policy tick.
            roll, pitch = roll_acc, pitch_acc
        elif self._att_rp is None:
            self._att_rp = np.array([roll_acc, pitch_acc])
        else:
            self._att_rp = np.array([
                alpha * (self._att_rp[0] + gyro[0] * self.dt)
                + (1.0 - alpha) * roll_acc,
                alpha * (self._att_rp[1] + gyro[1] * self.dt)
                + (1.0 - alpha) * pitch_acc])
        if self._deployed_transport is None:
            roll, pitch = float(self._att_rp[0]), float(self._att_rp[1])
        # DR: IMU dropout / freeze (dr.imu_dropout_*, default OFF => the
        # guard skips the call: no rng, no state touched, bit-exact). Models
        # the real MPU-6050 freezing to a stuck sentinel (65534) / reading dead.
        _er_imu = self._ep_rand
        if _er_imu is not None and _er_imu.imu_dropout_ticks > 0.0:
            roll, pitch, gyro = self._apply_imu_dropout(
                _er_imu, roll, pitch, gyro)

        # Servo current estimate. torque and qvel are both in MuJoCo DOF
        # order here (torque = qfrc_actuator[_vadr], NOT remapped to
        # logical); this is what the estimate has always used and what the
        # power model was fitted against, so per-joint order is consistent.
        #
        # DEFAULT ("power"): the validated mechanical-power model (fitted
        # 2026-09-19, /tmp/gaitval, over survey gaits 1-4,7,10 vs the real
        # robots' walk_summary current_mean_a):
        #     per-joint current = iq/18 + k * |torque * qvel|
        # (iq_bus=0.19 A, k=0.02282 A/W), then a 0.1 s low-pass. The
        # ~345:1 non-backdrivable STS3215 gearbox holds a static load at
        # ~0 winding current, so this correctly makes holding/stance cheap
        # — the old min(|torque|*1.2, 3.0) proxy overstated holding current
        # ~20x. See rl_move/sim/audit_over_current.py for the old proxy's
        # anatomy.
        #
        # SAFETY: precisely because holding is cheap, a STALL (high torque,
        # ~0 speed → ~0 mechanical power) also reads ~0 A under this model,
        # so keying the SafetyLayer over-current trip on it would SILENTLY
        # DISABLE stall protection (a real STS3215 melts fighting a bad
        # pose — cooked knee, 2026-08-06). We therefore keep a SEPARATE,
        # stall-sensitive trip signal from the LEGACY torque proxy
        # (min(|torque|*1.2, 3.0), same 0.1 s low-pass) in
        # ``over_current_signal``; the SafetyLayer and trip-proximity
        # reward shaping prefer it (robot_state.over_current_reading), so a
        # stall trips EXACTLY as before while the reward sees true power.
        #
        # LEGACY ("torque_proxy"): servo_current = the old proxy and NO
        # separate trip signal (over_current_signal=None → the trip falls
        # back to servo_current). Bit-exact with pre-2026-09-19 behavior.
        alpha = self.dt / (self.dt + 0.1)
        legacy_current = np.minimum(np.abs(torque) * 1.2, 3.0)
        if self._current_model == "power":
            qvel_raw = self.data.qvel[self._vadr]  # MuJoCo order, w/ torque
            raw_current = (self._current_iq_joint
                           + self._current_k_a_per_w
                           * np.abs(torque * qvel_raw))
            if self._current_k_stall_a_per_nm:
                # Winding/load-stall term: current ~ torque above the free-
                # hold rail (2026-09-21 refit). Zero at idle/gentle holds
                # (|torque| < thr), so idle stays iq_bus and the trip signal
                # (below) is untouched.
                raw_current = (raw_current
                               + self._current_k_stall_a_per_nm
                               * np.maximum(np.abs(torque)
                                            - self._current_stall_thr_nm, 0.0))
            raw_trip = legacy_current
        else:
            raw_current = legacy_current
            raw_trip = None
        if getattr(self, "_cur_filt", None) is None:
            self._cur_filt = raw_current
        else:
            self._cur_filt = (1.0 - alpha) * self._cur_filt + alpha * raw_current
        servo_current = self._cur_filt.copy()
        over_current_signal = None
        if raw_trip is not None:
            if getattr(self, "_trip_cur_filt", None) is None:
                self._trip_cur_filt = raw_trip
            else:
                self._trip_cur_filt = ((1.0 - alpha) * self._trip_cur_filt
                                       + alpha * raw_trip)
            over_current_signal = self._trip_cur_filt.copy()

        # Optional height-RATE channel (obs.height_vel_sense, 2026-09-17
        # walkcurr `lower` observation-space axis, RATE half -- see
        # rl_move.estimator.HeightRateEstimator / env.build_obs). Uses
        # the SAME (possibly DR-corrupted) q/roll/pitch build_obs's
        # position channel (obs.height_err_sense) reads off `state`,
        # just computed here where the stateful estimator instance
        # lives (build_obs itself stays pure/stateless). Gated so a run
        # with the channel off pays no extra FK cost.
        if float(cfg_get(self.cfg, "obs", "height_vel_sense",
                         default=0.0)) == 1.0:
            if getattr(self, "_height_vel_est", None) is None:
                from rl_move.estimator import HeightRateEstimator
                self._height_vel_est = HeightRateEstimator(dt=self.dt)
            self._height_vel_mps = self._height_vel_est.update(
                q, roll, pitch)
        else:
            self._height_vel_mps = 0.0

        del mujoco
        state = RobotState(
            timestamp=self.data.time,
            joint_position=q,
            joint_velocity=qd,
            imu_roll=float(roll),
            imu_pitch=float(pitch),
            imu_yaw=0.0,
            imu_gyro=gyro,
            imu_accel=f_imu,
            commanded_position=self._cmd.copy(),
            servo_current=servo_current,
            over_current_signal=over_current_signal,
            bus_ok=True,
            imu_ok=True,
            dt=self.dt,
        )
        if self._deployed_transport is not None:
            state = self._deployed_transport.acquire(
                state, accel_tilt=(roll_acc, pitch_acc))
        return state

    # ------------------------------------------------------------------
    # physics
    # ------------------------------------------------------------------

    def _apply_struct_compliance_to_model(self, model) -> None:
        if self._struct_comp is None or self._struct_comp_k is None:
            return
        self._struct_comp.apply_effective_kp(
            model, self._pos_act, k=self._struct_comp_k)

    def _walk_push_torque_nm(self) -> float:
        """dr.walk_push_* (08-12, the takeoff mechanism the command-side
        kick could not deliver): signed half-sine roll TORQUE on the
        chassis over the first ~second of walk-mode episodes, applied
        via xfrc_applied about the chassis's own x-axis. The 08-12
        replay_trace calibration measured the fold-pulse kick
        saturating at 5-10° peak / ~10 °/s at ANY dose (planted
        opposite feet + write-profile rate limit), far below the
        hardware takeoff regime (13-27° peaks, 11-46 °/s) — a base
        torque bypasses the actuator path and reaches it. Stateless
        per tick (pure function of _ep_rand + _step_i; the substep
        loop overwrites xfrc every step, zero outside the window →
        pool-restore safe). Applied by _advance on private-model envs;
        shared-model (MJX shim) envs expose it to their vec env, which
        hands the per-env value to the batched stepper's xfrc row."""
        er = self._ep_rand
        if (er is None or er.walk_push_peak_nm == 0.0
                or er.walk_push_dur_s <= 0.0
                or self._goal_traj is None
                or getattr(self._goal_traj, "mode", "") != "walk"):
            return 0.0
        t = self._step_i * self.dt
        repeat_s = float(getattr(er, "walk_push_repeat_period_s", 0.0))
        if repeat_s > 0.0:
            t -= float(getattr(er, "walk_push_start_s", 0.0))
            if t < 0.0:
                return 0.0
            t %= repeat_s
        if t >= er.walk_push_dur_s:
            return 0.0
        return er.walk_push_peak_nm * math.sin(
            math.pi * t / er.walk_push_dur_s)

    def _ext_push_force_n(self) -> tuple[float, float]:
        """dr.ext_push_* (AMP brief §7.4/§9.3, M3 push-recovery
        curriculum): a mid-episode horizontal FORCE pulse (fx, fy),
        world-frame, half-sine ramped like every pulse in this file.
        Unlike ``_walk_push_torque_nm`` (a fixed roll TORQUE confined to
        the first ~1.5s that reproduces the hardware TAKEOFF wobble),
        this fires once (or, with dr.ext_push_repeat_max>1, several
        times -- see EpisodeRandomization.ext_push_extra) at random
        point(s) LATER in a walk-mode episode on a policy that is
        already walking -- the actual "shove it mid-stride and see if
        it recovers" test. Stateless per tick (pure function of
        _ep_rand + _step_i); zero outside every pulse's window ->
        pool-restore safe, same as its sibling. The pulses are sampled
        non-overlapping (see domain_rand.sample), so at most one term
        is ever nonzero -- summing is just the simplest way to combine
        them without a branch per pulse."""
        er = self._ep_rand
        if (er is None or self._goal_traj is None
                or getattr(self._goal_traj, "mode", "") != "walk"):
            return (0.0, 0.0)
        t = self._step_i * self.dt
        fx = fy = 0.0
        for peak, dur, t0, ang in (
                (er.ext_push_peak_n, er.ext_push_dur_s,
                 er.ext_push_start_s, er.ext_push_dir_rad),
                *er.ext_push_extra):
            if peak == 0.0 or dur <= 0.0 or t < t0 or t >= t0 + dur:
                continue
            mag = peak * math.sin(math.pi * (t - t0) / dur)
            fx += mag * math.cos(ang)
            fy += mag * math.sin(ang)
        return (fx, fy)

    def _advance(self, *, limp: bool = False) -> None:
        assert self._profile is not None
        mujoco = self._mujoco
        h = self.model.opt.timestep
        r_off = (np.zeros(3) if self._ep_rand is None
                 else self._ep_rand.imu_pos_m)
        vel = np.zeros(6)
        push_nm = 0.0 if limp else self._walk_push_torque_nm()
        push_fx, push_fy = (0.0, 0.0) if limp else self._ext_push_force_n()
        # Only claim xfrc_applied[chassis, 0:3] for episodes that actually
        # drew an ext_push this episode (dr.ext_push_prob > 0 somewhere
        # upstream) -- indices 0:3 are also used by unrelated interactive
        # tools (web_session.py's manual push slider, quad probes) that
        # never touch dr.ext_push_*; when this episode never drew a push
        # (the default, and always true for those tools since they don't
        # set dr.ext_push_prob), skip the write entirely so this axis
        # stays a complete no-op and cannot clobber their state.
        ext_push_owns_row = (not limp and self._ep_rand is not None
                             and self._ep_rand.ext_push_peak_n != 0.0)
        # Transient per-leg foot-catch/stumble event (dr.foot_catch_
        # force_n, see _update_foot_catch_state for the liftoff-
        # triggered window this reads). Computed ONCE per tick like
        # push_nm/push_fx above -- the window (_foot_catch_end_s) is
        # tick-granularity, not substep-granularity. foot_catch_active
        # is None whenever this episode owns no row (the default),
        # so the substep loop below skips the per-leg write entirely.
        foot_catch_active = None
        if not limp and self._foot_catch_owns_row:
            t_now = self._step_i * self.dt
            foot_catch_active = t_now < self._foot_catch_end_s
        for _ in range(self._substeps):
            # load_nm feeds BOTH the dynamic backlash (if active) and the
            # load-coupled latency (if active) -- same one-substep-lagged
            # |actuator force| reading, harmless (unread) when neither
            # mechanism is enabled this episode.
            target = self._profile.tick(h, load_nm=self._backlash_prev_force)
            if not limp and self._backlash is not None:
                # Dynamic joint backlash (dr.joint_backlash_deg, see
                # domain_rand.JointBacklash): the effective target lags
                # the profile's true target by up to half the (possibly
                # load-widened) gap after a direction reversal. Load is
                # the PREVIOUS substep's actuator force -- one-substep
                # lagged, never a look-ahead into this substep's own
                # not-yet-computed torque.
                target = self._backlash.apply(
                    target, self._backlash_prev_force)
            q = self.data.qpos[self._qadr]
            if limp:
                # Torque-off settling (reset only): the actuator reference
                # follows q, leaving pure kv damping — how an operator
                # lays the robot down before enabling hold.
                eff = q
            else:
                # Firmware dead-zone at the PHYSICS level: inside the
                # deadband the real controller outputs nothing, so a servo
                # holding a settled pose applies ~zero torque. Without
                # this, the stiff fitted kp (≈1000 Nm/rad) turns a 0.2°
                # captured-pose offset into a 3 Nm isometric fight against
                # the ground — the robot chatters on its contacts and
                # "draws" 3 A lying still (belly-rest episodes tripped
                # over_current doing nothing). Soft dead-zone: torque
                # grows smoothly from zero past the band.
                err = target - q
                db = self._profile.deadband_rad
                eff = q + np.sign(err) * np.maximum(np.abs(err) - db, 0.0)
            self.data.ctrl[self._pos_act] = eff
            # Takeoff push torque about the chassis's CURRENT x-axis
            # (world-frame xfrc row). Overwritten every substep, zeroed
            # outside the pulse window — no state survives the window.
            Rp = self.data.xmat[self._chassis_bid].reshape(3, 3)
            self.data.xfrc_applied[self._chassis_bid, 3:6] = (
                Rp[:, 0] * push_nm)
            # Mid-episode external push (dr.ext_push_*): world-frame
            # horizontal force, same overwrite-every-substep /
            # zero-outside-window convention as the takeoff torque
            # above (no state survives the pulse window) -- but ONLY
            # for episodes that own this row (see ext_push_owns_row).
            if ext_push_owns_row:
                self.data.xfrc_applied[self._chassis_bid, 0:3] = (
                    push_fx, push_fy, 0.0)
            # Transient foot-catch/stumble event: brief retrograde
            # (opposing the chassis's current forward direction, same
            # Rp as the takeoff torque above) + downward force on the
            # caught foot's PAD body -- world-frame, overwritten every
            # substep, zeroed outside each leg's own active window
            # (same no-state-survives-the-window convention as every
            # other pulse in this file). Only touches pad-body xfrc
            # rows for episodes that own them (see reset-time
            # ``_foot_catch_owns_row``) -- nothing else in this file
            # writes ``xfrc_applied`` on ``_pad_bids``.
            if foot_catch_active is not None:
                fwd = Rp[:, 0]
                for i in range(6):
                    if foot_catch_active[i]:
                        fmag = float(self._ep_rand.foot_catch_force_n[i])
                        self.data.xfrc_applied[self._pad_bids[i], 0:3] = (
                            -fwd[0] * fmag, -fwd[1] * fmag,
                            -fmag * FOOT_CATCH_DOWN_FRAC)
                    else:
                        self.data.xfrc_applied[self._pad_bids[i], 0:3] = (
                            0.0, 0.0, 0.0)
            mujoco.mj_step(self.model, self.data)
            # Unconditional (was gated on self._backlash is not None):
            # the load-coupled latency mechanism (ServoProfile.tick's
            # load_nm) also reads this lagged reading, and computing it
            # is cheap/inert when neither mechanism is enabled -- no
            # physics/reward path consumes it in that case.
            self._backlash_prev_force[:] = np.abs(
                self.data.actuator_force[self._pos_act])
            # Accumulate the IMU-point specific force at the physics rate
            # (exact velocities, one FD) — includes the lever-arm
            # acceleration of an off-center IMU without tick-rate
            # aliasing. Averaged per control tick in _read_state.
            mujoco.mj_objectVelocity(
                self.model, self.data, mujoco.mjtObj.mjOBJ_BODY,
                self._chassis_bid, vel, 0)
            R = self.data.xmat[self._chassis_bid].reshape(3, 3)
            v_pt = vel[3:] + np.cross(vel[:3], R @ r_off)
            if self._imu_prev_v is not None:
                a_pt = (v_pt - self._imu_prev_v) / h
                self._imu_f_accum += a_pt - self.model.opt.gravity
                self._imu_f_n += 1
            self._imu_prev_v = v_pt.copy()
            # Gyro too: the chassis micro-dithers at tens of Hz (stiff
            # contacts + stiff servos); sampling the instantaneous rate
            # once per control tick aliases that into phantom rotation
            # which the attitude filter then integrates. The real MPU
            # integrates at 1 kHz where zero-mean dither cancels.
            self._gyro_accum += self.data.sensordata[
                self._gyro_adr:self._gyro_adr + 3]
            self._gyro_n += 1

    def _settle(self, seconds: float, *, limp: bool = False) -> None:
        n = int(round(seconds / self.dt))
        for _ in range(n):
            self._advance(limp=limp)

    @staticmethod
    def _clip_to_joint_limits(q: np.ndarray) -> np.ndarray:
        """Clip a robot-absolute joint vector to hardware limits."""
        from rl_move.safety import AXIS_LIMITS_DEG
        q = q.copy()
        for j in range(N_JOINTS):
            lo, hi = AXIS_LIMITS_DEG[j % 3]
            q[j] = float(np.clip(q[j], lo * DEG2RAD, hi * DEG2RAD))
        return q

    def _sample_reset_start_offset_rad(self) -> np.ndarray | None:
        """Config-level start jitter, separate from broad DR.

        ``dr.placement_noise_deg`` already covers this in randomized
        training. The reset.* knobs exist so evaluators can run a DR0
        "imperfect handoff" panel without also perturbing mass,
        friction, latency, sensors, or faults.
        """
        jitter = float(cfg_get(self.cfg, "reset", "start_jitter_deg",
                               default=0.0))
        bad_prob = float(cfg_get(self.cfg, "reset", "start_bad_prob",
                                 default=0.0))
        if jitter < 0.0:
            raise ValueError("reset.start_jitter_deg must be >= 0")
        if not 0.0 <= bad_prob <= 1.0:
            raise ValueError("reset.start_bad_prob must be in [0, 1]")
        if jitter == 0.0 and bad_prob == 0.0:
            self._reset_start_bad_joints = []
            return None
        off = np.zeros(N_JOINTS, dtype=float)
        if jitter > 0.0:
            off += self.rng.uniform(-jitter, jitter, N_JOINTS) * DEG2RAD
        bad_joints: list[int] = []
        if bad_prob > 0.0 and self.rng.random() < bad_prob:
            max_joints = int(float(cfg_get(
                self.cfg, "reset", "start_bad_max_joints", default=1)))
            max_joints = max(1, min(N_JOINTS, max_joints))
            lo = float(cfg_get(self.cfg, "reset", "start_bad_deg_min",
                               default=8.0))
            hi = float(cfg_get(self.cfg, "reset", "start_bad_deg_max",
                               default=16.0))
            if lo < 0.0 or hi < lo:
                raise ValueError("reset.start_bad_deg_min/max invalid")
            n_bad = int(self.rng.integers(1, max_joints + 1))
            bad_joints = list(self.rng.choice(
                N_JOINTS, size=n_bad, replace=False))
            for j in bad_joints:
                mag = float(self.rng.uniform(lo, hi)) * DEG2RAD
                off[j] = mag if self.rng.random() < 0.5 else -mag
        self._reset_start_bad_joints = [int(j) for j in bad_joints]
        return off

    def _apply_reset_start_offset(self, q: np.ndarray) -> np.ndarray:
        off = self._reset_start_offset_rad
        if off is None:
            return q
        return q + off

    def _start_pose_rad(self) -> np.ndarray:
        """Plant pose plus start-offset channels, clipped to limits."""
        q = self._plant_deg * DEG2RAD
        if self._ep_rand is not None:
            q = q + self._ep_rand.start_offset_rad
        q = self._apply_reset_start_offset(q)
        return self._clip_to_joint_limits(q)

    # Tipped-start hip-fold gain: settled body roll per degree of hip
    # fold, measured on the CPU twin at the plant stance (probe 08-10:
    # settled roll ≈ 0.36 × fold, near-linear over 6-18° targets; see
    # the dr.tipped_start_* axis in domain_rand.py). The inverse maps
    # the sampled target roll to the fold the pattern commands.
    # SHARED by rise_rock/walk_kick, whose doses were replay-calibrated
    # against hardware tapes THROUGH this mapping — do not retune it
    # for them (their targets are trip-crossing by design).
    TIP_ROLL_PER_FOLD = 0.36
    # Tipped-START-only recalibration (dig-in 2026-09-23, hardstartcorr
    # plateau root cause): at the current plant stance the 0.36 gain
    # overshoots — achieved settle roll ≈ 1.33 × target on BOTH model
    # families (measured med ratios 1.26–1.40 mesh, 1.31–1.37
    # primitive over 3–7° targets, /tmp probe recorded in the 09-23
    # standwalk STATUS entry), so a capped 7° target settled at
    # 9.0–11.0° and spawned INSIDE the 10° tilt_roll trip band —
    # violating this method's own "spawn with recovery headroom, never
    # mid-trip" invariant and making ~30–40 % of max-dose tipped plant
    # spawns unwinnable regardless of policy (terminated 0.76–1.0 s
    # after reset under an idealized instant level command). The
    # tipped path therefore uses its own measured gain so achieved
    # roll ≈ sampled target; rise_rock/walk_kick keep 0.36 untouched.
    TIPPED_START_ROLL_PER_FOLD = 0.48

    def _apply_tipped_start(self, q_start: np.ndarray) -> np.ndarray:
        """Add the tipped-start (roll recovery) pattern, if this episode
        drew one (dr.tipped_start_*; plant/park starts only — the
        caller decides, belly-rise starts never tip).

        The sampled target body roll becomes an asymmetric leg fold:
        folding one side's hips drops the body on that side once the
        feet load (the same hip sign the park start uses to LIFT feet —
        with the foot planted the body moves instead); the folded
        side's knees extend a little to keep the feet under the hips.
        The target is capped at 70% of the run's own tilt-trip envelope
        so the episode spawns with recovery headroom, never mid-trip
        (stance runs at 10° see ≤7° tips; the 25° deployment contract
        sees ≤17.5°). Sets ``_tipped_applied`` so _reset_finalize keeps
        the tilt reference LEVEL instead of re-anchoring at the lean.
        """
        er = self._ep_rand
        if er is None or abs(er.tipped_roll_deg) < 1e-9:
            return q_start
        cap = 0.7 * self.safety.max_roll * RAD2DEG
        roll = float(np.clip(er.tipped_roll_deg, -cap, cap))
        fold = abs(roll) / self.TIPPED_START_ROLL_PER_FOLD * DEG2RAD
        # Legs 0-2 mount on the +y (left) side (azimuths 30/90/150°),
        # legs 3-5 on the right; positive roll leans the body right
        # (IMU convention: roll = atan2(ay, az), +y side up).
        legs = (3, 4, 5) if roll > 0 else (0, 1, 2)
        q = q_start.copy()
        for leg in legs:
            q[joint_index(leg, "hip")] -= fold
            q[joint_index(leg, "knee")] += 0.5 * fold
        self._tipped_applied = True
        return q

    def _rise_rock_offset(self) -> np.ndarray | None:
        """dr.rise_rock_* (08-11, hardware belly-curl rocking gap):
        one-side hip/knee fold bias added to the PHYSICAL servo
        command on rise-mode episodes that drew it, RAMP-GATED by the
        rise goal's height-ramp progress. Uses the tipped-start
        fold→roll mapping. The logical loop never sees the bias (like
        zero_drift_cmd_frame); encoders read the true drooped angles
        and the tilt reference stays level, so leveling and honest
        ref-tracking are paid only when the policy closes the
        command-vs-read loop. Stateless per tick (pure function of
        _ep_rand + _goal_traj + _step_i → pool-restore safe by
        construction).

        CALIBRATION (08-11/12, replay_trace open-loop replay of the
        10 recorded rl_stand failures): the hardware trip is NOT a
        curl-long rock — the tapes are FLAT through the curl, then
        ramp 0→10.6° in the last ~1.2 s as the belly unloads onto a
        near-diagonal foot pair (support knife-edge; sim and hardware
        sit on opposite branches — sim gets caught at ~2° by the
        planted opposite feet, hardware tips through the trip).
        A PERSISTENT fold rocks the flat curl too (unlike every tape)
        and one sign saturates at 3-5°; gating the fold by the
        height-ramp fraction reproduces the recorded signature:
        flat curl, then an accelerating ramp that crosses the 10°
        trip band near ramp end at ~18° target dose on the branch
        that removes the catching foot (the other branch saturates —
        sign is sampled ±, so training visits both)."""
        er = self._ep_rand
        if (er is None or er.rise_rock_roll_deg == 0.0
                or self._goal_traj is None
                or getattr(self._goal_traj, "mode", "") != "rise"):
            return None
        h = np.asarray(self._goal_traj.height, dtype=float)
        h_tgt = float(np.max(h)) if h.size else 0.0
        if h_tgt <= 1e-9:
            frac = 1.0
        else:
            i = min(max(self._step_i, 0), len(h) - 1)
            frac = float(np.clip(h[i] / h_tgt, 0.0, 1.0))
        if frac <= 1e-6:
            return None
        roll = er.rise_rock_roll_deg
        fold = abs(roll) * frac / self.TIP_ROLL_PER_FOLD * DEG2RAD
        legs = (3, 4, 5) if roll > 0 else (0, 1, 2)
        dq = np.zeros(N_JOINTS, dtype=float)
        for leg in legs:
            dq[joint_index(leg, "hip")] -= fold
            dq[joint_index(leg, "knee")] += 0.5 * fold
        return dq

    def _walk_kick_offset(self) -> np.ndarray | None:
        """dr.walk_kick_* (08-11, hardware takeoff-transient gap):
        TRANSIENT one-side fold pulse on the PHYSICAL servo command
        over the first ~second of walk-mode episodes. bench_report
        over 18 hardware walks: every one crosses 5° roll within
        0.6-1.5 s of gait start at 11-46 °/s roll rates, and static
        leans do not reproduce it (takeoff25-r1 child==parent) — the
        gap is the roll RATE, so the injection must move. Half-sine
        envelope: ramps in and out with net-zero terminal offset, so
        only the dynamic excursion remains to be survived. Same
        fold→roll mapping and command-side wiring as tipped/rise-rock
        (logical loop blind, encoders read true angles, tilt ref
        level). Stateless per tick (pure function of _ep_rand +
        _step_i → pool-restore safe by construction)."""
        er = self._ep_rand
        if (er is None or er.walk_kick_roll_deg == 0.0
                or er.walk_kick_dur_s <= 0.0
                or self._goal_traj is None
                or getattr(self._goal_traj, "mode", "") != "walk"):
            return None
        t = self._step_i * self.dt
        if t >= er.walk_kick_dur_s:
            return None
        roll = er.walk_kick_roll_deg * math.sin(
            math.pi * t / er.walk_kick_dur_s)
        if abs(roll) < 0.5:
            return None
        fold = abs(roll) / self.TIP_ROLL_PER_FOLD * DEG2RAD
        legs = (3, 4, 5) if roll > 0 else (0, 1, 2)
        dq = np.zeros(N_JOINTS, dtype=float)
        for leg in legs:
            dq[joint_index(leg, "hip")] -= fold
            dq[joint_index(leg, "knee")] += 0.5 * fold
        return dq

    def _walk_stop_freeze_override(self, q_safe):
        """goal.walk_stop_freeze_s (2026-08-24, joyfullcurr10-
        stopsettle-probe dig-in): STRUCTURAL stop-hold, not a reward
        charge. The stopsettle diagnostic measured the V6 b1 cert's
        residual creep as a genuine POST-grace floor (excluding the
        exact 0.4s reward.walk_stop_grace_s window a checkpoint was
        trained under barely moved the metric: stop_speed_settled_m_s
        0.03107 vs raw stop_speed_m_s 0.03264, ~5%) -- refuting the
        entire stop-speed/stop-current REWARD-PRICING lever both by
        dose (joyfullcurr9/10) and by measurement methodology (this
        run), per that run's own pre-registered gate text. This hook
        is the named next lever: instead of pricing sustained motion
        and hoping the policy learns true stillness, it FORCES the
        physical command to hold -- once a walk/quadwalk-mode stop
        segment has been commanded for more than walk_stop_freeze_s
        seconds (same grace convention as the stop reward charges),
        the tick's own q_safe is discarded and replaced with the
        PREVIOUS tick's own safe command (self._cmd, read before it is
        overwritten below) -- i.e. the policy's action this tick is
        never issued to the plant. This is why the override must
        return the previous q_safe rather than re-deriving a target
        from a zeroed action: the action space is an offset from the
        nominal pose, not from the previous command, so a zeroed
        action would NOT generally hold the current pose. Turn-in-
        place commands (wz_ref != 0) are exempted exactly like the
        stop reward charges (a nonzero turn IS the commanded motion).
        The elapsed-stop timer still advances during an exempted turn
        (matching the reward charges' own timer semantics) so a turn
        that stops mid-episode does not get a fresh grace window.
        Default 0.0 = off, bit-exact (returns q_safe unchanged, no
        state touched)."""
        thr = float(cfg_get(self.cfg, "goal", "walk_stop_freeze_s",
                             default=0.0))
        if thr <= 0.0:
            return q_safe
        if (self._goal_traj is None
                or getattr(self._goal_traj, "mode", "")
                not in ("walk", "quadwalk")):
            return q_safe
        goal = self._current_goal()
        s_ref = float(np.hypot(
            float(getattr(goal, "vx_ref", 0.0) or 0.0),
            float(getattr(goal, "vy_ref", 0.0) or 0.0)))
        if s_ref > 1e-3:
            self._walk_stop_freeze_cmd_s = 0.0
            return q_safe
        t = getattr(self, "_walk_stop_freeze_cmd_s", 0.0) + self.dt
        self._walk_stop_freeze_cmd_s = t
        wz = abs(float(getattr(goal, "wz_ref", 0.0) or 0.0))
        if wz > 1e-3 or t < thr:
            return q_safe
        return self._cmd.copy()

    def _true_roll_pitch(self) -> tuple[float, float]:
        """Ground-truth chassis attitude in the IMU's roll/pitch
        convention (privileged; reset-time only). Uses the episode's
        own gravity so slope DR stays inside the tilt reference,
        exactly like the legacy start-attitude anchoring."""
        R = np.asarray(self.data.xmat[self._chassis_bid],
                       dtype=float).reshape(3, 3)
        g = (self._ep_rand.gravity_vec if self._ep_rand is not None
             else np.array([0.0, 0.0, -9.80665]))
        f = R.T @ (-g)   # static specific force in the body frame
        return (math.atan2(f[1], f[2]),
                math.atan2(-f[0], math.hypot(f[1], f[2])))

    def _recover_start_bank(self) -> np.ndarray | None:
        """Harvested recover-mode start poses (08-15, recover_to_plant
        family 2). Lazy-loads the npz named by cfg
        goal.recover_start_bank (key ``q_rad``, shape (K,18)); caches
        None when unset."""
        if hasattr(self, "_rec_bank_cache"):
            return self._rec_bank_cache
        path = cfg_get(self.cfg, "goal", "recover_start_bank",
                       default=None)
        bank = None
        if path:
            arr, npz = _load_robot_abs_q_npz(
                str(path), source="recover_start_bank")
            npz.close()
            if arr.ndim != 2 or arr.shape[1] != N_JOINTS or len(arr) == 0:
                raise ValueError(
                    f"recover_start_bank {path}: expected "
                    f"(K,{N_JOINTS}) q_rad, got {arr.shape}")
            bank = arr
        self._rec_bank_cache = bank
        return bank

    def _rise_start_bank(self) -> np.ndarray | None:
        """Harvested settled lower-endpoint poses (08-14, post-lower
        rise exposure — SESSION_BULK_GATE's named boundary). Lazy-loads
        the npz named by cfg goal.rise_start_bank (key ``q_rad``, shape
        (K,18)); caches None when unset so the legacy path costs one
        attribute check."""
        if hasattr(self, "_rise_bank_cache"):
            return self._rise_bank_cache
        path = cfg_get(self.cfg, "goal", "rise_start_bank", default=None)
        bank = None
        if path:
            arr, npz = _load_robot_abs_q_npz(
                str(path), source="rise_start_bank")
            if arr.ndim != 2 or arr.shape[1] != N_JOINTS or len(arr) == 0:
                raise ValueError(
                    f"rise_start_bank {path}: expected (K,{N_JOINTS}) "
                    f"q_rad, got {arr.shape}")
            bank = arr
            npz.close()
        self._rise_bank_cache = bank
        return bank

    def _lower_start_bank(self) -> np.ndarray | None:
        """Harvested composed-session lower-entry poses (2026-09-23,
        goal.lower_start_bank/lower_start_bank_frac; same lazy-cache
        contract as _rise_start_bank)."""
        if hasattr(self, "_lower_bank_cache"):
            return self._lower_bank_cache
        path = cfg_get(self.cfg, "goal", "lower_start_bank", default=None)
        bank, qvel_bank = None, None
        if path:
            arr, npz = _load_robot_abs_q_npz(
                str(path), source="lower_start_bank")
            if arr.ndim != 2 or arr.shape[1] != N_JOINTS or len(arr) == 0:
                raise ValueError(
                    f"lower_start_bank {path}: expected (K,{N_JOINTS}) "
                    f"q_rad, got {arr.shape}")
            bank = arr
            # v2 bank (goal.bank_qvel_restore, 2026-09-23 ~19:5x):
            # MuJoCo-native qvel per row, same order as q_rad -- NOT
            # under the robot_abs contract (velocity isn't a hardware
            # deployment artifact), so read directly with no frame
            # check. Absent on v1 banks -> None, same off-by-default
            # bit-exact contract as everything else here.
            if "qvel_mujoco" in npz.files:
                qvel_bank = np.asarray(npz["qvel_mujoco"], dtype=float)
                if qvel_bank.shape != bank.shape:
                    npz.close()
                    raise ValueError(
                        f"lower_start_bank {path}: qvel_mujoco shape "
                        f"{qvel_bank.shape} != q_rad shape {bank.shape}")
            npz.close()
        self._lower_bank_cache = bank
        self._lower_bank_qvel_cache = qvel_bank
        return bank

    def _lower_start_bank_qvel(self) -> np.ndarray | None:
        """Companion qvel array for _lower_start_bank (None if the
        configured bank predates goal.bank_qvel_restore or none is
        configured); relies on _lower_start_bank having populated the
        cache (same lazy-load call site pattern used everywhere else
        in this file)."""
        self._lower_start_bank()
        return self._lower_bank_qvel_cache

    def _walk_entry_bank(self) -> np.ndarray | None:
        """Harvested composed-session walk-entry poses (2026-09-23,
        goal.walk_entry_bank/walk_entry_bank_frac; same lazy-cache
        contract as _rise_start_bank/_lower_start_bank -- the walk-
        mode analogue, reintroduced 2026-09-23 ~19:5x alongside
        goal.bank_qvel_restore. NOT the same mechanism as the v1
        walk_entry_bank closed the same day (CURRENT_TRUTHS ~19:3x):
        that one only ever varied the injected POSITION; this one is
        rebuilt to always carry the matching momentum too."""
        if hasattr(self, "_walk_bank_cache"):
            return self._walk_bank_cache
        path = cfg_get(self.cfg, "goal", "walk_entry_bank", default=None)
        bank, qvel_bank = None, None
        if path:
            arr, npz = _load_robot_abs_q_npz(
                str(path), source="walk_entry_bank")
            if arr.ndim != 2 or arr.shape[1] != N_JOINTS or len(arr) == 0:
                raise ValueError(
                    f"walk_entry_bank {path}: expected (K,{N_JOINTS}) "
                    f"q_rad, got {arr.shape}")
            bank = arr
            if "qvel_mujoco" in npz.files:
                qvel_bank = np.asarray(npz["qvel_mujoco"], dtype=float)
                if qvel_bank.shape != bank.shape:
                    npz.close()
                    raise ValueError(
                        f"walk_entry_bank {path}: qvel_mujoco shape "
                        f"{qvel_bank.shape} != q_rad shape {bank.shape}")
            npz.close()
        self._walk_bank_cache = bank
        self._walk_bank_qvel_cache = qvel_bank
        return bank

    def _walk_entry_bank_qvel(self) -> np.ndarray | None:
        """Companion qvel array for _walk_entry_bank (see
        _lower_start_bank_qvel)."""
        self._walk_entry_bank()
        return self._walk_bank_qvel_cache

    def _apply_bank_qvel_handoff(self) -> None:
        """Composed-session momentum restore (2026-09-23 standwalk
        ~19:5x): the velocity-preserving companion to goal.
        rise_start_bank/goal.lower_start_bank/goal.walk_entry_bank.

        Those banks (and the now-CLOSED walk_entry_bank_frac /
        3-for-3-refuted lower_start_bank_frac doses, CURRENT_TRUTHS
        2026-09-23 ~19:3x) matched only the joint ANGLE of a real
        rise->walk / walk->lower composed-session handoff. Two things
        then discarded the real momentum a moving specialist actually
        carries at that instant: the bank stored q_rad alone (no
        qvel), and even if it had, the standard ~1.2s static PD
        settle every reset() runs (_place_at_plant + 2x _settle)
        drives velocity back toward zero regardless of what pose it
        is targeting -- so exposure to the exact harvested pose still
        never taught a specialist to handle the live momentum a real
        handoff hands it.

        Called from reset() at the SAME insertion point as
        _apply_walk_reverse_handoff (right after the ordinary settle/
        q_nom capture, before _reset_finalize captures episode
        references) -- so this restore is invisible to the episode's
        own bookkeeping, exactly like that mechanism. Sets
        data.qvel[_vadr] to the exact recorded row for the bank pose
        this episode actually drew (already MuJoCo-native, no frame
        conversion needed) plus a small multiplicative jitter, then
        mj_forward()s so contact/derived quantities are consistent.

        Default OFF (goal.bank_qvel_restore<=0): no-op even when a
        v2 bank with qvel is configured, so every existing
        rise_start_bank/lower_start_bank run stays bit-exact. Also a
        no-op when the episode didn't draw a bank start at all, or
        drew one from a v1 (position-only) bank.
        """
        qvel = self._pending_bank_qvel_mj
        self._pending_bank_qvel_mj = None
        if qvel is None:
            return
        if float(cfg_get(self.cfg, "goal", "bank_qvel_restore",
                         default=0.0)) <= 0.0:
            return
        qvel = np.asarray(qvel, dtype=float)
        jitter_frac = float(cfg_get(self.cfg, "goal",
                                    "bank_qvel_jitter_frac",
                                    default=0.15))
        if jitter_frac < 0.0:
            raise ValueError("goal.bank_qvel_jitter_frac must be >= 0")
        if jitter_frac > 0.0:
            # Multiplicative jitter with a small additive floor (rad/s)
            # so near-zero-velocity joints in the harvested row still
            # get SOME diversity across episodes, not a repeated exact
            # zero -- same rationale as the position bank's own +-2deg
            # jitter.
            scale = np.maximum(np.abs(qvel), 0.05)
            qvel = qvel + self.rng.normal(0.0, jitter_frac, N_JOINTS) * scale
        self.data.qvel[self._vadr] = qvel
        self._mujoco.mj_forward(self.model, self.data)

    def _place_at_plant(self, q_rad: np.ndarray) -> None:
        """Set qpos to ``q_rad`` with the chassis at foot-contact height."""
        import mujoco_prototype as MP
        mujoco = self._mujoco
        feet = fk_all_feet(self._mujoco_to_logical_q(q_rad))
        foot_drop = float(np.min(feet[:, 2]))  # most negative = lowest foot
        base_z = MP.YAW_OUTPUT_HEIGHT - foot_drop + MP.FOOT_R + 0.002

        mujoco.mj_resetData(self.model, self.data)
        self.data.qpos[:3] = (0.0, 0.0, base_z)
        self.data.qpos[3:7] = (1.0, 0.0, 0.0, 0.0)
        self.data.qpos[self._qadr] = q_rad
        self.data.qvel[:] = 0.0
        self.data.ctrl[:] = 0.0
        self.data.ctrl[self._pos_act] = q_rad
        mujoco.mj_forward(self.model, self.data)
        if self._model_source != "primitive":
            # The analytic base_z above uses the LEGACY kinematic constants
            # (body_ik FK + YAW_OUTPUT_HEIGHT); on the mesh-family models
            # (real hip rise, mid-plane foot line) it lands ~60 mm high and
            # the spawn would free-fall through the settle. Re-place from
            # the model's own geometry: lowest collidable point 2 mm above
            # the ground plane (legacy path untouched — bit-exact).
            low = lowest_collidable_z(self.model, self.data)
            self.data.qpos[2] += 0.002 - low
            mujoco.mj_forward(self.model, self.data)
        # Foot-height placement assumes feet are the lowest points. At the
        # zero pose (legs straight out) the yaw-servo belly boxes are lower
        # than the feet and would start inside the floor — lift until
        # nothing penetrates, then the settle drops it onto the belly.
        for _ in range(40):
            worst = 0.0
            for ci in range(self.data.ncon):
                worst = min(worst, float(self.data.contact[ci].dist))
            if worst > -1e-4:
                break
            self.data.qpos[2] += -worst + 0.001
            mujoco.mj_forward(self.model, self.data)
        # RECOVER "flip" spawn (08-15): consume-once pending base
        # orientation — rotate, lift clear of the floor, and let the
        # caller's settle choreography drop it however it lands
        # (side/back/upside-down). Both reset paths (C reset() and the
        # MJX batched choreography's place_env) run through here, so
        # one hook covers both. None everywhere outside the recover
        # mode's flip kind — every legacy placement is bit-exact.
        flip = getattr(self, "_flip_spawn_pending", None)
        if flip is not None:
            self._flip_spawn_pending = None
            self.data.qpos[3:7] = flip
            self.data.qpos[2] += 0.03
            mujoco.mj_forward(self.model, self.data)
            for _ in range(40):
                worst = 0.0
                for ci in range(self.data.ncon):
                    worst = min(worst, float(self.data.contact[ci].dist))
                if worst > -1e-4:
                    break
                self.data.qpos[2] += -worst + 0.001
                mujoco.mj_forward(self.model, self.data)

    # ------------------------------------------------------------------
    # gym API
    # ------------------------------------------------------------------

    def _reset_begin(self, seed: int | None = None) -> np.ndarray:
        """Pre-physics half of reset: bookkeeping, this episode's DR
        sample, goal sample, and the start pose. Touches NO model or
        physics state, so the batched MJX vec env can drive it for a
        shim env and run the settle choreography itself. Returns
        q_start (rad, 18). RNG draw order (DR sample, then goal) is
        identical to the historical inline code.
        """
        if seed is not None:
            self.rng = np.random.default_rng(seed)
        self._episode += 1
        self._step_i = 0
        self._prev_action[:] = 0.0
        self._prev_prev_action = np.zeros(self.n_act, dtype=float)
        self.safety.clear_estop()
        self._tipped_applied = False
        self._flip_spawn_pending = None
        # Composed-session momentum-restore handoff (2026-09-23,
        # standwalk ~19:5x — see _apply_bank_qvel_handoff): cleared
        # every episode so a bank draw from a PRIOR episode can never
        # leak into one that didn't itself draw a bank start this
        # time; only spawn_pose_q_start's own rise_bank/lower_bank/
        # walk_entry_bank branches (balance_reset.py) set it.
        self._pending_bank_qvel_mj = None

        self._ep_rand = (self.randomizer.sample(self.rng)
                         if self.randomizer is not None else None)
        self._reset_start_offset_rad = self._sample_reset_start_offset_rad()
        if self._struct_comp is not None:
            dr = (getattr(self.randomizer, "scale", 1.0)
                  if self.randomizer is not None else 0.0)
            self._struct_comp_k = self._struct_comp.sample(
                self.rng, scale=dr)
        else:
            self._struct_comp_k = None

        reset_gravity_ease(self)

        start_at = reset_mode_seq_and_goal(self)
        # Reference state initialization (RSI, DeepMimic-style; operator
        # 08-10 late). The 08-10 forensic ladder (score1 -> scoreref1 ->
        # -dr0 -> -dr0-lowlr -> -dr0-riseonly) proved the rise reward
        # orders correctly even under full exploration noise (noisy
        # replay +357 vs cheats < 0) yet training NEVER visits the paid
        # states: pricing, DR, LR, mode interference and noise were each
        # exonerated by a controlled run, leaving pure exploration - the
        # gradient cannot cross from "lying at the ref start" to "the
        # full rise" because nothing between pays. RSI closes it by
        # SPAWNING rise episodes on the demonstrated path at a random
        # phase (belly curl through ~90% of the ramp), so rollouts
        # experience the paid states directly and learning can proceed
        # backward along the path. cfg goal.rise_rsi_frac in [0,1]
        # (default 0 = legacy exact; no rng draw when off), needs
        # reward.rise_ref_path. The settle choreography (incl. the limp
        # sag) runs unchanged; _reset_finalize re-aligns the reference
        # clock to the nearest path point of the pose that actually
        # settled, so the mechanism is robust to sag on every impl.
        self._rsi_pending = False
        self._rsi_ref_tick0: int | None = None
        if (self._goal_traj is not None
                and getattr(self._goal_traj, "mode", "") == "rise"
                # Bank episodes ARE the post-lower exposure — RSI must
                # not override them (rise_bank never occurs unless
                # goal.rise_start_bank is configured, so the legacy
                # rng stream is untouched when the feature is off).
                and getattr(self._goal_traj, "start_at", "")
                != "rise_bank"):
            rsi_f = float(cfg_get(self.cfg, "goal", "rise_rsi_frac",
                                  default=0.0))
            rsi_ref = cfg_get(self.cfg, "reward", "rise_ref_path",
                              default=None)
            if rsi_f > 0.0 and rsi_ref:
                ref = load_rise_ref(str(rsi_ref))
                # "h" (per-tick height) only exists in newer extracts;
                # without it the remaining-rise schedule can't be built.
                if "h" in ref and self.rng.random() < rsi_f:
                    n, i0 = len(ref["q"]), int(ref["ramp_i0"])
                    j = int(self.rng.integers(
                        0, i0 + int(0.9 * (n - 1 - i0))))
                    q_rsi = ref["q"][j] + self.rng.uniform(
                        -2.0, 2.0, N_JOINTS) * DEG2RAD
                    self._rsi_pending = True
                    return self._logical_to_mujoco_q(
                        self._clip_to_joint_limits(q_rsi))
        # RECOVER RSI (08-16, zero-family mechanism fix): spawn a
        # flagged recover episode ON the demonstrated belly->plant
        # path instead of its family pose. Root cause (cw-recover-any8
        # /any9, hw track): the recovery ladder's partial_* rungs are
        # LINEAR curls (f * q_crouch), not states on the executable
        # rise trajectory, so a policy stuck at the zero (belly-flat)
        # family never PRACTICES from mid-rise states — the exact
        # exploration gap the rise-mode RSI above closed for the rise
        # task (row-range formula reused: belly curl through ~90% of
        # the ramp, never the free-success top). The flag is set ONLY
        # by walk_task._sample_recover on NATURALLY drawn kinds
        # (goal.recover_rsi_frac/_kinds, default off); forced CERT/
        # eval kinds never carry it, so certification stays pure by
        # construction. The settle choreography (incl. limp sag) runs
        # unchanged — same sag-robustness contract as rise RSI. Level
        # tilt anchoring matches the recover "any" branch below.
        if (self._goal_traj is not None
                and getattr(self._goal_traj, "mode", "") == "recover"
                and getattr(self._goal_traj, "recover_rsi", False)):
            rsi_ref = cfg_get(self.cfg, "reward", "rise_ref_path",
                              default=None)
            if not rsi_ref:
                raise ValueError("goal.recover_rsi_frac needs "
                                 "reward.rise_ref_path")
            ref = load_rise_ref(str(rsi_ref))
            if "h" not in ref:
                raise ValueError("goal.recover_rsi_frac needs a rise "
                                 "reference with per-tick heights "
                                 "(re-extract with extract_rise_ref)")
            n, i0 = len(ref["q"]), int(ref["ramp_i0"])
            j = int(self.rng.integers(0, i0 + int(0.9 * (n - 1 - i0))))
            q_rsi = ref["q"][j] + self.rng.uniform(
                -2.0, 2.0, N_JOINTS) * DEG2RAD
            if self._ep_rand is not None:
                q_rsi = q_rsi + self._ep_rand.start_offset_rad
            self._tipped_applied = True
            return self._logical_to_mujoco_q(
                self._clip_to_joint_limits(q_rsi))
        q_start = spawn_pose_q_start(self, start_at)
        return self._logical_to_mujoco_q(q_start)

    def reset(self, *, seed: int | None = None, options: dict | None = None):
        del options
        q_start = self._reset_begin(seed)

        # Restore pristine model, then apply this episode's randomization.
        self.model.body_mass[:] = self._base_body_mass
        self.model.body_inertia[:] = self._base_body_inertia
        self.model.body_ipos[:] = self._base_body_ipos
        self.model.body_pos[:] = self._base_body_pos
        self.model.geom_pos[:] = self._base_geom_pos
        self.model.site_pos[:] = self._base_site_pos
        self.model.geom_friction[:] = self._base_geom_friction
        self.model.geom_solref[:] = self._base_geom_solref
        self.model.opt.gravity[:] = self._base_gravity
        if self._ep_rand is not None:
            self._ep_rand.apply_to_model(
                self.model, chassis_bid=self._chassis_bid)
            apply_params_to_model(
                self.model, self.params,
                kp_scale=self._ep_rand.kp_scale,
                kv_scale=self._ep_rand.kv_scale,
                torque_scale=self._ep_rand.torque_scale)
            # dr.fault_*: no-op unless this episode drew a fault (must
            # run AFTER apply_params_to_model, which SETS these rows).
            self._ep_rand.apply_fault_to_model(self.model)
            # dr.leg_torque_scale / struct overlay per-leg torque
            # asymmetry: no-op unless this episode carries non-unit
            # scales (also must run AFTER apply_params_to_model).
            self._ep_rand.apply_asym_to_model(self.model)
        else:
            apply_params_to_model(self.model, self.params)
        # Stick-slip baseline: capture THIS episode's post-DR (static
        # foot_friction_scale-dosed) foot coefficients as the KINETIC/
        # baseline value the per-tick mechanism ramps away from -- must
        # run AFTER apply_to_model (which sets the static per-foot
        # asymmetry) and BEFORE anything reads geom_friction below (the
        # slip-settle override restores from ``fr`` afterward, not from
        # this baseline, so order there is unaffected).
        self._stickslip_base_mu = self.model.geom_friction[
            self._stickslip_foot_gids, 0].copy()
        er_ss = self._ep_rand
        self._stickslip_active = (
            er_ss is not None and bool(np.any(er_ss.foot_stickslip_gain > 0.0)))
        self._stickslip_gain = (
            er_ss.foot_stickslip_gain.copy() if self._stickslip_active
            else np.zeros(6, dtype=float))
        self._stickslip_vel_ref_mps = (
            float(er_ss.foot_stickslip_vel_ref_mps)
            if er_ss is not None else 0.02)
        self._stickslip_prev_xy = None
        # Transient foot-catch/stumble event (dr.foot_catch_force_n):
        # only claim the pad-body xfrc rows for episodes that actually
        # drew a nonzero magnitude this episode (same "owns_row"
        # discipline as _ext_push_force_n) -- assume every foot starts
        # PLANTED (matches every episode's settled start pose) so the
        # very first liftoff of the episode can still trigger.
        er_fc = self._ep_rand
        self._foot_catch_owns_row = (
            er_fc is not None and bool(np.any(er_fc.foot_catch_force_n != 0.0)))
        if self._foot_catch_owns_row and any(b < 0 for b in self._pad_bids):
            # Fail loud, not silent: xfrc_applied[-1] would land on an
            # arbitrary body, not a real foot pad. Both current model
            # families (mesh and legacy primitive) define named
            # "L{i}_pad" bodies, so this should never fire in practice
            # -- defensive only, for a future model variant that drops
            # the pad body.
            raise ValueError(
                "dr.foot_catch_force_n needs L{i}_pad bodies -- "
                "model has none")
        self._foot_catch_prev_touch = np.ones(6, dtype=bool)
        self._foot_catch_end_s = np.full(6, -1.0, dtype=float)
        self._foot_catch_cooldown_until_s = np.zeros(6, dtype=float)
        self._apply_struct_compliance_to_model(self.model)
        if self._ease_g != 1.0:
            # Physics-easing fallback for randomize=False private-model
            # envs (_reset_begin); with DR on the scale already lives in
            # _ep_rand.gravity_vec and _ease_g stays 1.0.
            self.model.opt.gravity[:] = (
                self.model.opt.gravity * self._ease_g)

        # Mode-sequencing canonical frames (goal.mode_seq): capture the
        # settled plant/belly reference frames on THIS episode's model
        # (DR applied above) before the episode's own placement — the
        # probe physics is wiped by the placement + settle below, so the
        # episode start is untouched. Cached across resets when the
        # model cannot change (no DR, no easing); recomputed per episode
        # otherwise.
        if ((float(cfg_get(self.cfg, "goal", "mode_seq",
                           default=0.0)) > 0.0
             or float(cfg_get(self.cfg, "goal", "mode_seq_stance",
                              default=0.0)) > 0.0)
                and (self._seq_frames is None
                     or self._ep_rand is not None
                     or self._ease_g != 1.0)):
            self._seq_capture_frames()

        self._place_at_plant(q_start)
        er = self._ep_rand
        self._profile = ServoProfile(
            self.params, q_start,
            latency_scale=1.0 if er is None else er.latency_scale,
            deadband_scale=1.0 if er is None else er.deadband_scale,
            vel_scale=1.0 if er is None else er.vel_scale,
            latency_load_gain=None if er is None else er.latency_load_gain,
            latency_load_ref_nm=(
                1.2 if er is None else er.latency_load_ref_nm),
        )
        if er is not None and np.any(er.joint_backlash_gap_rad > 0.0):
            self._backlash = JointBacklash(
                er.joint_backlash_gap_rad,
                load_gain=er.joint_backlash_load_gain,
                load_ref_nm=er.joint_backlash_load_ref_nm)
            self._backlash.reset(q_start)
        else:
            self._backlash = None
        self._backlash_prev_force[:] = 0.0
        self._cmd = self._mujoco_to_logical_q(q_start)
        # Settle with slippery feet AND limp servos first: when a
        # human sets the robot down (torque off), feet micro-slip and
        # joints sag until the structure reaches a passive
        # equilibrium — otherwise randomized geometry + pinned
        # contacts leave the legs isometrically preloaded at 2-3 A
        # from step 0.
        fr = self.model.geom_friction[:, 0].copy()
        self.model.geom_friction[:, 0] = self.SLIP_MU
        self._settle(0.4)      # stiff: reach the commanded pose
        self._settle(0.5, limp=True)  # limp: bleed contact preload
        self.model.geom_friction[:, 0] = fr

        # Hold-current semantics, same as the hardware env: nominal is the
        # pose the robot actually SETTLED at (however badly it was placed),
        # not the ideal plant. Capturing the PASSIVE equilibrium means
        # "hold this pose" needs ~zero torque — like hardware, where
        # q_nom is read from encoders while the servos are unloaded.
        q_nom_mujoco = self.data.qpos[self._qadr].copy()
        self._q_nom = self._mujoco_to_logical_q(q_nom_mujoco)
        self._profile.reset(q_nom_mujoco)
        self._cmd = self._q_nom.copy()
        self._settle(0.3)
        self._apply_walk_reverse_handoff()
        self._apply_bank_qvel_handoff()
        obs, info = self._reset_finalize()
        probe_n = self._reset_history_probe_steps()
        for _ in range(probe_n):
            self._advance()
            obs = self._reset_history_probe_obs()
        if probe_n:
            info["reset_history_probe_ticks"] = probe_n
            info["reset_history_probe_s"] = probe_n * self.dt
        return obs, info

    def _reset_finalize(self):
        """Post-settle half of reset: episode references, filter resets,
        first state read, first obs. Reads physics only through
        ``self.data`` (the vec env feeds a shim env a batched-tick data
        view), with ``self._q_nom`` already captured by the caller.
        Returns the (obs, info) reset tuple.
        """
        # Curl channel target: the ideal plant footprint (foot anchors can
        # slide from wherever they started toward it — required to stand
        # up from the zero pose, useful to fix a badly-placed leg).
        self.ik.reset(
            self._q_nom,
            plant_q_rad=self._plant_deg * DEG2RAD,
        )
        self.safety.set_nominal(self._q_nom)
        self._cur_filt = None
        self._height_vel_est = None
        self._height_vel_mps = 0.0
        self._trip_cur_filt = None
        self._torque_debt = None
        self._prev_current_rate = None
        self._imu_prev_v = None
        self._imu_f_accum[:] = 0.0
        self._imu_f_n = 0
        self._gyro_accum[:] = 0.0
        self._gyro_n = 0
        self._att_rp = None
        self._cmd_dropping = False
        self._imu_dropping = False
        self._imu_drop_dead = False
        self._imu_hold_rp = None
        self._imu_hold_gyro = None
        if self._deployed_transport is not None:
            self._deployed_transport.reset()
        # Height anchor: goal height refs (rise) are relative to wherever
        # the body actually settled, same convention as the tilt refs.
        self._z0 = float(self.data.xpos[self._chassis_bid, 2])
        # Grounded pad heights at episode start. Stance episodes begin at
        # the plant with all six feet loaded (verified by zero-action
        # probe), so this is the "foot down" z for each pad.
        self._pad_z_ref = np.array(
            [float(self.data.xpos[b, 2]) if b >= 0 else 0.0
             for b in self._pad_bids])
        # Transition-drag bookkeeping (operator 08-11 night: the robot
        # scrapes its feet across the floor during stand/sit). Per-foot
        # previous contact + XY for the trans_drag_mm metric in
        # _step_finish; snapshot via mjx_host.SNAP_ATTRS (pool-restore
        # lesson, commit 65edba7).
        self._tdrag_prev_xy = [None] * 6
        self._tdrag_prev_on = [False] * 6
        # HOLD-mode min-foot-load termination bookkeeping
        # (safety.hold_min_load_terminate_s, standwalk mesh2 rung-6):
        # own EMA of the worst (min-over-feet) touch force this
        # episode, and seconds it has stayed below the floor,
        # consecutively — same lifecycle/EMA pattern as walk_task's
        # _walk_qvel_ema/_walk_idle_low_s, but universal here (hold
        # mode is available on every task class, not just
        # SimHexapodJointWalkEnv) — snapshot via mjx_host.SNAP_ATTRS.
        self._hold_minload_ema = 0.0
        self._hold_minload_low_s = 0.0
        # Continuity variant (safety.hold_min_load_ema_continuous,
        # 09-04): seed the EMA from the MEASURED min-over-feet force at
        # the settled spawn instead of 0.0, so the very first ticks
        # (and any price built on the EMA) read the true planted state
        # rather than a zero-init charging artifact. Default off =
        # legacy 0.0 init, bit-exact.
        if (float(cfg_get(self.cfg, "safety",
                          "hold_min_load_ema_continuous",
                          default=0.0)) > 0.0
                and self._pad_z_ref is not None):
            self._hold_minload_ema = self._minload_min_force_now(
                float(cfg_get(self.cfg, "safety",
                              "hold_min_load_terminate_n", default=0.3)))
        # Per-episode cache: first charged tick of the terminal
        # end-posture window (computed lazily from the goal schedule).
        self._end_posture_from = None
        # RSI episodes: align the reference clock to the path point the
        # robot ACTUALLY settled at (the limp-settle stage sags mid-rise
        # poses; nearest-neighbor re-alignment makes the mechanism
        # sag-robust on every impl), then rewrite the height schedule to
        # command the REMAINING rise from the settled spawn — heights
        # stay relative to _z0 like every other episode's.
        if getattr(self, "_rsi_pending", False) and self._goal_traj is not None:
            ref = load_rise_ref(str(cfg_get(
                self.cfg, "reward", "rise_ref_path", default="")))
            q_set = self._mujoco_to_logical_q(
                self.data.qpos[self._qadr])
            rms = np.sqrt(((ref["q"] - q_set[None, :]) ** 2).mean(axis=1))
            j0 = int(np.argmin(rms))
            self._rsi_ref_tick0 = j0
            # STALE-REFERENCE-HEIGHT FIX (08-22, root-caused from
            # cw-stand-footlow2-plant150-2c-heightfix's RSI-start
            # height_err pinned at 22-29mm after 10M extra steps of
            # training, zero movement — the pre-registered "stays
            # pinned regardless of budget" FAIL branch). ref["h"] is
            # the npz's OWN recorded per-tick chassis height, extracted
            # before the tibia-150 geometry change; replaying the SAME
            # q_rad trajectory on the CURRENT sim settles ~21mm higher
            # (measured h_rel=131.94mm vs the npz's stored h_rel_end_m
            # =110.96mm — CURRENT_TRUTHS rise_valid_plant finding).
            # The old code anchored the RSI episode's ABSOLUTE height
            # target to this stale h_end, silently training every RSI
            # spawn to a target ~21mm below the corrected
            # goal.rise_height_mm window — a genuine reward<->eval
            # misalignment, not undertraining. Fix: anchor the
            # ABSOLUTE target to this episode's own already-sampled,
            # CURRENT-cfg height (self._goal_traj.height[-1], drawn
            # from goal.rise_height_mm before this block runs) and use
            # the reference array ONLY for the FRACTIONAL progress at
            # the spawn point (robust to a uniform/stale h-scale
            # mismatch; the q_rad geometry, and hence the progress
            # ordering along the path, is unaffected by tibia length).
            h_end_ref = float(ref["h"][-1])
            h_target = float(np.asarray(self._goal_traj.height)[-1])
            frac_done = float(ref["h"][j0]) / max(h_end_ref, 1e-6)
            frac_done = min(max(frac_done, 0.0), 1.0)
            h_left = max(h_target * (1.0 - frac_done), 0.002)
            ramp_s = float(cfg_get(self.cfg, "goal", "rise_ramp_s",
                                   default=6.0))
            n_ramp = max(int(round(ramp_s * min(h_left / max(h_target, 1e-3),
                                                1.0) / self.dt)), 3)
            n_ep = len(np.asarray(self._goal_traj.height))
            self._goal_traj.height = h_left * np.clip(
                np.arange(n_ep, dtype=float) / n_ramp, 0.0, 1.0)
        # Staged height scores (rise/raise/lower): potential-based
        # progress on |height_err| plus one-time milestone bonuses at
        # fractions of the episode's height target. Sim-only (privileged
        # body height). SIGNED: lower episodes have a negative target and
        # milestones fire on the way down.
        if self._goal_traj is not None:
            h = np.asarray(self._goal_traj.height)
            self._h_target = float(h[int(np.argmax(np.abs(h)))])
        else:
            self._h_target = 0.0
        self._h_milestones: set[float] = set()
        self._prev_h_err_abs = 0.0
        # Stand-score ratchet baseline (reward.rise_score_income): seeded
        # with the episode's FIRST score so crouch/near-plant starts don't
        # collect their starting posture as free income.
        self._score_best: float | None = None
        # Depth-ratchet baseline (reward.lower_score_prog, 2026-09-13):
        # same convention as _score_best above, just for the lower-side
        # `lower_depth_frac` ratchet — seeded on first read so a
        # mid-descent start (lowerpartial) doesn't collect its starting
        # depth as free income.
        self._lower_score_best: float | None = None
        # Feet-under-body ("curl") scores, rise episodes only: mean XY
        # distance from each foot to its plant-footprint anchor. Curling
        # changes NO height term (belly stays down), so without this the
        # one step that makes standing possible has zero gradient.
        self._is_rise = (self._goal_traj is not None
                         and getattr(self._goal_traj, "mode", "") == "rise")
        # GETUP (recover→stand→walk, 08-11) episode state: mode flag +
        # the staged-progress ratchet baseline. The baseline is seeded
        # on the FIRST post-settle tick (walk_task._post_step) so the
        # spawn posture is never income — same convention as
        # _score_best. Both attrs ride mjx_host.SNAP_ATTRS.
        self._is_getup = (self._goal_traj is not None
                          and getattr(self._goal_traj, "mode", "")
                          == "getup")
        self._getup_best = None
        # RECOVER (recover_to_plant, 08-15 directive) episode state:
        # mode flag, the PBRS previous-potential (seeded on the first
        # post-settle tick — spawn posture is never income), and the
        # continuous success-hold counter. All three ride
        # mjx_host.SNAP_ATTRS (pool-restored episodes must not inherit
        # another episode's potential baseline or hold streak).
        self._is_recover = (self._goal_traj is not None
                            and getattr(self._goal_traj, "mode", "")
                            == "recover")
        self._rec_phi_prev = None
        self._rec_hold_n = 0
        # HOLD/TRACK BC-anchor eligibility (RL_PLAN queue 2.3, 08-11:
        # the rise lever repeated after both hold pricing levers — hard
        # zero, then the fade — moved the pricing but never reached a
        # quiet plant). Unlike rise, hold/track have no moving reference
        # to chase; the natural supervised target is simply the pose the
        # episode actually settled at (self._q_nom, captured post-settle
        # in reset() — "trivially available", RISE.md). Emission happens
        # in _step_finish once self._q_nom exists.
        self._is_hold_bc = (self._goal_traj is not None
                            and getattr(self._goal_traj, "mode", "")
                            in ("hold", "track"))
        # LOWER BC-anchor eligibility (08-11, anchorstate2 follow-up):
        # the lower bank's strict xfail documents that one-leg-aloft
        # keeps ~85% of the honest lower return (rise_posture_gate
        # prices a lifted leg at pf=5/6) — the incentive behind the
        # deployed specialist's 62-99 mm dangling foot AND the prime
        # suspect for the six-run leg-1 hold park (pricing changes
        # moved nothing all campaign; anchor supervision is the only
        # lever that moved the park fingerprint). Target emission in
        # _step_finish; gated by train.bc_anchor_lower.
        self._is_lower_bc = (self._goal_traj is not None
                             and getattr(self._goal_traj, "mode", "")
                             == "lower")
        # WALK BC-anchor reference (RL_PLAN queue 2.1 follow-up, 08-11:
        # probe_walk_income exonerated the trans1 stack's pricing —
        # honest gait out-earns every degenerate 2-4x in all four
        # directions at DR 0 AND 0.5, and the collapsed trans1/mirror2
        # checkpoints earn BELOW a freeze — so the paddle/sacrifice
        # attractors are optimization failures, not paid basins. Same
        # signature as rise/hold: nothing tells a churning leg WHICH
        # WAY to move. Third application of the proven lever: supervise
        # walk-tick actions toward the command-conditioned scripted
        # TripodGait — the exact open-loop gait that walks/crabs/turns
        # the REAL robot (tape-measured 08-10). Per-episode instance,
        # phase state lives on it, so it MUST ride SNAP_ATTRS
        # (pool-restore lesson, commit 65edba7).
        # 08-12 follow-up (cw-arch-gru-anchor1/scratch-anchor1): both
        # arms reproduce the twice-closed walk-freeze/paddle failure
        # when walk ticks are anchored ALONGSIDE rise/hold/lower on a
        # GRU, while rise/hold/lower gains held clean — the anchor
        # protects stance skills but still fights locomotion. Gated by
        # train.bc_anchor_walk so a future arm can anchor stance only.
        # Default 1.0 (on) preserves every existing config bit-exact;
        # only an explicit bc_anchor_walk=0 disables this block.
        self._walk_bc_gait = None
        self._walk_bc_gait_alt = None
        self._walk_bc_t = 0.0
        if (self._goal_traj is not None
                and getattr(self._goal_traj, "mode", "") == "walk"
                and ((float(cfg_get(self.cfg, "train", "bc_anchor_coef",
                                    default=0.0)) > 0.0
                      and float(cfg_get(self.cfg, "train", "bc_anchor_walk",
                                       default=1.0)) > 0.0)
                     # assistfade rung-3 residual fade (see _step_begin):
                     # needs the SAME command-conditioned teacher gait
                     # even with no BC loss at all (bc_anchor_coef=0).
                     or float(cfg_get(self.cfg, "goal",
                                      "walk_residual_gate",
                                      default=0.0)) > 0.0)):
            self._walk_bc_gait = self._make_walk_bc_gait()
            if float(cfg_get(
                    self.cfg, "train", "bc_anchor_multiteacher_blend",
                    default=0.0)) > 0.0:
                # PHASE-SCHEDULED MULTI-TEACHER (09-05): a SEPARATE
                # persistent gait object, queried once per combined
                # tick (never twice on the same tick against the
                # primary ``_walk_bc_gait``) so its own EMA velocity
                # smoothing (TripodGait._smoothed_command, tau=0.15)
                # tracks a stable vx=0 setpoint over time instead of
                # inheriting a stale dt=0 double-query artifact — see
                # test_multiteacher_alt_target_matches_pure_turn_
                # geometry's own regression history for why a same-
                # object double-query was refuted first.
                self._walk_bc_gait_alt = self._make_walk_bc_gait()
        # First ramp tick of a rise schedule (hold window ends here) —
        # the alignment anchor for the rise-reference tracking term:
        # references are recorded ramp-relative so episodes with
        # jittered hold lengths all join the same trajectory.
        self._rise_ramp_i0 = 0
        if self._is_rise:
            nz = np.nonzero(
                np.abs(np.asarray(self._goal_traj.height)) > 1e-12)[0]
            self._rise_ramp_i0 = int(nz[0]) if len(nz) else 0
        # First ramp tick of a lower schedule (hold window ends here) —
        # the `_lower_gate_tick` staged-descent gate's own hold-boundary,
        # same convention as `_rise_ramp_i0` just above (mirrored, not
        # shared, so a future rise-only change can't silently affect
        # lower's freeze window).
        self._lower_ramp_i0 = 0
        if self._is_lower_bc:
            nz = np.nonzero(
                np.abs(np.asarray(self._goal_traj.height)) > 1e-12)[0]
            self._lower_ramp_i0 = int(nz[0]) if len(nz) else 0
        # Mode-seq stand anchor (goal.mode_seq): the absolute chassis z
        # of the last COMMANDED standing height. A mid-sequence rise
        # aims back at this (re-anchored per switch — lesson 5 of the
        # transitions directive: start-relative refs are the #1 hidden-
        # state trap). Standing starts anchor at the settled height;
        # rise starts at the commanded top; a belly-start lower has no
        # known stand height until its first rise completes.
        if getattr(self, "_seq_plan", None) is not None:
            _m0 = getattr(self._goal_traj, "mode", "")
            if _m0 == "rise":
                self._seq_stand_z = self._z0 + self._h_target
            elif getattr(self._goal_traj, "start_at", "plant") != "zero":
                self._seq_stand_z = self._z0
            else:
                self._seq_stand_z = None
        self._plant_feet_xy = fk_all_feet(
            self._plant_deg * DEG2RAD)[:, :2]
        self._curl_dist_prev = self._curl_dist()
        self._curl_milestones: set[float] = set()
        self._rise_gate_freeze_ticks = 0
        self._lower_gate_freeze_ticks = 0
        self._pretuck_latched = False
        self._decouple_latched = False
        self._rise_h_prev = None
        self._state = self._read_state()
        self._rec_reset_height_mm = 0.0
        self._rec_reset_tilt_deg = 0.0
        self._rec_reset_min_load_n = 0.0
        self._rec_reset_pad_spread_mm = 0.0
        if self._is_recover:
            _rr, _rp = self._true_roll_pitch()
            _loads = [max(float(self.data.sensordata[a]), 0.0)
                      if a >= 0 else 0.0 for a in self._touch_adr]
            _pad_z = [float(self.data.xpos[b, 2]) for b in self._pad_bids]
            self._rec_reset_height_mm = float(
                self.data.xpos[self._chassis_bid, 2]) * 1000.0
            self._rec_reset_tilt_deg = max(abs(_rr), abs(_rp)) * RAD2DEG
            self._rec_reset_min_load_n = min(_loads)
            self._rec_reset_pad_spread_mm = (
                max(_pad_z) - min(_pad_z)) * 1000.0
        # Anchor trip, obs, and reward to the start attitude — mount bias
        # / slope isn't tipping, and goals mean "lean from here".
        self._tilt_ref0 = (self._state.imu_roll, self._state.imu_pitch)
        if getattr(self, "_tipped_applied", False):
            # Tipped-start episodes (dr.tipped_start_*) keep the
            # reference LEVEL: subtract the privileged true attitude so
            # only the IMU bias/mount part stays in the ref. The policy
            # then SEES the lean in obs and the attitude terms pay it
            # to level out — re-anchoring at the tip would train it to
            # HOLD the lean, the opposite of the point.
            t_roll, t_pitch = self._true_roll_pitch()
            self._tilt_ref0 = (self._state.imu_roll - t_roll,
                               self._state.imu_pitch - t_pitch)
        self.safety.set_tilt_reference(*self._tilt_ref0)
        # Settled lean relative to the episode tilt reference, captured
        # once post-settle (same tick _q_nom was captured). The
        # tilt-comp teacher's settle-lean source reads this
        # (train.bc_anchor_tilt_from_settle in _step_finish): a
        # per-episode CONSTANT, so the commanded counter-rotation does
        # not shrink as the student levels. Probe-measured 08-13
        # (probe_tilt_teacher): the current-lean proportional source
        # has a closed-loop fixed point at (L0+deadband)/2 (~4deg for
        # the ~6.5deg tipped spawns) — the teacher itself can never
        # demonstrate a <=3deg settle. In SNAP_ATTRS (pool-restore).
        self._settle_lean = (self._state.imu_roll - self._tilt_ref0[0],
                             self._state.imu_pitch - self._tilt_ref0[1])
        er = self._ep_rand
        info = {
            "episode": self._episode,
            "q_nominal_deg": (self._q_nom * RAD2DEG).tolist(),
            "roll_deg": self._state.imu_roll * RAD2DEG,
            "pitch_deg": self._state.imu_pitch * RAD2DEG,
            # Attitude relative to the episode's tilt reference — the
            # tipped-start recovery metric reads this (≈ true lean for
            # tipped episodes, where the ref stays level).
            "roll_rel_deg": (self._state.imu_roll
                             - self._tilt_ref0[0]) * RAD2DEG,
            "randomization": None if er is None else er.summary(),
        }
        if self._reset_start_offset_rad is not None:
            info["reset_start_jitter"] = {
                "bad_start_joints": list(self._reset_start_bad_joints),
                "start_offset_max_deg": round(float(np.max(
                    np.abs(self._reset_start_offset_rad))) * RAD2DEG, 1),
            }
        if self._struct_comp is not None and self._struct_comp_k is not None:
            info["struct_compliance"] = self._struct_comp.summary(
                self._struct_comp_k)
        if self._leg_mount_flex_addrs is not None:
            info["leg_mount_flex"] = leg_mount_flex_diagnostics(
                self.model, self.data)
        if self._joint_series_flex_addrs is not None:
            info["joint_series_flex"] = joint_series_flex_diagnostics(
                self.model, self.data)
        goal = self._current_goal()
        if goal is not None:
            info["goal_mode"] = self._goal_traj.mode
        return self._final_obs(
            build_obs(self.cfg, self._state, self._q_nom,
                      self._prev_action, goal=goal,
                      tilt_ref=self._tilt_ref0,
                      height_vel_mps=self._height_vel_mps), reset=True), info

    def _curl_dist(self) -> float:
        """Mean XY distance (m) from each foot to its plant anchor,
        computed in the body frame from true joint angles."""
        feet = fk_all_feet(self._mujoco_to_logical_q(
            self.data.qpos[self._qadr]))[:, :2]
        return float(np.mean(
            np.linalg.norm(feet - self._plant_feet_xy, axis=1)))

    def plant_report(self,
                     height_err_m: float | None = None
                     ) -> tuple[bool, dict]:
        """Live PLANT_SPEC check of the CURRENT tick (see valid_plant
        at module level — the shared stand criterion). The footprint
        term reuses _curl_dist (body-frame FK vs the plant anchors),
        so the identical criterion is available to the reward path,
        the eval harness, and the semantics bank."""
        if self._pad_z_ref is None or any(b < 0 for b in self._pad_bids):
            return False, {"error": "no pad clearance reference"}
        clear = [float(self.data.xpos[b, 2]) - self._pad_z_ref[i]
                 for i, b in enumerate(self._pad_bids)]
        feet_xy = np.array([self.data.xpos[b, :2]
                            for b in self._pad_bids])
        # Plant-validity strain gate: read the stall-sensitive current so a
        # strained plant is still rejected (default power model reads ~0 at
        # a stall); falls back to servo_current on hardware / legacy model.
        cur = over_current_reading(self._state)
        return valid_plant(
            pad_clear_m=clear, feet_xy=feet_xy,
            com_xy=self.data.subtree_com[0, :2],
            roll_rad=self._state.imu_roll,
            pitch_rad=self._state.imu_pitch,
            height_err_m=height_err_m,
            footprint_err_m=self._curl_dist(),
            max_current_a=(float(np.max(np.abs(cur)))
                           if cur is not None else None))

    # Goal-conditioned subclass hooks (base env: no goal, 47-dim obs).
    def _sample_goal(self):
        return None

    def _current_goal(self):
        if self._goal_traj is None:
            return None
        # Only one of the two freeze counters is ever nonzero for a
        # given episode (rise xor lower mode — see `_is_rise`/
        # `_is_lower_bc`), so a plain sum is a safe combination; each
        # gate only ever increments its own counter (`_rise_gate_tick`
        # / `_lower_gate_tick`).
        idx = (self._step_i
               - getattr(self, "_rise_gate_freeze_ticks", 0)
               - getattr(self, "_lower_gate_freeze_ticks", 0))
        return self._goal_traj.at(idx)

    def _rise_gate_tick(self) -> None:
        """Rise curl sub-goal (``goal.rise_curl_gate``, default 0 = OFF
        = bit-exact identical to every prior checkpoint): called once
        per real tick, right after ``self._step_i`` advances and
        before the tick's reward/obs goal is read.

        Escalation context (2026-09-13, `risecurlgate-s1-canary2m`
        CANARY FAIL-MECHANISM): TWO successive income-repricing levers
        on `reward_rise_score_prog` (current-headroom-gated, then
        curl-geometry-gated) both left the flat/bridge rise/det failing
        trajectories bit-identical to the ungated parent — pricing the
        SAME continuous height ramp differently never stopped the
        policy from attempting the sprawled straight push, because the
        height ref advances on a fixed WALL-CLOCK schedule
        (`goal.rise_ramp_s` after `goal.rise_hold_s`) regardless of
        whether the feet ever curled in. This is not another re-price:
        it makes the height ramp's own onset CONDITIONAL on a genuine
        intermediate sub-goal (feet within 40 mm of the plant
        footprint, i.e. curl-to-bridge-pose), by freezing
        the trajectory index fed to ``_current_goal()`` at the last
        pre-ramp (height==0) tick for as long as the sub-goal is unmet,
        up to a capped extra wait (`rise_curl_gate_max_extra_s`) so an
        episode that never curls still eventually gets scored on the
        attempt rather than stalling forever. ``_rise_ramp_i0`` (already
        computed at reset as the first nonzero index of the height
        schedule, for the pre-existing BC-reference alignment) doubles
        as the natural hold-boundary here. Crouch starts (curl_dist
        already ~0) are exempt from the curl sub-goal — nothing to
        gate.

        (2026-09-23, standwalk track second-rise-gap dig-in: this
        function used to also carry a second, independent sub-goal,
        ``goal.rise_stability_gate`` — freeze the ramp onset until
        measured attitude settled near-level, on the theory that the
        composed rise->walk->lower->rise->walk gate baseline's second
        (post-lower) rise falls because the policy is asked to climb
        before it arrests the attitude/momentum an unfamiliar post-
        lower pose leaves it in. Trained on both stand architectures
        (`cw-stand50hz-gru-dr07-risestabgate-s1`,
        `cw-stand50hz-mlp-dr07-risestabgate`) against a pre-registered
        eval_modeseq gate: FAILed both — GRU second-rise stayed 5/24
        (same band as the ungated parent), MLP reached 10/24 but with
        own-cfg(dr=0.7) termination regressing 2/36->4/36 including a
        severe over_current outlier. Refuted and removed per
        RESEARCH_RULES' close-the-key rule; the postlower second-rise
        gap needs a genuinely new curriculum-family design, not another
        index-freeze variant on this same mechanism. See
        `cw-stand50hz-gru-dr07-risestabgate-s1`/
        `cw-stand50hz-mlp-dr07-risestabgate` run ledgers.)

        Pure index-freeze: no new physics, no change to any existing
        reward term's formula; every other reward/obs path reads
        whatever ``_current_goal()`` returns exactly as before.
        Tests: rl_move/tests/test_rise_curl_gate_hold.py.
        """
        if not self._is_rise or self._goal_traj is None:
            return
        curl_on = float(cfg_get(self.cfg, "goal", "rise_curl_gate",
                                 default=0.0)) == 1.0
        if not curl_on:
            return
        hold_n = int(getattr(self, "_rise_ramp_i0", 0))
        freeze = self._rise_gate_freeze_ticks
        idx = self._step_i - freeze
        if idx < hold_n:
            return  # still inside the natural pre-ramp hold window
        max_extra_s = float(cfg_get(
            self.cfg, "goal", "rise_curl_gate_max_extra_s", default=2.0))
        max_extra_ticks = int(round(max_extra_s / self.dt))
        if freeze >= max_extra_ticks:
            return  # capped -- let the ramp proceed without the
                    # sub-goal met
        curl_met = (getattr(self._goal_traj, "start_at", None)
                    == "crouch"
                    or self._curl_dist() <= 40.0 * 0.001)
        if curl_met:
            return  # sub-goal met -- unlock permanently
        self._rise_gate_freeze_ticks = freeze + 1

    def _lower_stage_planted_frac(self, load_ref_n: float) -> float:
        """Fraction of feet (0..1) measured PLANTED right now: touch
        force >= ``load_ref_n`` newtons, same sensor read as
        ``hold_feet_load``/``_minload_min_force_now``; legs with no
        touch sensor fall back to the geometric clearance test those
        two use as well (clear <= ``foot_down_mm``). Used only by
        ``_lower_gate_tick`` — a plain instantaneous measurement, no
        smoothing, so the gate reacts on the very tick a foot lifts or
        re-plants."""
        n_on = 0
        for i in range(6):
            if self._touch_adr[i] >= 0:
                f_n = max(float(
                    self.data.sensordata[self._touch_adr[i]]), 0.0)
                on = f_n >= load_ref_n
            else:
                clear_i = (float(self.data.xpos[self._pad_bids[i], 2])
                           - self._pad_z_ref[i])
                on = clear_i <= PLANT_SPEC["foot_down_mm"] * 0.001
            if on:
                n_on += 1
        return n_on / 6.0

    def _lower_gate_tick(self) -> None:
        """Staged multi-phase descent (``goal.lower_stage_gate``,
        default 0 = OFF = bit-exact identical to every prior
        checkpoint): called once per real tick, right after
        ``self._step_i`` advances and before the tick's reward/obs
        goal is read. Mirrors ``_rise_gate_tick``'s index-freeze
        construction exactly, generalized from a one-shot pre-ramp
        sub-goal to a CONTINUOUS per-tick condition across the whole
        descent.

        Escalation context (2026-09-13, walkcurr `lowerscoreprog` /
        `lowerratchetpartial` / `lowerdenseposture`): three independent
        REWARD-side levers on the same from-plant lower depth gap
        (~40mm height_err_end, ~20-30% depth_frac, flat since
        `lowerscoreprog-{s0,s1}-6m`) all FAIL-MECHANISM at the same
        magnitude — repricing what depth income PAYS never changes how
        far the height ramp COMMANDS the policy to go, because
        ``goal.height_ref`` (the value the policy actually observes
        via ``TaskGoal.as_obs``; this recipe's own reward terms read
        ``h_rel``/``self._h_target`` directly and never consume
        ``height_ref`` at all) advances on a fixed wall-clock schedule
        (``goal.lower_ramp_s``) regardless of whether the feet are
        staying planted on the way down — the observed COMMAND has no
        way to say "you're not ready to go deeper yet". This is not a
        fourth re-price: it makes the ramp's own advance conditional on
        a genuine per-tick sub-goal (a measured fraction of feet loaded
        above 1 N, hardcoded threshold 0.7), by freezing the
        trajectory index fed to ``_current_goal()`` for as long as the
        sub-goal is unmet, up to a capped extra wait
        (5 s) so an episode that
        never plants still eventually gets scored on the attempt
        rather than stalling forever. Unlike the rise gate (which only
        holds the PRE-ramp onset), this re-checks every tick for the
        whole descent, so a policy that plants, unplants, then
        replants pauses and resumes rather than losing credit
        permanently. Pure index-freeze: no new physics, no change to
        any existing reward term's formula; every other reward/obs
        path reads whatever ``_current_goal()`` returns exactly as
        before.
        Tests: rl_move/tests/test_lower_stage_gate.py.
        """
        if not self._is_lower_bc or self._goal_traj is None:
            return
        if float(cfg_get(self.cfg, "goal", "lower_stage_gate",
                          default=0.0)) != 1.0:
            return
        hold_n = int(getattr(self, "_lower_ramp_i0", 0))
        freeze = self._lower_gate_freeze_ticks
        idx = self._step_i - freeze
        if idx < hold_n:
            return  # still inside the natural pre-ramp hold window
        if idx >= len(self._goal_traj.height) - 1:
            return  # ramp array already exhausted -- nothing to freeze
        max_extra_ticks = int(round(5.0 / self.dt))
        if freeze >= max_extra_ticks:
            return  # capped -- let the ramp proceed ungated from here
        if self._lower_stage_planted_frac(1.0) >= 0.7:
            return  # sub-goal met this tick -- ramp advances normally
        self._lower_gate_freeze_ticks = freeze + 1

    def _act_to_q(self, clipped: np.ndarray):
        """Map a clipped action to joint targets: (q_rad, ok, reason).

        Base env: body-offset action through the fixed-foot IK. The raw
        joint-space subclass overrides this and nothing else.
        """
        offset = action_to_body_offset(
            clipped, self.cfg,
            curl_frac=getattr(self.ik, "curl_frac", None))
        ik = self.ik.solve(offset)
        return ik.q_rad, ik.ok, ik.reason

    def _active_episode_steps(self) -> int:
        """Current trajectory horizon, bounded by the env's allocation."""
        limit = getattr(self._goal_traj, "duration_steps", None)
        if limit is None:
            return int(self.episode_steps)
        return min(int(self.episode_steps), max(1, int(limit)))

    def apply_residual_blend_frac(self, frac: float) -> dict:
        """Move the live assistfade rung-3 residual blend to ``frac``
        of the GATED anneal (0 = the low start, held until the
        trainer's own ignition-gate callback latches a pass; 1 = the
        cfg ``goal.walk_residual_blend`` target); see the
        ``goal.walk_residual_anneal_gate`` block in ``__init__``.
        Mirrors ``apply_drag_allow_frac``'s contract exactly: raises
        when the gate is not armed, so a broadcast that silently
        no-ops is never a hidden failure mode. VecEnv ``env_method``
        hook (sharded workers can't be poked in-process)."""
        if self._residual_blend_ramp is None:
            raise RuntimeError(
                "apply_residual_blend_frac called but goal."
                "walk_residual_anneal_gate is not set (>0) in this "
                "env's cfg — the residual-blend gated anneal is not "
                "armed")
        f = min(max(float(frac), 0.0), 1.0)
        s = self._residual_blend_ramp["start"]
        t = self._residual_blend_ramp["target"]
        self._residual_blend_override = s + f * (t - s)
        self._residual_blend_ramp["frac"] = f
        return {"frac": f, "blend": self._residual_blend_override}

    def apply_residual_blend_frac_perleg(self, fracs) -> dict:
        """Per-LEG variant of ``apply_residual_blend_frac`` (see that
        method's docstring for the shared start/target ramp contract
        this reuses unchanged — only the FRACTION now varies per leg
        instead of being one shared scalar). ``fracs`` is a length-6
        iterable, one independent [0, 1] anneal fraction per leg
        (mirror.py's N_LEGS ordering: action indices [3*leg, 3*leg+3)
        — see the action-blend consumer in ``step()``). Requires
        ``goal.walk_residual_perleg_gate>0`` (the per-leg refinement of
        the same ramp ``apply_residual_blend_frac`` drives) — raises
        the same way if unarmed, including when only the plain
        (non-per-leg) anneal gate is armed instead."""
        if self._residual_blend_ramp is None or not self._residual_perleg_gate:
            raise RuntimeError(
                "apply_residual_blend_frac_perleg called but goal."
                "walk_residual_perleg_gate is not armed (>0) in this "
                "env's cfg — the per-leg residual-blend gated anneal "
                "is not armed")
        f = np.clip(np.asarray(fracs, dtype=np.float64), 0.0, 1.0)
        if f.shape != (6,):
            raise ValueError(
                "apply_residual_blend_frac_perleg expects 6 fracs (one "
                f"per leg), got shape {f.shape}")
        s = self._residual_blend_ramp["start"]
        t = self._residual_blend_ramp["target"]
        self._residual_blend_override = s + f * (t - s)
        self._residual_blend_ramp["frac"] = f.copy()
        return {"frac": f.tolist(),
                "blend": self._residual_blend_override.tolist()}

    def apply_hold_grace_frac(self, frac: float) -> dict:
        """Move the live HOLD-mode termination envelope to ``frac`` of
        the gated tightening curriculum (0 = the loose ``safety.
        hold_grace_start_*`` start, held until the trainer's ignition
        gate first latches a survival-competence pass; 1 = the cfg
        ``safety.hold_max_height_drop_mm``/``hold_height_grace_s``
        target); see the ``safety.hold_grace_curriculum`` block in
        ``__init__``. Mirrors ``apply_residual_blend_frac``'s contract
        exactly: raises when the gate is not armed, so a broadcast
        that silently no-ops is never a hidden failure mode. VecEnv
        ``env_method`` hook (sharded workers can't be poked
        in-process)."""
        if self._hold_grace_ramp is None:
            raise RuntimeError(
                "apply_hold_grace_frac called but safety."
                "hold_grace_curriculum is not set (>0) in this env's "
                "cfg — the hold-grace gated anneal is not armed")
        f = min(max(float(frac), 0.0), 1.0)
        r = self._hold_grace_ramp
        self._hold_grace_override_drop_mm = (
            r["start_drop"] + f * (r["target_drop"] - r["start_drop"]))
        self._hold_grace_override_grace_s = (
            r["start_grace"] + f * (r["target_grace"] - r["start_grace"]))
        r["frac"] = f
        return {"frac": f, "drop_mm": self._hold_grace_override_drop_mm,
                "grace_s": self._hold_grace_override_grace_s}

    def apply_profile_ramp_frac(self, frac: float) -> dict:
        """Move the live write profile to ``frac`` of the ramp
        (0 = gentle start, 1 = the cfg target dose); trainer-driven —
        see the ``bus.profile_ramp_steps`` block in ``__init__``.
        Returns the applied values (counts/s, acc units, deg/tick) so
        the trainer can print/log the active profile. Raises when the
        ramp is not armed: a broadcast that silently no-ops is the
        dropped-cfg failure class (gotcha 3), never fall back quietly.
        """
        if self._profile_ramp is None:
            raise RuntimeError(
                "apply_profile_ramp_frac called but bus."
                "profile_ramp_steps is not set (>0) in this env's cfg "
                "— the profile ramp is not armed")
        f = min(max(float(frac), 0.0), 1.0)
        s = self._profile_ramp["start"]
        t = self._profile_ramp["target"]
        ws, acc, dq = (s[i] + f * (t[i] - s[i]) for i in range(3))
        self.write_speed_deg_s = ws * 360.0 / 4096.0
        self.write_acc_units = float(acc)
        # safety is deep-copied into MJX pool-restore snapshots
        # (mjx_host.SNAP_ATTRS), so a restored episode would revive a
        # stale max_dq — _step_begin re-asserts this value every tick
        # while the ramp is armed (the commit-65edba7 bug class).
        self._profile_ramp_dq_rad = math.radians(dq)
        self.safety.max_dq = self._profile_ramp_dq_rad
        self._profile_ramp["frac"] = f
        return {"frac": f, "write_speed_counts_s": ws,
                "write_acc": float(acc), "max_delta_q_deg": dq}

    def apply_dr_stage_frac(self, frac: float) -> dict:
        """Move the episode-reset DR distribution to ``frac`` of the
        staged-DR ramp (0 = calibrated nominal sim with sensor-noise
        floors kept, 1 = this run's full post-override ranges);
        trainer-driven — see the ``env.dr_stage_ramp_steps`` block in
        ``__init__``. Returns a summary of the live ranges so the
        trainer can print/log the active stage. Raises when the ramp
        is not armed: a broadcast that silently no-ops is the
        dropped-cfg failure class (gotcha 3), never fall back quietly.
        Affects only FUTURE episode resets (the sample() draw at
        reset); the trainer flushes pooled resets on each change so
        pre-minted pool entries never leak a stale stage.
        """
        if self._dr_stage_full is None:
            raise RuntimeError(
                "apply_dr_stage_frac called but env.dr_stage_ramp_"
                "steps is not set (>0) in this env's cfg — the "
                "DR-stage ramp is not armed")
        f = min(max(float(frac), 0.0), 1.0)
        key = round(f, 6)
        ranges = self._dr_stage_cache.get(key)
        if ranges is None:
            # f >= 1 restores the EXACT captured full-ranges object:
            # the endpoint is bit-identical to the un-staged recipe,
            # not a float-rounded reconstruction of it.
            ranges = (self._dr_stage_full if f >= 1.0
                      else self._dr_stage_full.scaled(f))
            self._dr_stage_cache[key] = ranges
        self.randomizer.ranges = ranges
        self._dr_stage_frac = f
        return {"frac": f,
                "mass_scale_lo": float(ranges.mass_scale[0]),
                "mass_scale_hi": float(ranges.mass_scale[1]),
                "friction_lo": float(ranges.friction_scale[0]),
                "friction_hi": float(ranges.friction_scale[1]),
                "ground_tilt_deg": float(ranges.ground_tilt_deg),
                "bad_start_prob": float(ranges.bad_start_prob),
                "fault_prob": float(ranges.fault_prob)}

    def _step_begin(self, action):
        """Pre-physics half of step: action validation, IK, safety
        filter, and the servo command. Returns ``(early, ctx)`` —
        ``early`` is a full step tuple when the action was rejected
        outright (no physics runs in that case), else None with ``ctx``
        for :meth:`_step_finish` after physics has advanced one tick.
        Split so the batched MJX vec env can run all envs' pre-physics
        halves, one batched tick, then all post-physics halves.
        """
        # In-run coefficient scheduler (see __init__): both stacks call
        # _step_begin every tick (sim_env.step and the MJX vec envs'
        # step_wait), so this is the one hook that clocks identically
        # everywhere. Runs BEFORE this tick's reward is computed.
        if self._sched_key:
            self._sched_ticks += 1
            t = self._sched_ticks * self._sched_n
            if t <= self._sched_t0:
                v = self._sched_v0
            elif t >= self._sched_t1:
                v = self._sched_v1
            else:
                f = ((t - self._sched_t0)
                     / (self._sched_t1 - self._sched_t0))
                v = self._sched_v0 + f * (self._sched_v1 - self._sched_v0)
            self._sched_value = v
            node = self.cfg
            for k in self._sched_path[:-1]:
                node = node.setdefault(k, {})
            node[self._sched_path[-1]] = v
        # Rung-3 assistance-removal ("residual fade", EASIER_WALKING_
        # CURRICULUM.md item 3 / assistfade track): goal.walk_residual_
        # gate>0 (default 0, bit-exact off) blends the raw policy
        # action with the SAME command-conditioned scripted TripodGait
        # reference the WALK BC-anchor target uses (self._walk_bc_gait,
        # constructed whenever this gate OR bc_anchor_coef is on — see
        # __init__/_reset_begin), via one tied scalar `goal.walk_
        # residual_blend` in [0, 1]:
        #     applied = ref + blend * (raw_action - ref)
        # blend=0 => applied IS the reference: the raw policy has ZERO
        # authority, so an untrained/adversarial actor still produces
        # the reference gait (solves rung 3's ignition problem
        # structurally, not via reward shaping). blend=1 => applied IS
        # the raw policy action exactly (the reference cancels out —
        # mathematically identical to this gate being off). This one
        # scalar satisfies both halves of the curriculum doc's rung-3
        # description ("increase residual authority" = the growing
        # blend*(raw-ref) term; "reduce reference amplitude" = the
        # shrinking (1-blend) weight left on ref) — an explicit
        # assume-and-go simplification (OPERATOR_QUESTIONS.md) instead
        # of two independently-scheduled knobs. `blend` is either (a)
        # driven by the generic sched.* engine above (sched.key=
        # "goal.walk_residual_blend", v0 small -> v1=1.0, a fixed
        # step-count calendar — the original rung-3 recipe, now
        # closed 6/6 arms per rl_docs/tracks/assistfade/STATUS.md
        # 09-09), or (b) held at ``self._residual_blend_override``
        # when the GATED anneal is armed (goal.walk_residual_anneal_
        # gate>0, see __init__/apply_residual_blend_frac) — a
        # structurally different, behavior-contingent schedule instead
        # of a calendar one. Only active on WALK ticks with a live
        # command-conditioned teacher — never touches rise/hold/lower/
        # getup. Bank: test_residual_blend_anneal.py (rl_move/tests),
        # historical bank test_assistfade_rung3_* (test_task_
        # semantics.py, retired 09-08, not extended).
        if (float(cfg_get(self.cfg, "goal", "walk_residual_gate",
                          default=0.0)) > 0.0
                and getattr(self, "_walk_bc_gait", None) is not None
                and getattr(self, "n_act", 0) == N_JOINTS):
            _res_override = getattr(self, "_residual_blend_override",
                                     None)
            if _res_override is not None and np.ndim(_res_override) > 0:
                # Per-leg override (goal.walk_residual_perleg_gate,
                # 2026-09-14): a (6,) array, one blend per leg —
                # broadcast to the 18-dim action via repeat(3) (leg-
                # major joint order, mirror.py's N_LEGS convention:
                # action index 3*leg+axis). _res_blend_active is a
                # plain bool since "any leg still < 1.0" is what
                # decides whether the reference-blend math below runs
                # at all (running it is a no-op, not wrong, when every
                # leg is already at 1.0 — this just skips the extra
                # work in that common end-state).
                _res_blend_perleg = np.clip(
                    np.asarray(_res_override, dtype=np.float64),
                    0.0, 1.0)
                _res_blend = np.repeat(_res_blend_perleg, 3)
                _res_blend_active = bool(np.any(_res_blend_perleg < 1.0))
            else:
                _res_blend = float(np.clip(
                    _res_override if _res_override is not None
                    else cfg_get(self.cfg, "goal", "walk_residual_blend",
                                default=1.0),
                    0.0, 1.0))
                _res_blend_active = _res_blend < 1.0
            if _res_blend_active:
                _res_goal = self._current_goal()
                if _res_goal is not None:
                    from .joint_task import q_rad_to_action
                    _res_g = self._walk_bc_gait
                    _res_g.set_velocity(
                        vx=float(_res_goal.vx_ref),
                        vy=float(_res_goal.vy_ref),
                        omega=float(getattr(_res_goal, "wz_ref", 0.0)
                                    or 0.0))
                    _res_ref = q_rad_to_action(
                        np.asarray(_res_g.desired_deg(
                            self._step_i * self.dt)) * DEG2RAD
                        ).astype(np.float32)
                    action = np.clip(
                        _res_ref + _res_blend
                        * (np.asarray(action, dtype=np.float32)
                           - _res_ref),
                        -1.0, 1.0)
        assert self._state is not None and self._profile is not None
        clipped, bad = self.safety.validate_action(action, n_act=self.n_act)
        pen = float(cfg_get(self.cfg, "reward",
                            "safety_termination_penalty", default=10))
        if clipped is None:
            self._step_i += 1
            # Early-fall horizon cost (08-15, operator directive
            # fb_20260815T114414): reward.term_cost_per_remaining_s
            # charges k * REMAINING episode seconds on top of the flat
            # penalty for ANY safety termination, so a drag-then-fall
            # cannot bank income a survivor would have kept earning
            # (cw-mt-c2's ~6 s drag-then-fall retained positive return
            # at the flat -10). Truncation is never charged. Default
            # 0.0 = legacy bit-exact.
            k_rem = float(cfg_get(self.cfg, "reward",
                                  "term_cost_per_remaining_s",
                                  default=0.0))
            if k_rem > 0.0:
                rem_cost = k_rem * max(self._active_episode_steps()
                                       - self._step_i,
                                       0) * self.dt
                # Bounded terminal cost (08-17, operator-approved
                # fb_20260817T005114 item 5): the uncapped horizon
                # charge reached ~-730 on an early 60 s fall and the
                # critic never learned to predict that rare cliff
                # (explained variance ~0 through 40M on
                # cw-arch-joystick-long-scratch3). term_cost_max caps
                # the ADDED horizon component only (flat penalty is
                # untouched); falls stay decisively bad via the dense
                # roll/pitch shaping + this bounded charge. Default
                # 0 = off, legacy uncapped bit-exact.
                cap = float(cfg_get(self.cfg, "reward",
                                    "term_cost_max", default=0.0))
                if cap > 0.0:
                    rem_cost = min(rem_cost, cap)
                pen += rem_cost
            parts = {"reward_termination": -pen}
            return (self._final_obs(
                        build_obs(self.cfg, self._state, self._q_nom,
                                  self._prev_action,
                                  goal=self._current_goal(),
                                  tilt_ref=self._tilt_ref0,
                                  height_vel_mps=self._height_vel_mps),
                                  reset=False),
                    -pen, True, False,
                    {"termination_reason": bad, **parts}), None

        if self._ep_rand is not None and self._ep_rand.action_noise > 0:
            clipped = np.clip(
                clipped + self.rng.normal(0.0, self._ep_rand.action_noise,
                                          self.n_act), -1.0, 1.0)

        q_prop, q_ok, q_reason = self._act_to_q(clipped)
        if getattr(self, "debug_pipeline_record", False):
            # Action-pipeline probe hook (2026-09-08 walkcurr action-
            # clipping/controllability preflight): stash the exact
            # per-tick decoder inputs/outputs so eval traces can audit
            # actor -> proposed-target -> SafetyLayer transmission
            # offline. Copies only, attribute unset by default => zero
            # behavior change and zero cost on every existing path.
            self._dbg_applied_action = np.asarray(
                clipped, dtype=np.float64).copy()
            self._dbg_proposed_q = np.asarray(
                q_prop, dtype=np.float64).copy()
            self._dbg_presafe_last = self.safety._last_safe.copy()
            self._dbg_max_dq_rad = float(self.safety.max_dq)
        if self._profile_ramp_dq_rad is not None:
            # Profile ramp armed: pool-restores revive a deep-copied
            # SafetyLayer minted under an older ramp value — re-assert
            # the live slew clamp every tick (see apply_profile_ramp_frac).
            self.safety.max_dq = self._profile_ramp_dq_rad
        safety_state = (self._state if self._deployed_transport is None else
                        self._deployed_transport.safety_state(self._state))
        q_safe, status = self.safety.filter(
            q_prop, safety_state, ik_ok=q_ok, ik_reason=q_reason,
            action=clipped, curl_frac=getattr(self.ik, "curl_frac", None))
        # Structural stop-hold override (goal.walk_stop_freeze_s,
        # default 0.0 = off, bit-exact identity) -- see
        # _walk_stop_freeze_override for why this runs here (after
        # the safety filter, before self._cmd is latched below).
        q_safe = self._walk_stop_freeze_override(q_safe)

        terminated = bool(status.terminate)
        if not terminated:
            self._cmd = q_safe.copy()
            # DR: occasionally a SyncWrite is lost on the bus — the servos
            # keep chasing the previous goal for one tick.
            if self._ep_rand is None:
                dropped = False
            elif self._ep_rand.cmd_drop_burst_len > 0.0:
                # DR: bursty drops (dr.cmd_drop_burst_len) -- brownout/bus
                # stalls drop CONSECUTIVE SyncWrites. Two-state Markov: enter
                # with cmd_drop_prob, stay with (1 - 1/len). The else-branch
                # (==0, default) is the i.i.d. single-tick path, bit-exact.
                if self._cmd_dropping:
                    dropped = True
                    if self.rng.random() < (
                            1.0 / max(self._ep_rand.cmd_drop_burst_len, 1.0)):
                        self._cmd_dropping = False
                else:
                    dropped = self.rng.random() < self._ep_rand.cmd_drop_prob
                    if dropped:
                        self._cmd_dropping = True
            else:
                dropped = self.rng.random() < self._ep_rand.cmd_drop_prob
            write_due = (self._deployed_transport is None
                         or self._deployed_transport.write.due(self.data.time))
            if not dropped and write_due:
                # Zero-drift FRAME mode (dr.zero_drift_cmd_frame=1): a
                # drifted set_zero shifts reads AND commands together on
                # hardware — logical target C drives physical C - bias
                # (obs adds +bias, so the read converges back to C and
                # the loop is self-consistent; only physics sees the
                # offset). Legacy mode biased reads only, leaving a
                # cmd-vs-read residual hardware never shows.
                cmd_phys = q_safe
                if (self._ep_rand is not None
                        and self._ep_rand.zero_drift_cmd_frame):
                    cmd_phys = q_safe - self._ep_rand.joint_zero_bias_rad
                rock = self._rise_rock_offset()
                if rock is not None:
                    cmd_phys = self._clip_to_joint_limits(cmd_phys + rock)
                kick = self._walk_kick_offset()
                if kick is not None:
                    cmd_phys = self._clip_to_joint_limits(cmd_phys + kick)
                self._profile.command(
                    self._logical_to_mujoco_q(cmd_phys),
                    speed_deg_s=self.write_speed_deg_s,
                    acc_units=self.write_acc_units)
        return None, (clipped, terminated, status, pen)

    def _apply_foot_stickslip(self) -> None:
        """Per-CONTROL-TICK Coulomb stick-slip friction update
        (dr.foot_stickslip_gain, see domain_rand.stickslip_friction_mult).

        Guarded no-op whenever this episode drew all-zero gain (the
        default) -- costs one attribute check, no array ops, no rng.
        Deliberately called ONCE per real env.step() (not per physics
        substep, and NOT from ``_settle``/``_seq_capture_frames``): a
        tick-rate update is cheap and matches the existing per-foot XY
        slip-velocity convention (walk_task's own k_tslip finite-
        difference uses the SAME env.dt cadence, a separate independent
        cache -- no shared state, no risk of the two mechanisms
        interfering). Deliberately does NOT touch ``_advance``'s substep
        loop or the reset-time SLIP_MU settle override, which
        temporarily replaces ALL geom_friction wholesale -- rewriting
        just the foot rows there would silently fight that override.

        Uses THIS tick's foot XY position vs. LAST tick's (one-tick
        lagged, never a look-ahead -- same convention as
        ``_backlash_prev_force``) to estimate sliding speed, then sets
        ``model.geom_friction[foot_gids, 0]`` to the per-episode KINETIC
        baseline (captured at reset, after the static foot_friction_scale
        dose) times the live stick-slip multiplier.
        """
        if not self._stickslip_active:
            return
        cur_xy = self.data.site_xpos[self._stickslip_foot_sids, :2].copy()
        if self._stickslip_prev_xy is None:
            speed = np.zeros(6, dtype=float)
        else:
            speed = (np.linalg.norm(cur_xy - self._stickslip_prev_xy, axis=-1)
                      / max(self.dt, 1e-9))
        self._stickslip_prev_xy = cur_xy
        mult = stickslip_friction_mult(
            speed, self._stickslip_vel_ref_mps, self._stickslip_gain)
        self.model.geom_friction[self._stickslip_foot_gids, 0] = (
            self._stickslip_base_mu * mult)

    def _update_foot_catch_state(self) -> None:
        """Per-CONTROL-TICK liftoff detector driving the transient
        foot-catch/stumble event (dr.foot_catch_force_n, see
        domain_rand.EpisodeRandomization). Guarded no-op whenever this
        episode drew all-zero magnitude (the default) -- costs one
        attribute check.

        Fires once per genuine LIFTOFF: the foot's own touch-force
        sensor (``_touch_adr``, the same ground-truth load reading
        ``_lower_stage_planted_frac``/``hold_feet_load`` use) transi-
        tioning from planted to airborne. This is deliberately NOT a
        blind clock/phase guess -- it is coupled to whatever gait the
        frozen policy actually produces, on this exact tick, which is
        the "coupled to gait phase" requirement named in
        rl_docs/tracks/speed/STATUS.md (09-20). A cooldown prevents a
        chattering touch reading near the threshold from re-triggering
        mid-event.

        Called ONCE per real env.step() (before ``_advance``, same
        site/cadence as ``_apply_foot_stickslip``) using THIS tick's
        sensor data -- i.e. the result of the PREVIOUS tick's physics,
        never a look-ahead into the tick about to run."""
        if not self._foot_catch_owns_row:
            return
        t = self._step_i * self.dt
        for i in range(6):
            adr = self._touch_adr[i]
            f_n = float(self.data.sensordata[adr]) if adr >= 0 else 0.0
            touched = f_n > FOOT_CATCH_LOAD_ON_N
            if (self._foot_catch_prev_touch[i] and not touched
                    and t >= self._foot_catch_cooldown_until_s[i]):
                self._foot_catch_end_s[i] = t + FOOT_CATCH_DURATION_S
                self._foot_catch_cooldown_until_s[i] = (
                    t + FOOT_CATCH_COOLDOWN_S)
            self._foot_catch_prev_touch[i] = touched

    def step(self, action):
        early, ctx = self._step_begin(action)
        if early is not None:
            return self._post_step(early)
        self._apply_foot_stickslip()
        self._update_foot_catch_state()
        self._advance()
        return self._post_step(self._step_finish(ctx))

    def _post_step(self, result):
        """Subclass hook applied to EVERY completed step tuple (both the
        normal path and the rejected-action early return) — walk-mode
        shaping lives here so the batched vec env inherits it."""
        # AMP track (08-22, M1 reward-loop wiring): when
        # goal.amp_style_obs=1 (default 0 = bit-exact legacy: no key,
        # no compute), emit the 60-dim AMP discriminator feature
        # vector (rl_docs/AMP_LOCOMOTION.md §3.6) into info each tick.
        # RAW joint angles in dims 0..17 (neutral=0): the trainer-side
        # AMPStyleVecWrapper subtracts the motion library's OWN neutral
        # pose so there is exactly one authoritative neutral convention
        # (the library's — verified identical across all teacher_v1
        # clips). Works on both physics backends: obs_style_from_data
        # only touches qpos/qvel/xpos/xmat/sensordata, present on real
        # MjData and on mjx_host.FakeData alike. On the rejected-action
        # early return the mirror is one tick stale — that episode
        # terminates immediately and the wrapper's done-masking drops
        # the follow-up pairing, so at most one near-duplicate
        # transition per (rare) rejected action reaches the
        # discriminator replay.
        if self._deployed_transport is not None:
            result[4]["transport"] = self._deployed_transport.summary()
        amp_on = getattr(self, "_amp_style_on", None)
        if amp_on is None:
            amp_on = float(cfg_get(self.cfg, "goal", "amp_style_obs",
                                   default=0.0)) > 0.0
            self._amp_style_on = amp_on
            # goal.amp_style_cmd_cond=1 (default 0 = bit-exact legacy,
            # only reachable when amp_style_obs is also on): appends
            # the CURRENT commanded (vx_ref, vy_ref, wz_ref) to the
            # emitted obs_style vector (60 -> 63 dims). This is the
            # command-conditioning fix for the 08-23 yaw-authority
            # root-cause finding (rl_docs/tracks/amp/STATUS.md ~12:4x):
            # the discriminator previously saw raw base_angular_velocity
            # with no idea what rotation rate was COMMANDED, so any
            # policy turning faster than the teacher's own demos (which
            # embody ~0.13-0.18 rad/s regardless of label) read as
            # "unlike the teacher" and got docked — pricing, wider-
            # ceiling demos, style ablation and reset densification
            # were all measured unable to move this. Only meaningful
            # paired with a motion library built with
            # ``build_motion_library.py --cmd-cond`` (matching 63-dim
            # obs_style) — a mismatched dim is a loud shape error from
            # AMPStyleVecWrapper/AMPDiscriminator, never a silent
            # misread.
            self._amp_style_cmd_cond = float(cfg_get(
                self.cfg, "goal", "amp_style_cmd_cond", default=0.0)) > 0.0
            if amp_on:
                from .amp_features import chassis_pad_gyro_ids
                self._amp_style_ids = chassis_pad_gyro_ids(self)
                self._amp_style_neutral = np.zeros(
                    int(self._amp_style_ids.qadr.shape[0]))
        if amp_on:
            from .amp_features import obs_style_from_data
            cmd = None
            if self._amp_style_cmd_cond:
                goal = self._current_goal()
                cmd = (float(getattr(goal, "vx_ref", 0.0)),
                       float(getattr(goal, "vy_ref", 0.0)),
                       float(getattr(goal, "wz_ref", 0.0)))
            result[4]["amp_obs_style"] = obs_style_from_data(
                self.data, self._amp_style_ids, self._amp_style_neutral,
                cmd=cmd)
        return result

    def _rise_ref_clock(self, ref: dict) -> tuple[int, bool]:
        """Reference tick for the CURRENT (post-step) state + is_rsi.

        RSI episodes joined the reference at the settled tick j0
        (_reset_finalize nearest-neighbor alignment); legacy episodes
        time-align at the ramp start. Clamped to the path end — the
        reference's final plant is the hold target thereafter. Shared
        by the rise-ref tracking reward and the BC-anchor target
        emission so the two can never disagree about the clock."""
        if self._rsi_ref_tick0 is not None:
            j = self._rsi_ref_tick0 + int(round(
                self._step_i * self.dt / ref["dt"]))
            is_rsi = True
        else:
            t_rel = (self._step_i - self._rise_ramp_i0) * self.dt
            j = ref["ramp_i0"] + int(round(t_rel / ref["dt"]))
            is_rsi = False
        return min(max(j, 0), len(ref["q"]) - 1), is_rsi

    def _make_walk_bc_gait(self):
        """Canonical robot-coordinate gait for the walk BC anchor.

        2026-09-02: knee arg is robot_abs (absolute tibia); 100, not 80
        -- see ``_default_plant_deg`` for the full derivation of this
        literal (100 = the historical mujoco-relative 80 + hip 20).

        2026-09-23 (extplant82-actionbox-yaw11 dig-in follow-up): the
        stance synced here used to be the LITERAL 20.0/100.0 pair above
        regardless of ``self._plant_deg`` -- fine while every bc_anchor_
        walk run trained under the legacy tucked plant (hip=20/knee=100
        robot_abs, ``_default_plant_deg``'s own value, so the literal
        WAS correct there), but the entire extplant82 extended-plant
        family (``plant.hip_deg``/``plant.knee_deg`` cfg overrides,
        2026-09-22 lukas-ef spec, e.g. hip=20/knee=82) sets
        ``bc_anchor_coef=3.0`` too -- discovered live in the yaw11-
        ramp5m-s0 FAIL triage: this teacher was STILL syncing to the
        old knee=100 target, which is physically UNREACHABLE inside
        that lineage's own action box (bias+box center 82, max reach
        ~97) by DESIGN (the box exists specifically to make knee=100
        unreachable, per the actionbox-s0 hypothesis). Every extplant82-
        actionbox arm (s0/ramp/ramp5m/ramp5m-logstdcomp/yaw11-ramp5m)
        therefore trained under a constant, unwinnable MSE-vs-
        unreachable-target supervisory pull toward one edge the whole
        run -- a plausible full explanation for the "policy never uses
        the room it has" oscillation-suppression signature the
        logstdcomp dig-in measured (3-10 deg peak-to-peak knee swing vs
        the box's own ~24 deg width) that log-std compensation (which
        doesn't touch this pull at all) could not fix. Fixed to read
        the run's OWN resolved plant target (``self._plant_deg``, robot_
        abs [yaw,hip,knee]x6, same array ``_default_plant_deg``/
        ``plant_deg=`` populate) instead of the hardcoded literal --
        bit-exact for every run that never overrides plant.hip_deg/
        knee_deg (self._plant_deg defaults to exactly 20.0/100.0), only
        a behavior change for the plant-overridden family that has
        never had a verdicted PASS under the old hardcoded literal.

        ``train.bc_anchor_teacher_yaw_arm_scale`` (standwalk Next item
        2, candidate (i)-v2, 09-03 -- see tripod_gait.py's
        ``combined_yaw_arm_scale`` docstring for the full derivation):
        default 1.0 = legacy identity (bit-exact off); a static
        per-run dose, read once here since the cfg never changes
        mid-run.

        ``train.bc_anchor_teacher_selective_omega_boost`` (standwalk
        Next item 2, "selective per-leg omega boost" candidate,
        09-04 -- see tripod_gait.py's ``combined_selective_omega_
        boost`` docstring): unlike the yaw-arm-scale/amplify-scale
        family (angle-only reshape, all refuted), this boosts the
        TRUE foot target for only the 3 legs the vx cross term
        attenuates, restricted internally to combined ticks --
        mirrors the already-tried UNIFORM ``bc_anchor_teacher_omega_
        boost`` (applied earlier, to ``_bc_wz`` itself, before
        ``set_velocity``) but at the per-leg level, inside
        ``TripodGait.desired_deg`` itself. Zero-training scripted-
        teacher validation (``probe_turn_authority.py --policy
        scripted --scripted-selective-omega-boost``): dose 3.0 beats
        the uniform lever's own best dose on real body wz_med, both
        signs, with a comparable vx cost. Default 1.0 = legacy
        identity (bit-exact off).

        ``train.bc_anchor_teacher_period_scale`` /
        ``train.bc_anchor_teacher_lift_scale`` /
        ``train.bc_anchor_teacher_stride_scale`` (speed track step 1,
        2026-09-11): gait-geometry doses for the SAME teacher, mapped
        1:1 onto TripodGait's existing ``period_scale`` /
        ``lift_scale`` / ``stride_scale`` ctor knobs, so a speed-track
        arm can anchor to a longer-stride / higher-lift / retuned-
        cadence target instead of the stock 0.75 s geometry. Doses are
        chosen from the zero-training feasibility sweep
        (``probe_teacher_headings --period-scale/--lift-scale/
        --stride-scale``), never guessed. Defaults 1.0 = legacy
        identity (bit-exact off) like every other dose knob here.

        ``train.bc_anchor_teacher_stance_radius_scale`` (speed track,
        2026-09-11 ~11:2x): maps 1:1 onto TripodGait's existing
        ``stance_radius_scale`` ctor knob (home foot radial distance
        x this, clipped to [0.55, 1.05] same as the turn-track's
        ``probe_turn_authority.py`` usage). Zero-training sweep
        (``probe_teacher_headings --stance-radius-scale``) found a
        real, small, already-capped speed gain at the class's own
        legal ceiling (1.05: +2.5% speed, improved slip) -- free money
        to fold into a speed-track dose alongside period/lift/stride,
        never a standalone lever. Default 1.0 = legacy identity
        (bit-exact off)."""
        from hexapod_core.tripod_gait import TripodGait
        _g = TripodGait(
            vx=0.0,
            period_scale=float(cfg_get(
                self.cfg, "train", "bc_anchor_teacher_period_scale",
                default=1.0)),
            lift_scale=float(cfg_get(
                self.cfg, "train", "bc_anchor_teacher_lift_scale",
                default=1.0)),
            stride_scale=float(cfg_get(
                self.cfg, "train", "bc_anchor_teacher_stride_scale",
                default=1.0)),
            stance_radius_scale=float(cfg_get(
                self.cfg, "train", "bc_anchor_teacher_stance_radius_scale",
                default=1.0)),
            combined_yaw_arm_scale=float(cfg_get(
                self.cfg, "train", "bc_anchor_teacher_yaw_arm_scale",
                default=1.0)),
            combined_selective_omega_boost=float(cfg_get(
                self.cfg, "train", "bc_anchor_teacher_selective_omega_boost",
                default=1.0)))
        _g.sync_plant_stance(float(self._plant_deg[1]),
                             float(self._plant_deg[2]))
        _g.reset_phase()
        return _g

    def _apply_walk_reverse_handoff(self) -> None:
        """Rung-4 reverse-curriculum warm start (EASIER_WALKING_
        CURRICULUM.md item 4 / assistfade track, 2026-09-07).

        Default 0 = OFF, bit-exact (single cheap cfg_get + early
        return -- no rng draw, no extra physics tick, unless the gate
        is armed). When ``goal.walk_reverse_handoff_gate>0``: called
        from ``reset()`` AFTER the ordinary settle (robot standing
        quietly at ``q_nom``) and BEFORE ``_reset_finalize()`` captures
        the episode's start references (``_z0``/``_pad_z_ref``/IK
        reset/etc), so those references reflect the POST-handoff state
        like any other episode start, not the pre-handoff static one.

        Runs the SAME proven scripted TripodGait teacher used by the
        WALK BC anchor / rung-3 residual blend
        (``self._make_walk_bc_gait()``) for
        ``goal.walk_reverse_handoff_s`` further seconds of REAL physics
        (genuine contact forces / momentum / footfall via
        ``self._advance()`` -- a state TELEPORT would skip the settle
        machinery entirely and is deliberately not what this does).
        Meant to be driven by the existing generic in-run ``sched.*``
        engine (no new trainer callback needed, same pattern as rung
        3's ``goal.walk_residual_blend``):
        ``sched.key="goal.walk_reverse_handoff_s"``, v0=<a few seconds>
        annealing to v1=0.0. A large v0 hands the policy an
        ALREADY-MOVING, mid-gait state for the rest of the episode
        (easy -- rung 4's own historical failure mode was always a
        static-basin freeze from a motionless stand); as the schedule
        anneals toward 0 over training, the handoff shrinks back to the
        ORIGINAL zero-handoff static start (hard) -- the reverse-
        curriculum direction the doc names ("expand the set of starts
        backward toward the true beginning"). The handoff itself is
        NOT a rollout transition (no reward/obs is exposed to the RL
        algorithm for these ticks, exactly like the pre-existing
        settle/``_reset_history_probe`` ticks it sits next to) --
        avoids any action/reward mismatch bias.

        Each episode's handoff starts at a RANDOM phase of the gait
        cycle (not always the same point) so the policy sees a
        diversity of already-moving states, not one memorized pose.

        CPU single-env ``reset()`` only for now -- the MJX vec-env
        twin (``mjx_vec_env.py``/``mjx_sharded_vec_env.py``
        ``_choreography()``, needed for real GPU-scale training
        throughput) is an explicitly deferred follow-up, named in
        ``rl_docs/tracks/assistfade/STATUS.md``; this env's own held-
        out gate evals and the semantics bank both exercise this CPU
        path directly."""
        gate = float(cfg_get(self.cfg, "goal", "walk_reverse_handoff_gate",
                             default=0.0))
        if gate <= 0.0:
            return
        handoff_s = float(cfg_get(self.cfg, "goal", "walk_reverse_handoff_s",
                                  default=0.0))
        if handoff_s <= 0.0:
            return
        goal = self._current_goal()
        if goal is None:
            return
        gait = self._make_walk_bc_gait()
        gait.set_velocity(vx=float(getattr(goal, "vx_ref", 0.0) or 0.0),
                          vy=float(getattr(goal, "vy_ref", 0.0) or 0.0),
                          omega=float(getattr(goal, "wz_ref", 0.0) or 0.0))
        gait.reset_phase(phase=float(self.rng.uniform(0.0, 2 * math.pi)))
        n = int(round(handoff_s / self.dt))
        for k in range(n):
            t = k * self.dt
            q_rad = self._clip_to_joint_limits(
                np.asarray(gait.desired_deg(t), dtype=float) * DEG2RAD)
            # Same command path a normal RL-action tick uses (_step_finish):
            # queue a profile write (latency + trapezoidal slew + deadband
            # all apply, exactly like a real command), THEN advance physics
            # -- not a raw ctrl/state teleport.
            self._cmd = q_rad.copy()
            self._profile.command(
                self._logical_to_mujoco_q(q_rad),
                speed_deg_s=self.write_speed_deg_s,
                acc_units=self.write_acc_units)
            self._advance()

    # ---- mode sequencing (goal.mode_seq; TRANSITIONS_DIRECTIVE item 1)

    def _seq_segment_traj(self, mode: str, tick: int):
        """Build one mid-episode segment's reference schedule. Only the
        goal tasks support mode sequencing: goal_task (rise/hold/lower,
        goal.mode_seq_stance) and walk_task (adds walk, goal.mode_seq)."""
        raise NotImplementedError(
            "mode_seq segments require a goal task (joint_goal for "
            "stance-only sequences, joint_walk for walk grammars)")

    # Segment family -> canonical start pose the frame probe settles at.
    # walk/hold/track/lower episodes all reset at the plant; rise resets
    # belly-flat (the instrument's post-lower rise uses
    # force_rise_start="flat" — eval_modeseq.reanchor_to).
    SEQ_FRAME_FAMILY = {"rise": "belly", "walk": "plant", "hold": "plant",
                        "track": "plant", "lower": "plant"}

    def _seq_capture_frames(self) -> None:
        """Settle-probe the canonical segment frames for this episode's
        model (called from reset() BEFORE the episode's own placement,
        which wipes the probe physics). Each probe replays the exact
        reset choreography (place -> slip stiff settle -> slip limp
        settle -> capture nominal -> hold settle) at the family's
        canonical start pose, and records the reference frame a FRESH
        episode of that family would get: q_nom, _z0, pad-z ref. These
        are the eval_handoff/reanchor_to() mechanics — the composition-
        proven switch context both eval instruments derive via a full
        env.reset() — reproduced in-env so mid-episode switches see the
        identical frame. No rng draws (legacy streams bit-exact)."""
        frames: dict = {}
        for fam, q_probe in (
                ("plant", self._logical_to_mujoco_q(
                    self._clip_to_joint_limits(
                        self._plant_deg * DEG2RAD))),
                ("belly", np.zeros(N_JOINTS, dtype=float))):
            self._place_at_plant(q_probe)
            er = self._ep_rand
            self._profile = ServoProfile(
                self.params, q_probe,
                latency_scale=1.0 if er is None else er.latency_scale,
                deadband_scale=1.0 if er is None else er.deadband_scale,
                vel_scale=1.0 if er is None else er.vel_scale,
                latency_load_gain=(
                    None if er is None else er.latency_load_gain),
                latency_load_ref_nm=(
                    1.2 if er is None else er.latency_load_ref_nm),
            )
            if er is not None and np.any(er.joint_backlash_gap_rad > 0.0):
                self._backlash = JointBacklash(
                    er.joint_backlash_gap_rad,
                    load_gain=er.joint_backlash_load_gain,
                    load_ref_nm=er.joint_backlash_load_ref_nm)
                self._backlash.reset(q_probe)
            else:
                self._backlash = None
            self._backlash_prev_force[:] = 0.0
            self._cmd = self._mujoco_to_logical_q(q_probe)
            fr = self.model.geom_friction[:, 0].copy()
            self.model.geom_friction[:, 0] = self.SLIP_MU
            self._settle(0.4)
            self._settle(0.5, limp=True)
            self.model.geom_friction[:, 0] = fr
            q_nom_mujoco = self.data.qpos[self._qadr].copy()
            q_nom = self._mujoco_to_logical_q(q_nom_mujoco)
            self._profile.reset(q_nom_mujoco)
            if self._backlash is not None:
                self._backlash.reset(q_nom_mujoco)
            self._cmd = q_nom.copy()
            self._settle(0.3)
            frames[fam] = {
                "q_nom": q_nom,
                "z0": float(self.data.xpos[self._chassis_bid, 2]),
                "pad_z_ref": np.array(
                    [float(self.data.xpos[b, 2]) if b >= 0 else 0.0
                     for b in self._pad_bids]),
            }
        self._seq_frames = frames

    def _seq_maybe_switch(self) -> None:
        """Mid-episode mode switch (called once per tick, immediately
        after _step_i advances and BEFORE the goal is read). At each
        planned boundary: install the new segment family's CANONICAL
        reference frame (q_nom / _z0 / pad-z ref from the settle probe
        — exactly what eval_handoff/reanchor_to() derive via a fresh
        reset of the target mode), regenerate the refs with a blend
        window, and re-derive the goal-derived episode bookkeeping.
        Physics, servo/profile state, tilt frame and the safety layer's
        slew memory all carry over — on hardware a mode command changes
        no physical state, and the proven reanchor mechanics explicitly
        restore them across the switch.

        HISTORY (trans-dagger2 kill, 08-14): v1 of this switch kept the
        EPISODE-reset q_nom and re-based _z0 on the instantaneous
        chassis height. Since obs joints are (q - q_nom), a rise-start
        sequence fed every later plant-family segment a belly frame
        (~79 deg off at the knees) — footlow2_hard1 fell 99/225 demo
        sequences in-env (lower 73) while scoring 11/12 zero-fall on
        the instrument, whose frames come from reanchor_to(). The
        canonical-frame install below is the fix."""
        nxt = self._seq_idx + 1
        if self._seq_plan is None or nxt >= len(self._seq_plan):
            return
        seg = self._seq_plan[nxt]
        if self._step_i < int(seg["tick"]):
            return
        i0 = int(seg["tick"])
        frame = (self._seq_frames or {}).get(
            self.SEQ_FRAME_FAMILY[str(seg["mode"])])
        if frame is None:
            raise RuntimeError(
                "goal.mode_seq: canonical segment frames missing — "
                "neither reset() (_seq_capture_frames) nor the MJX "
                "choreography (MjxVecEnv._mint_seq_frames, the batched "
                "twin landed 08-14) minted them before the first "
                "switch. This is an invariant violation, not a "
                "missing-feature guard; see TRANSITIONS_DIRECTIVE.")
        # Old ABSOLUTE refs at the boundary (blend origin).
        g_old = self._goal_traj.at(self._step_i)
        old_abs_h = self._z0 + g_old.height_ref
        old_r, old_p = g_old.roll_ref, g_old.pitch_ref
        # Install the new segment family's canonical frame (lesson 5:
        # rise-after-lower must NOT aim at a stale frame — and the
        # trans-dagger2 lesson above: the frame must be the one the
        # specialists trained in, not the episode's start frame).
        self._z0 = float(frame["z0"])
        self._q_nom = frame["q_nom"].copy()
        self._pad_z_ref = frame["pad_z_ref"].copy()
        traj, h_target, ramp_i0 = self._seq_segment_traj(
            str(seg["mode"]), i0)
        # Blend window: refs continuous in ABSOLUTE terms across the
        # switch (engagement-snap lesson 6 — never hand the policy a
        # step-change reference at a control handoff).
        b = int(seg.get("blend", 0))
        if b > 0:
            n = len(traj.height)
            s = np.clip((np.arange(n) - i0 + 1.0) / float(b), 0.0, 1.0)
            s[:i0] = 0.0   # pre-switch region, never read again
            dh = old_abs_h - self._z0
            traj.height = (1.0 - s) * dh + s * np.asarray(traj.height,
                                                          dtype=float)
            traj.roll = (1.0 - s) * old_r + s * np.asarray(traj.roll,
                                                           dtype=float)
            traj.pitch = (1.0 - s) * old_p + s * np.asarray(traj.pitch,
                                                            dtype=float)
        self._goal_traj = traj
        self._seq_idx = nxt
        self._seg_entry_step = self._step_i
        self._seq_seg_end = (int(self._seq_plan[nxt + 1]["tick"])
                             if nxt + 1 < len(self._seq_plan)
                             else int(self.episode_steps))
        self._seq_reset_mode_state(str(seg["mode"]), ramp_i0, h_target)

    def _seq_reset_mode_state(self, mode: str, ramp_i0: int,
                              h_target: float) -> None:
        """Re-derive the goal-derived per-episode bookkeeping for a new
        segment (the exact set _reset_finalize derives from the goal —
        milestones/ratchets restart so a segment can never inherit
        another segment's income baseline; SNAP_ATTRS lesson)."""
        self._h_target = float(h_target)
        self._h_milestones = set()
        self._prev_h_err_abs = 0.0
        self._score_best = None
        self._lower_score_best = None
        self._is_rise = mode == "rise"
        self._is_getup = False
        self._getup_best = None
        self._is_recover = False   # recover never occurs mid-sequence
        self._rec_phi_prev = None
        self._rec_hold_n = 0
        self._is_hold_bc = mode in ("hold", "track")
        self._is_lower_bc = mode == "lower"
        self._rise_ramp_i0 = int(ramp_i0)
        self._lower_ramp_i0 = int(ramp_i0)
        self._lower_gate_freeze_ticks = 0
        self._rsi_pending = False
        self._rsi_ref_tick0 = None
        self._end_posture_from = None
        self._curl_dist_prev = self._curl_dist()
        self._curl_milestones = set()
        self._rise_gate_freeze_ticks = 0
        self._pretuck_latched = False
        self._decouple_latched = False
        self._rise_h_prev = None
        self._prev_current_rate = None
        # Hold/lower BC anchors mid-sequence use q_nom directly — which
        # the switch just re-based to the CANONICAL plant frame, i.e.
        # exactly the settled-plant base a fresh single-mode hold/lower
        # episode anchors at (and the frame the stance teachers were
        # trained against). The v1 "pose carried INTO the segment"
        # anchor existed to dodge the belly episode-q_nom trap; with
        # per-switch canonical frames that trap is gone and the carried
        # pose (mid-stride after a walk segment) would anchor WORSE
        # than the teachers' own base. Kept as an attr (always None)
        # for SNAP_ATTRS/pool compatibility.
        self._seq_pose_anchor = None
        self._walk_bc_gait = None
        self._walk_bc_gait_alt = None
        self._walk_bc_t = 0.0
        if (mode == "walk"
                and ((float(cfg_get(self.cfg, "train", "bc_anchor_coef",
                                    default=0.0)) > 0.0
                      and float(cfg_get(self.cfg, "train", "bc_anchor_walk",
                                       default=1.0)) > 0.0)
                     # assistfade rung-3 residual fade — see _step_begin.
                     or float(cfg_get(self.cfg, "goal",
                                      "walk_residual_gate",
                                      default=0.0)) > 0.0)):
            self._walk_bc_gait = self._make_walk_bc_gait()
            if float(cfg_get(
                    self.cfg, "train", "bc_anchor_multiteacher_blend",
                    default=0.0)) > 0.0:
                self._walk_bc_gait_alt = self._make_walk_bc_gait()

    def _minload_min_force_now(self, floor_n: float) -> float:
        """Worst (min-over-feet) touch force right now, the quantity the
        hold_min_load termination/price EMA tracks. A foot with no touch
        sensor (adr<0) falls back to the clearance test used elsewhere
        in this file (clear > foot_down_mm => "up" => scored unloaded,
        else scored comfortably above the floor). Factored out 09-04 so
        the reset-time EMA seed (hold_min_load_ema_continuous) and the
        per-tick update read the identical measurement."""
        forces_now = []
        for i in range(6):
            if self._touch_adr[i] >= 0:
                forces_now.append(max(float(
                    self.data.sensordata[self._touch_adr[i]]), 0.0))
            else:
                clear_i = (float(self.data.xpos[self._pad_bids[i], 2])
                           - self._pad_z_ref[i])
                forces_now.append(
                    0.0 if clear_i > PLANT_SPEC["foot_down_mm"] * 0.001
                    else floor_n * 2.0)
        return min(forces_now)

    def _step_finish(self, ctx):
        """Post-physics half of step: state read, reward, obs."""
        clipped, terminated, status, pen = ctx
        self._state = self._read_state()
        self._step_i += 1
        if getattr(self, "_seq_plan", None) is not None:
            self._seq_maybe_switch()
        self._rise_gate_tick()
        self._lower_gate_tick()
        goal = self._current_goal()
        h_err = None
        h_rel = float(self.data.xpos[self._chassis_bid, 2]) - self._z0
        terminated = collapse_terminations(self, h_rel, status, terminated)
        (minload_short_k, minload_in_hold, minload_floor_n,
         terminated) = hold_minload_termination(self, status, terminated)
        terminated = walk_idle_and_leg_duty_terminations(self, status,
            terminated)
        unload_f = None
        if goal is not None:
            # GETUP mode has no height reference at all: its staged
            # stand score (walk_task._post_step) replaces the height
            # kernel/shaping. Feeding h_err = h_rel here would CHARGE
            # standing up away from the settled spawn height — the
            # exact opposite of the task. RECOVER (08-15) has the
            # identical shape: its potential Phi prices height, and
            # the spawn-anchored h_err would charge every honest rise
            # (measured -58/ep on the reference rise replay).
            if not (getattr(self, "_is_getup", False)
                    or getattr(self, "_is_recover", False)):
                h_err = h_rel - goal.height_ref
            if goal.unload_leg is not None:
                adr = self._touch_adr[int(goal.unload_leg)]
                if adr >= 0:
                    unload_f = float(self.data.sensordata[adr])
        # Quiet-stance gate: the reference is stationary when this tick's
        # refs match last tick's (holds, and the flat top of every ramp).
        ref_quiet = True
        if goal is not None and self._goal_traj is not None:
            prev_g = self._goal_traj.at(self._step_i - 1)
            ref_quiet = (
                abs(goal.roll_ref - prev_g.roll_ref) < 1e-9
                and abs(goal.pitch_ref - prev_g.pitch_ref) < 1e-9
                and abs(goal.height_ref - prev_g.height_ref) < 1e-9)
        reward, parts = compute_reward(self.cfg, self._state, clipped,
                                       self._prev_action, goal=goal,
                                       tilt_ref=self._tilt_ref0,
                                       height_err=h_err,
                                       unload_force_n=unload_f,
                                       ref_quiet=ref_quiet,
                                       prev_prev_action=self._prev_prev_action)
        reward = hold_still_gate_reward(self, goal, parts, ref_quiet, reward)
        reward = hold_minload_shortfall_reward(self, minload_floor_n,
            minload_in_hold, minload_short_k, parts, reward)
        transition_foot_drag_metric(self, parts)
        lower_score_mode, depth_frac, reward = rise_scored_steps_reward(self,
            goal, h_err, h_rel, parts, reward)
        reward = rise_curl_reward(self, goal, h_rel, parts, reward)
        reward = rise_ref_track_reward(self, parts, reward)
        reward = current_penalties(self, parts, reward)
        reward = posture_support_load_headroom_reward(self, goal, parts,
            reward)
        mode_now, reward = stance_shaping_reward(self, clipped, goal, parts,
            reward)
        reward = end_posture_reward(self, goal, mode_now, parts, reward)
        reward = terminal_settlement_reward(self, depth_frac,
            lower_score_mode, parts, pen, reward, terminated)
        reward = rise_curl_only_pretrain_reward(self, parts, reward)
        truncated = self._step_i >= self._active_episode_steps()
        self._prev_prev_action = self._prev_action
        self._prev_action = clipped.copy()
        info = {"termination_reason": status.reason, **parts,
                "safety_ok": status.ok,
                "roll_deg": self._state.imu_roll * RAD2DEG,
                "pitch_deg": self._state.imu_pitch * RAD2DEG,
                "roll_rel_deg": (self._state.imu_roll
                                 - self._tilt_ref0[0]) * RAD2DEG}
        if self._sched_value is not None:
            # Live scheduled-coefficient value — auto-logged to W&B as
            # env/sched_value by the trainers' info-scalar sweep, so
            # triage can see WHERE on the ramp a behavior change lands.
            info["sched_value"] = float(self._sched_value)
        bc_anchor_target(self, info)
        if self._state.servo_current is not None:
            info["mean_current_a"] = float(
                np.mean(np.abs(self._state.servo_current)))
            info["max_current_a"] = float(
                np.max(np.abs(self._state.servo_current)))
        if goal is not None:
            info["goal_mode"] = self._goal_traj.mode
            info["roll_ref_deg"] = goal.roll_ref * RAD2DEG
            info["pitch_ref_deg"] = goal.pitch_ref * RAD2DEG
            info["track_err_deg"] = math.hypot(
                self._state.imu_roll - self._tilt_ref0[0] - goal.roll_ref,
                self._state.imu_pitch - self._tilt_ref0[1] - goal.pitch_ref
            ) * RAD2DEG
            info["height_mm"] = h_rel * 1000.0
            info["height_ref_mm"] = goal.height_ref * 1000.0
            if self._is_rise:
                # Per-tick start_kind (flat/bridge/crouch/...), the
                # SAME shared derivation eval_checkpoint.py's own
                # `_start_kind()` uses for eval-report labeling
                # (rl_move.env.start_kind_of, extracted 2026-09-14
                # after finding this line's original plain
                # `getattr(self._goal_traj, "start_kind", None)` always
                # returned None -- rise/lower/hold trajectories never
                # set a literal `.start_kind` attribute, only getup/
                # recover do -- silently disabling
                # goal_mode_batch_split.py's rise-start_kind sub-split
                # the whole time it was "engaged"; see start_kind_of's
                # own docstring for the full bug writeup). Exposed here
                # (rise only) purely as a labeling channel for that
                # lever: a NEW-VALUE info key, never read by reward/
                # obs/termination, inert (no reward/physics/obs
                # change) for every run that doesn't consume it.
                info["start_kind"] = start_kind_of(self._goal_traj)
                # Two-phase rise sub-goal observability
                # (goal.rise_curl_gate): nonzero whenever the height
                # ramp's onset is currently being deferred waiting on
                # the curl-to-bridge sub-goal -- the direct telltale
                # that the mechanism is actually firing (env/rise_gate_
                # freeze_ticks in W&B), unlike the prior income-price
                # gate's factor, which stayed pinned at 1.0 the whole
                # `risecurlgate-s1-canary2m` run despite being "on".
                info["rise_gate_freeze_ticks"] = float(
                    self._rise_gate_freeze_ticks)
            elif getattr(self._goal_traj, "mode", "") == "walk":
                # WALK-START_KIND (2026-09-23, standwalk walk-entry
                # composed-session gap: two blend-fraction mechanisms
                # -- goal.walk_entry_bank position-only and its
                # goal.bank_qvel_restore position+velocity sibling --
                # both refuted 2/2 doses; the track's own named next
                # lever is a DISCRETE first-class start_kind curriculum
                # band, mirroring rise's flat/bridge/crouch sub-split
                # above, rather than another blend dose). Same
                # inert-by-default contract as the rise branch: a
                # NEW-VALUE info key, never read by reward/obs/
                # termination, only consumed by goal_mode_batch_split.
                # py's WALK-START_KIND sub-split when that (also
                # default-off) flag is armed.
                info["start_kind"] = start_kind_of(self._goal_traj)
            if self._is_lower_bc:
                # Staged-descent sub-goal observability
                # (goal.lower_stage_gate): nonzero whenever the height
                # ramp is currently being deferred waiting on the
                # planted-fraction sub-goal — the direct telltale that
                # the mechanism is firing (env/lower_gate_freeze_ticks
                # in W&B), same convention as the rise gate's own
                # counter above.
                info["lower_gate_freeze_ticks"] = float(
                    self._lower_gate_freeze_ticks)
            if h_err is not None:   # getup mode has no height ref
                info["height_err_mm"] = h_err * 1000.0
            if unload_f is not None:
                info["unload_force_n"] = unload_f
        return (self._final_obs(
                    build_obs(self.cfg, self._state, self._q_nom,
                              self._prev_action, goal=goal,
                              tilt_ref=self._tilt_ref0,
                              height_vel_mps=self._height_vel_mps),
                    reset=False),
                float(reward), terminated, truncated, info)

    def render(self):
        if self.render_mode != "rgb_array":
            return None
        mujoco = self._mujoco
        if self._renderer is None:
            self._renderer = mujoco.Renderer(self.model, 480, 640)
            self._cam = mujoco.MjvCamera()
            self._cam.distance = 0.7
            self._cam.elevation = -25.0
            self._cam.azimuth = 130.0
        self._cam.lookat[:] = self.data.xpos[self._chassis_bid]
        self._renderer.update_scene(self.data, camera=self._cam)
        # Decorative command cues are added after mjv_updateScene (which
        # rebuilds the scene each frame), so they appear in policy videos,
        # OpenCV players, and the web app's browser frames without touching
        # physics.
        draw_env_command_indicator(self, self._renderer.scene)
        return self._renderer.render()

    def close(self):
        if self._renderer is not None:
            # mujoco.Renderer only gained close() in 3.x; fall back to GC.
            if hasattr(self._renderer, "close"):
                self._renderer.close()
            self._renderer = None


def make_env(**kwargs):
    """Factory for SB3 ``make_vec_env``."""
    def _thunk():
        return SimHexapodBalanceEnv(**kwargs)
    return _thunk


if __name__ == "__main__":
    env = SimHexapodBalanceEnv(randomize=True, seed=0)
    obs, info = env.reset()
    print(f"obs {obs.shape} roll={info['roll_deg']:+.2f}° "
          f"pitch={info['pitch_deg']:+.2f}°")
    t0 = time.monotonic()
    ret = 0.0
    for i in range(env.episode_steps):
        obs, r, term, trunc, info = env.step(np.zeros(N_ACT))
        ret += r
        if term or trunc:
            break
    print(f"zero-action episode: steps={i + 1} return={ret:.3f} "
          f"roll={info['roll_deg']:+.2f}° pitch={info['pitch_deg']:+.2f}° "
          f"({time.monotonic() - t0:.2f}s wall)")
