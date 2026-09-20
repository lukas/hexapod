"""Per-episode domain randomization for the sim twin.

Randomizes exactly the quantities we cannot pin down (or that drift):

Physics / geometry (mutated on the loaded MjModel — no XML rebuild):
- chassis mass / CoM (battery position, wiring) + per-link mass jitter
- leg geometry: global link-length scale (print / CAD error) and
  independent per-leg per-segment variation (assembly tolerance).
  The policy-side IK keeps NOMINAL lengths — the mismatch is the point.
- foot / ground friction, contact compliance (table vs. carpet)
- ground slope (tilted gravity vector)
- actuator kp / kv scale (unit-to-unit servo spread), torque/voltage scale

Actuation / sensing (applied in the env, not the model):
- command latency, deadband, velocity-ceiling scale, dropped SyncWrites
- joint zero bias (encoder / set_zero error — the thing that bit us on
  2026-08-06), encoder noise
- IMU mount misalignment (random rotation chassis→IMU, hits tilt AND
  gyro), tilt/gyro bias + noise
- IMU mount POSITION (the IMU could be bolted anywhere on the robot).
  Position doesn't change static tilt, but an off-center IMU feels
  lever-arm accelerations whenever the body rotates, corrupting the
  accel-derived tilt exactly while the robot is leaning. The sim env
  computes the accelerometer at the randomized point so this shows up.
- action noise

Ranges are data-driven where possible: ``DomainRandomizer.from_params``
widens kp/kv/latency ranges using the measured joint-to-joint spread that
``fit_motor_model.py`` stores in ``sim_model.json``; everything else uses
the conservative defaults below.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field, replace

import numpy as np

from .servo_model import AXES, N_JOINTS, SimServoParams
from hexapod_core.joint_frame import leg_joints

DEG2RAD = math.pi / 180.0
N_LEGS = 6
G0 = 9.80665
# Cap on the load-coupling multiplier in JointBacklash.apply (see
# RandRanges.joint_backlash_load_gain) -- keeps a large load spike from
# blowing the gap up unboundedly; 4x the reference load is already a
# generous stance-to-shove range.
JOINT_BACKLASH_LOAD_CAP = 4.0

# Structured hard-region DR dose menu (dr.struct_dr_prob, 2026-09-13
# speed sim-to-real order). Values are the frozen-policy joint panel's
# PanelBounds (rl_move/sim/probe_dr_joint_panel.py, run
# logs/ckpt_eval/dr_joint_panel_20260913, doc
# docs/DR_JOINT_PANEL_2026-09-13.md); the emphasis directions are that
# panel's measured hard-region correlations with ps200 peak roll:
# per-joint kp spread +0.84, FRAME-COUPLED zero bias +0.77, CoM +0.59,
# cmd-drop +0.53, ground tilt +0.46, contact stiffness +0.45, per-foot
# friction / per-leg torque asymmetry -0.59/-0.46. Doses are FIXED
# evidence, not a cfg surface (same convention as the tipped/fault dose
# menus: probability follows the curriculum, the dose does not).
STRUCT_KP_PCT = 0.35
STRUCT_KV_PCT = 0.40
STRUCT_ZERO_BIAS_DEG = 5.0
STRUCT_COM_XY_M = 0.025
STRUCT_CMD_DROP = (0.0, 0.08)
STRUCT_CONTACT_STIFF = (0.50, 3.00)
STRUCT_TILT_DEG = 3.0
STRUCT_FOOT_FRICTION = (0.50, 1.10)
STRUCT_LEG_TORQUE = (0.60, 1.05)
STRUCT_TORQUE = (0.55, 1.05)
STRUCT_VEL = (0.70, 1.10)
STRUCT_LATENCY = (0.70, 2.50)
STRUCT_DEADBAND = (0.50, 3.00)
STRUCT_MASS = (0.85, 1.25)
STRUCT_FRICTION = (0.45, 1.40)
STRUCT_LEG_MASS_PCT = 0.20
_STRUCT_LEFT = (0, 1, 2)
_STRUCT_RIGHT = (3, 4, 5)
_STRUCT_FRONT = (0, 5)
_STRUCT_REAR = (2, 3)

# Valid dr.joint_backlash_group names (see RandRanges.joint_backlash_group).
BACKLASH_GROUPS = (
    "left", "right", "front", "rear",
    "yaw", "pitch", "knee",
    "leg0", "leg1", "leg2", "leg3", "leg4", "leg5",
)
_BACKLASH_LEG_GROUPS = {
    "left": _STRUCT_LEFT, "right": _STRUCT_RIGHT,
    "front": _STRUCT_FRONT, "rear": _STRUCT_REAR,
}
_BACKLASH_AXIS_GROUPS = {"yaw": 0, "pitch": 1, "knee": 2}


def dof_group_mask(group: str, *, param_name: str = "joint_backlash_group"
                    ) -> np.ndarray:
    """(N_JOINTS,) bool mask for a named leg/axis/compound joint group.

    Generic form of the mask ``dr.joint_backlash_group`` introduced
    (2026-09-14): "" -> all-True (legacy: every joint independently
    dosed). Leg groups ("left"/"right"/"front"/"rear"/"legN") set all 3
    axes of the named leg(s); axis groups ("yaw"/"pitch"/"knee") set that
    axis across all 6 legs. A "leg_group+axis_group" compound name
    intersects the two masks, e.g. "right+knee" = only the knee joint of
    the 3 right legs (3 of 18 joints, not 9). Raises on an unrecognized
    name -- fail loud, never silently dose nothing. ``param_name`` is
    only used to name the offending cfg field in the error message (so a
    caller other than joint_backlash_group, e.g. latency_load_group,
    reports itself correctly); the group vocabulary/semantics are shared.
    """
    if not group:
        return np.ones(N_JOINTS, dtype=bool)
    if "+" in group:
        parts = group.split("+")
        if len(parts) != 2:
            raise ValueError(f"unknown {param_name}: {group!r}")
        leg_part, axis_part = parts
        if leg_part not in _BACKLASH_LEG_GROUPS and not (
                leg_part.startswith("leg") and leg_part[3:].isdigit()):
            raise ValueError(f"unknown {param_name}: {group!r}")
        if axis_part not in _BACKLASH_AXIS_GROUPS:
            raise ValueError(f"unknown {param_name}: {group!r}")
        return (dof_group_mask(leg_part, param_name=param_name)
                & dof_group_mask(axis_part, param_name=param_name))
    mask = np.zeros(N_JOINTS, dtype=bool)
    if group in _BACKLASH_LEG_GROUPS:
        for leg in _BACKLASH_LEG_GROUPS[group]:
            mask[3 * leg:3 * leg + 3] = True
    elif group in _BACKLASH_AXIS_GROUPS:
        mask[_BACKLASH_AXIS_GROUPS[group]::3] = True
    elif group.startswith("leg") and group[3:].isdigit():
        leg = int(group[3:])
        if not (0 <= leg < N_LEGS):
            raise ValueError(f"{param_name} leg index out of range: {group!r}")
        mask[3 * leg:3 * leg + 3] = True
    else:
        raise ValueError(f"unknown {param_name}: {group!r}")
    return mask


def backlash_group_mask(group: str) -> np.ndarray:
    """(N_JOINTS,) bool mask for ``dr.joint_backlash_group``.

    Thin wrapper around ``dof_group_mask`` kept for the original call
    sites/tests -- see that function's docstring for the group
    vocabulary. Error messages are byte-identical to the pre-refactor
    version (both name ``joint_backlash_group``).
    """
    return dof_group_mask(group, param_name="joint_backlash_group")


def leg_group_mask(group: str, *, param_name: str = "foot_stickslip_group"
                    ) -> np.ndarray:
    """(N_LEGS,) bool mask for a named LEG-only group.

    Per-foot mechanisms (friction, not a joint axis) have no "yaw/pitch/
    knee" concept -- only the leg groups from ``dof_group_mask``'s
    vocabulary apply (left/right/front/rear/legN). "" -> all-True (every
    leg drawn independently, the historical default). Raises on an
    axis-only or compound name -- fail loud rather than silently
    stripping the axis part.
    """
    if not group:
        return np.ones(N_LEGS, dtype=bool)
    if group in _BACKLASH_LEG_GROUPS:
        mask = np.zeros(N_LEGS, dtype=bool)
        for leg in _BACKLASH_LEG_GROUPS[group]:
            mask[leg] = True
        return mask
    if group.startswith("leg") and group[3:].isdigit():
        leg = int(group[3:])
        if not (0 <= leg < N_LEGS):
            raise ValueError(f"{param_name} leg index out of range: {group!r}")
        mask = np.zeros(N_LEGS, dtype=bool)
        mask[leg] = True
        return mask
    raise ValueError(f"unknown {param_name}: {group!r} (leg groups only: "
                      "left/right/front/rear/leg0..leg5)")


def stickslip_friction_mult(speed_mps, vel_ref_mps: float, gain):
    """Coulomb stick-slip friction multiplier for a foot's ground contact.

    Classic textbook picture: STATIC friction (foot planted, near-zero
    sliding speed) exceeds KINETIC friction (foot actively sliding) by a
    fraction ``gain``. ``dr.foot_friction_scale`` already carries the
    per-episode KINETIC/baseline coefficient (the historical, always-on
    mechanism); this returns the EXTRA multiplier on top of that
    baseline, ramping from ``1+gain`` at zero sliding speed down to
    exactly ``1.0`` (pure baseline) once ``|speed|>=vel_ref_mps`` --
    linear ramp, mirrors ``curl_height_cap_frac``'s own ramp shape/
    testability convention. ``vel_ref_mps<=0`` degenerates to the SAFE
    (inert) value -- always ``1.0``, never a permanently-stuck extra
    boost -- consistent with every other guard in this module resolving
    a misconfiguration toward the historical no-op rather than an
    extreme.
    """
    speed = np.asarray(speed_mps, dtype=float)
    gain = np.asarray(gain, dtype=float)
    if vel_ref_mps <= 0.0:
        frac = np.zeros_like(speed)
    else:
        frac = np.clip(1.0 - np.abs(speed) / float(vel_ref_mps), 0.0, 1.0)
    return 1.0 + gain * frac

# Adaptive/adversarial hard-case sampler (dr.struct_dr_adaptive, speed
# track, 2026-09-14 — the DR-composition panel's own next-named lever
# after CTRL/WIDE/STRUCT/COMBO all closed, see STATUS.md 09-13 ~21:5x):
# named "stories" the struct overlay can draw, granular enough to bias
# sampling toward whichever region the CURRENT policy is currently
# worst on (an online per-episode regret bandit), rather than a fixed
# offline hard region. "correlated" collapses the panel's battery-sag/
# worn-leg/mass/floor latent story into one bucket (it does not itself
# subdivide); "asymmetric" splits by the group actually perturbed so a
# single systematically-bad group (e.g. one side) can be up-weighted
# independently of the others. Order is arbitrary but fixed (used as a
# stable dict key set, never as an index).
STRUCT_STORIES = (
    "correlated",
    "asym_left", "asym_right", "asym_front", "asym_rear", "asym_single",
)

# Frozen-joint DOF damping (N·m·s/rad). Seized-gearbox approximation:
# implicit (unconditionally stable) viscous lock. Against the fitted
# joint kv range (0.02-3.0) this is a 150-25000x stiffening; measured
# creep under a worst-case full-body drop-settle load is ~0.05 rad
# over 2 s (bent knee, whole robot landing on it) and far less under
# ordinary stance loads — effectively frozen at episode (15-60 s)
# scale with zero stepper changes (dof_damping is per-world model DR).
FROZEN_DOF_DAMPING = 500.0


def _rot_rpy(roll: float, pitch: float, yaw: float) -> np.ndarray:
    cr, sr = math.cos(roll), math.sin(roll)
    cp, sp = math.cos(pitch), math.sin(pitch)
    cy, sy = math.cos(yaw), math.sin(yaw)
    rx = np.array([[1, 0, 0], [0, cr, -sr], [0, sr, cr]])
    ry = np.array([[cp, 0, sp], [0, 1, 0], [-sp, 0, cp]])
    rz = np.array([[cy, -sy, 0], [sy, cy, 0], [0, 0, 1]])
    return rz @ ry @ rx


@dataclass
class RandRanges:
    """Half-widths / bounds for each randomized quantity."""
    mass_scale: tuple[float, float] = (0.85, 1.20)
    com_offset_m: float = 0.012          # chassis CoM shift, each of x/y
    leg_mass_jitter_pct: float = 0.10    # per leg-link, on top of mass_scale
    link_len_scale_pct: float = 0.02     # global print/CAD length error
    link_len_leg_pct: float = 0.012      # per-leg per-segment assembly spread
    friction_scale: tuple[float, float] = (0.6, 1.4)
    contact_stiff_scale: tuple[float, float] = (0.7, 2.0)  # solref timeconst
    ground_tilt_deg: float = 2.0         # floor slope via gravity vector
    kp_scale_pct: float = 0.20           # ± around fitted kp, per joint
    kv_scale_pct: float = 0.25
    torque_scale: tuple[float, float] = (0.80, 1.05)  # battery sag / spread
    latency_scale: tuple[float, float] = (0.7, 1.8)
    deadband_scale: tuple[float, float] = (0.5, 1.8)
    vel_scale: tuple[float, float] = (0.85, 1.10)
    cmd_drop_prob_max: float = 0.05      # lost SyncWrite per control tick
    # Start pose: how the human placed the robot this episode.
    placement_noise_deg: float = 2.0     # per-joint hand-placement slop
    bad_start_prob: float = 0.25         # episodes with badly-off joints
    bad_start_max_joints: int = 3        # how many joints can be way off
    bad_start_deg: tuple[float, float] = (8.0, 35.0)  # offset magnitude
    joint_zero_bias_deg: float = 1.0     # per-joint set_zero error
    # Logical-zero drift frame (operator directive 08-10, GPT handoff §7):
    # 0 = legacy, zero bias corrupts only the ENCODER READS — but that
    # leaves a permanent cmd-vs-read residual the policy can exploit,
    # which hardware never shows. 1 = the bias is a FRAME SHIFT: position
    # commands are translated into the same drifted frame the reads come
    # from (set_zero done on a slumped pose shifts BOTH). Reads and
    # commands stay self-consistent; the drift is only visible through
    # physics (gravity/contacts/IMU) — exactly the failure that dropped
    # the robot on 08-09. Flag, not a range: never scaled by dr-scale.
    zero_drift_cmd_frame: float = 0.0
    encoder_noise_deg: float = 0.09      # ~1 LSB of the 12-bit encoder
    # IMU could be installed anywhere: gross orientation is canonicalized
    # once by imu_calibrate, so rotation DR covers the RESIDUAL error;
    # position DR covers the full plausible mounting envelope (chassis
    # deck to raised platform) because no calibration removes lever-arm
    # acceleration effects.
    imu_mount_deg: float = 10.0          # residual mount rotation after calib
    imu_pos_xy_m: float = 0.07           # mount offset from chassis center
    imu_pos_z_m: tuple[float, float] = (-0.02, 0.10)  # below deck … platform
    imu_bias_deg: float = 1.0            # extra roll/pitch bias (calib error)
    tilt_noise_deg: float = 0.3
    gyro_bias_deg_s: float = 0.5
    gyro_noise_deg_s: float = 0.5
    action_noise: float = 0.02
    # Tipped start (roll recovery) — default ON everywhere, operator
    # ruling 08-10 after the dep-vref1-r1 hardware walk rolled away
    # monotonically to the 25° trip with zero corrective response
    # (rl_docs/HARDWARE.md "runaway roll"): plant-family episodes
    # sometimes BEGIN at a sustained body roll (asymmetric leg fold,
    # settled under gravity) while the tilt reference stays LEVEL, so
    # the policy sees the lean in obs and is paid to level out. Applied
    # in sim_env at plant/park starts only (never belly-rise), capped by
    # the run's safety envelope; see HexapodSimEnv._tipped_offset_rad.
    tipped_start_prob: float = 0.30
    tipped_start_deg: tuple[float, float] = (6.0, 18.0)  # target body roll
    # Rise rocking (hardware 08-11, bench_blast camera sessions; dose
    # + shape recalibrated 08-12 from open-loop replay of all 10
    # recorded stand failures — see sim_env._rise_rock_offset and
    # rl_move/sim/replay_trace.py): the real rise is FLAT through the
    # belly curl, then rolls 0→10.6° in the last ~1.2 s of the height
    # ramp as the belly unloads onto a near-diagonal foot pair, and
    # trips tilt_roll 10/10 at the same tick, while the sim's rise
    # stays ≤2.7° under BOTH actuator fits (joints track the tapes at
    # ~1° RMSE; μ 2→50 and CoM shifts to 10 mm change nothing — the
    # gap is a support knife-edge, not actuator/friction/CoM). Axis:
    # rise-mode episodes sometimes carry a one-side hip/knee fold bias
    # on the PHYSICAL servo command, RAMP-GATED by rise progress
    # (sim_env._rise_rock_offset; same fold→roll mapping as the
    # tipped start). Encoders read the true (drooped) angles and the
    # tilt reference stays level, so the policy is paid to close the
    # command-vs-read loop and level out — the exact skill the
    # hardware curl demands. Replay calibration: ~18° dose crosses
    # the 10° trip band with the recorded failure's own shape on the
    # branch that removes the catching foot. Default OFF (opt-in via
    # dr.rise_rock_*).
    rise_rock_prob: float = 0.0
    rise_rock_deg: tuple[float, float] = (8.0, 18.0)     # target body roll
    # Walk takeoff kick (hardware 08-11, bench_report over 18 walks):
    # EVERY hardware walk crosses 5° roll within 0.6-1.5 s of gait
    # start and peaks 13-27°, at sustained roll RATES of 11-46 °/s
    # (median 24, p90 45; gyro spikes to ~90) — while sim plant-start
    # episodes take off level, so surviving the transient is luck.
    # Static leans do NOT close the gap (cw-dep-tip1-takeoff25-r1:
    # child==parent at the matched 20-25° dose, lever closed) — the
    # gap is dynamic. Axis: walk-mode episodes sometimes get a
    # TRANSIENT one-side fold pulse on the PHYSICAL servo command over
    # the first ~second of gait (sim_env._walk_kick_offset, half-sine
    # ramp in and out, net-zero terminal offset).
    # DOSE CEILING MEASURED 08-12 (replay_trace calibration session):
    # the fold pulse SATURATES — frozen-plant response is 5.4° peak at
    # a 14° draw, 6.8-9.8° at a 30° draw, roll rates capped ~10 °/s by
    # the planted opposite feet + the servo write profile. It CANNOT
    # reach the hardware takeoff regime at any dose, which retro-
    # explains cw-dep-tip1-kick1's 0/24-falls-both null: the arm never
    # tested the hypothesis. Kept for reproducibility; superseded by
    # dr.walk_push_* (base torque pulse) below.
    walk_kick_prob: float = 0.0
    walk_kick_deg: tuple[float, float] = (8.0, 18.0)     # peak target roll
    walk_kick_s: tuple[float, float] = (0.5, 1.2)        # pulse duration
    # Walk takeoff PUSH (08-12, the mechanism the kick could not
    # deliver): half-sine roll TORQUE pulse on the chassis
    # (xfrc_applied) over the first ~second of walk-mode episodes —
    # a true roll-rate disturbance that bypasses the actuator path,
    # so it can reproduce the measured takeoff regime. Open-loop walk
    # replays (replay_trace on the 08-11 tapes) show the recorded
    # actions ALREADY rock the sim plant 8-25° — the transient is the
    # gait's own load transfer; this axis forces closed-loop rollouts
    # to visit those states instead of relying on takeoff luck.
    # Dose CALIBRATED policy-in-the-loop (tip1 walking fwd 0.05 m/s,
    # DR0 det, 08-12): the planted 6-foot stance absorbs any
    # plausible torque (2.2 Nm -> 0.2°) — the pulse lands when it
    # overlaps a tripod swing phase, so the duration must cover the
    # first gait cycle. 2.0 Nm/1.5 s: peaks 3-6°, no falls (soft);
    # 2.6 Nm/1.5 s: peaks {2.6, 3.2, 12.3, 30.2-fall} = the hardware
    # coin-flip regime, 5° crossings 0.56-0.76 s; 3.2 Nm: 3/4 falls
    # at 64-105 °/s (beyond the tapes' 11-46). Works on BOTH stacks:
    # C envs apply the xfrc in _advance; the MJX vec envs read each
    # shim's per-tick torque and hand it to the batched stepper
    # (plumbed 08-12). Default OFF (opt-in via dr.walk_push_*).
    walk_push_prob: float = 0.0
    walk_push_nm: tuple[float, float] = (2.0, 3.0)       # peak |torque|
    walk_push_s: tuple[float, float] = (0.8, 1.5)        # pulse duration
    # Recurrent form of the same chassis-roll disturbance (09-12 PS200
    # transfer probe). A positive period repeats the sampled pulse at this
    # cadence, beginning at walk_push_start_s; period 0 keeps the historical
    # takeoff-only t=0 pulse exactly. The dose is not curriculum-scaled, like
    # walk_push_nm/s. Ranges allow a training arm to randomize gait phase by
    # sampling start across one period without adding a second phase field.
    walk_push_repeat_period_s: tuple[float, float] = (0.0, 0.0)
    walk_push_start_s: tuple[float, float] = (0.0, 0.0)
    # Per-joint FAULT INJECTION (AMP brief §8; M0 checklist "fault
    # injection works"). With prob fault_prob an episode carries ONE
    # fault, drawn from fault_mix = (weakened joint, frozen joint,
    # disabled leg):
    #   - weakened: one joint's servo at fault_weak_scales strength
    #     (kp + torque limit scaled; 0.0 = dead servo, free-swinging
    #     against its kv backdrive damping);
    #   - frozen: one joint's actuator force zeroed and its DOF locked
    #     with FROZEN_DOF_DAMPING (seized-gearbox approximation — it
    #     creeps ~2 deg/15 s under a 0.5 N·m gravity load, close
    #     enough to "frozen at current position" at episode scale);
    #   - disabled leg: all 3 joints of one leg dead (scale 0.0).
    # Implementation is PURE MjModel field edits (actuator_gainprm/
    # biasprm/forcerange, dof_damping) — every touched field is in
    # mjx_backend.MODEL_DR_FIELDS, so the per-world model-DR upload
    # carries faults to the batched GPU stacks with ZERO stepper
    # changes. Default OFF (opt-in via dr.fault_*); the draw is
    # GUARDED so fault_prob=0 keeps the legacy rng stream bit-exact.
    fault_prob: float = 0.0
    fault_weak_scales: tuple[float, ...] = (0.7, 0.4, 0.2, 0.0)
    fault_mix: tuple[float, float, float] = (0.45, 0.25, 0.30)
    # Mid-episode external PUSH (AMP brief §7.4/§9.3, M3 push-recovery
    # curriculum). Distinct from dr.walk_push_* above (a fixed roll
    # TORQUE confined to the first ~1.5s that reproduces the measured
    # hardware TAKEOFF wobble): this is a random-direction horizontal
    # FORCE pulse fired once at a random point later in a walk-mode
    # episode, on a policy that is already walking, not taking off --
    # the actual "shove it mid-stride and see if it recovers" test the
    # brief and the M3/§9.3 cross-engine gate ask for ("recovers from
    # moderate pushes"). Half-sine ramp in/out like every pulse in this
    # file (net momentum, never a step discontinuity in xfrc). Direction
    # is drawn in the WORLD frame: walk episodes already visit every
    # heading via yaw-cmd, so a world-frame draw already covers
    # lateral/fore-aft/diagonal relative to the robot per brief §7.4
    # without needing a per-tick body-frame rotation. Default OFF
    # (opt-in via dr.ext_push_prob); guarded draw, same convention as
    # tipped/rock/kick/push/fault above (probability follows the
    # curriculum, the dose menu does not).
    ext_push_prob: float = 0.0
    ext_push_n: tuple[float, float] = (10.0, 25.0)       # peak |force| N
    ext_push_dur_s: tuple[float, float] = (0.15, 0.4)    # pulse duration
    ext_push_start_s: tuple[float, float] = (1.5, 9.0)   # delay from ep start
    # REPEATED pushes (M3 brief bar: "recovers from moderate pushes",
    # plural -- the mechanism above draws exactly ONE pulse/episode).
    # ext_push_repeat_max=1 (default) is the original single-push
    # behavior, byte-for-byte: the repeat-sampling branch below is only
    # entered when repeat_max>1, so it draws zero extra rng numbers and
    # stays bit-exact at the default. >1 draws that many independent
    # pulses (peak/dur/direction each redrawn from the SAME dose menus
    # above) spaced out in time so each one lands on a policy that has
    # had a chance to recover from the last: the Nth pulse starts
    # ext_push_gap_s after the (N-1)th ends, and sampling stops early
    # (fewer than repeat_max pulses that episode) once the next start
    # would land past ext_push_horizon_s -- a short/fast episode simply
    # gets fewer pulses rather than one crammed against the end. Same
    # convention as every dose menu here: this is a curriculum DOSE,
    # not scaled by DomainRandomizer.scaled(s) (only ext_push_prob is).
    ext_push_repeat_max: int = 1
    ext_push_gap_s: tuple[float, float] = (1.0, 3.0)
    ext_push_horizon_s: float = 13.0
    # Per-foot friction / per-leg torque-saturation asymmetry (2026-09-13
    # speed sim-to-real order; PanelBounds families the training DR never
    # had). Independent per-foot / per-leg draws inside the range; (1,1)
    # (the default) = OFF with a GUARDED draw (no rng consumed), keeping
    # the legacy stream bit-exact. Applied as pure MjModel field edits
    # (geom_friction rows + floor cap; actuator_forcerange rows) — both
    # fields are in mjx_backend.MODEL_DR_FIELDS so the per-world model-DR
    # upload carries them to the batched GPU stacks unchanged.
    foot_friction_scale: tuple[float, float] = (1.0, 1.0)
    leg_torque_scale: tuple[float, float] = (1.0, 1.0)
    # Structured hard-region DR (2026-09-13): with prob struct_dr_prob an
    # episode's base draw is OVERLAID with one correlated (battery-sag /
    # worn-leg / build-mass / floor latent stories) or asymmetric
    # (left/right/front/rear/single-leg group) ensemble drawn from the
    # STRUCT_* dose menu above — the joint panel's evidence-defined hard
    # region, including frame-coupled zero bias (zero_drift_cmd_frame
    # forced ON for the overlaid episode). 0.0 (default) = OFF, guarded
    # draw at the very END of sample() so the base stream is bit-exact.
    struct_dr_prob: float = 0.0
    # Dynamic, load-coupled joint BACKLASH (2026-09-14, speed track —
    # DR_JOINT_PANEL_2026-09-13's own escalation after CTRL/WIDE/STRUCT/
    # COMBO/ADAPT closed the whole bounded-STATIC-parameter family 0/5:
    # "very likely a DYNAMIC, load-coupled mechanism (series compliance/
    # backlash under load, servo-loop behavior under load, stick-slip)
    # that the simulator's parametric families do not express" — every
    # existing axis (kp/kv/torque/deadband/friction/etc.) is either a
    # constant-for-the-episode scale OR a symmetric always-on dead-zone
    # (dr.deadband_scale, already probed and refuted alone in
    # probe_ps200_transfer.py's "Deadband (backlash/post-encoder
    # compliance) dose" table — a uniform multiplier on the SAME
    # always-on dead-zone, not direction-reversal play). This is
    # different in kind: a classical mechanical BACKLASH (play) — the
    # actuator's effective setpoint only re-engages once the commanded
    # target has moved more than half the gap PAST the point of the last
    # direction reversal — whose gap WIDENS with the joint's own recent
    # load (a coarse stand-in for load-dependent series compliance /
    # stick-slip, since sim has no true gearbox/cable compliance model).
    # joint_backlash_deg: per-joint full-gap magnitude range (degrees),
    # sampled independently per joint per episode, like kp_scale_pct.
    # (0.0, 0.0) = OFF, guarded draw (no rng consumed), bit-exact.
    joint_backlash_deg: tuple[float, float] = (0.0, 0.0)
    # joint_backlash_load_gain: fraction the gap WIDENS per unit of
    # |actuator_force|/joint_backlash_load_ref_nm (capped at
    # JOINT_BACKLASH_LOAD_CAP); e.g. 1.0 = gap doubles at the reference
    # load. Sampled once per episode like the gap. (0.0, 0.0) = no load
    # coupling (a pure static-gap backlash), still guarded/bit-exact.
    joint_backlash_load_gain: tuple[float, float] = (0.0, 0.0)
    # Reference |force| (N*m-equivalent actuator-force units) that maps
    # to load_gain's "1 unit" of load. A modeling constant, not
    # randomized (never scaled by dr-scale, like zero_drift_cmd_frame) —
    # changing it changes what "full load" means, not how uncertain it
    # is. Small enough that ordinary stance/swing torques saturate it.
    joint_backlash_load_ref_nm: float = 1.2
    # joint_backlash_group: concentrate the gap on a NAMED subset of
    # joints instead of spreading it independently across all 18
    # (2026-09-14, speed track — the uniform-across-all-18 form of this
    # mechanism was probed NULL against the PS200 signature; the panel's
    # own hard-region correlation study names per-joint/per-leg
    # HETEROGENEITY, not global scale, as the strongest roll driver
    # (kp joint-to-joint spread +0.84), so an asymmetric/concentrated
    # dose is the next-named, untried form of the SAME mechanism, not a
    # new one). "" (default) = every joint drawn independently as
    # before, bit-exact (the mask is all-ones). Else one of
    # ``BACKLASH_GROUPS`` ("left"/"right"/"front"/"rear" leg groups,
    # "yaw"/"pitch"/"knee" axis groups, or "leg0".."leg5" a single leg's
    # 3 joints) — joints outside the named group are forced to zero gap
    # post-draw (same rng stream, same call count, purely a mask
    # multiply) so enabling/disabling this field never shifts any other
    # draw for a given seed.
    joint_backlash_group: str = ""
    # latency_load_gain / latency_load_ref_nm / latency_load_group
    # (2026-09-14, speed track): the SAME load-coupled, concentrated-
    # group recipe as joint_backlash_* above, applied to ServoProfile's
    # per-joint COMMAND LATENCY instead of positional play -- the design
    # note's OTHER named untried dynamic-mechanism candidate ("load-
    # coupled control-latency") after the backlash right-side/
    # intersection ladder plateaued at ~29-31% of the PS200 signature
    # (STATUS.md 2026-09-14 ~03:5x). Physical picture: a heavily loaded
    # joint's own position-sense-to-motion loop (SyncWrite backlog,
    # current-limited slew before the servo even begins moving) responds
    # SLOWER than an unloaded one, so bus/motion-start latency is not a
    # fixed per-episode draw but grows under load -- and concentrating
    # that growth on one side (heterogeneity, not global scale, per the
    # panel's own strongest roll correlate) is untried. Fraction the
    # per-joint latency WIDENS per unit of |actuator_force|/
    # latency_load_ref_nm (capped at servo_model.LATENCY_LOAD_FRAC_CAP).
    # (0.0, 0.0) = OFF, guarded (no rng consumed), bit-exact.
    latency_load_gain: tuple[float, float] = (0.0, 0.0)
    # Reference |force| mapping to "1 unit" of load -- a modeling
    # constant, not scaled by dr-scale (same convention as
    # joint_backlash_load_ref_nm/zero_drift_cmd_frame).
    latency_load_ref_nm: float = 1.2
    # "" (default) = every joint's load-coupling gain drawn independently
    # (bit-exact no-op at gain 0, same guarded-last-draw convention as
    # joint_backlash_deg); else one of BACKLASH_GROUPS (shared vocabulary,
    # see dof_group_mask) -- concentrates the SAME per-joint gain draw
    # onto a named leg/axis subset instead of spreading it across all 18.
    latency_load_group: str = ""
    # foot_stickslip_gain / foot_stickslip_vel_ref_mps / foot_stickslip_group
    # (2026-09-14, speed track): the structurally-different mechanism
    # family named after BOTH prior dynamic candidates closed -- per-side
    # concentrated joint backlash plateaued at ~29-31% of the PS200
    # signature (STATUS.md ~03:5x) and load-coupled command latency was a
    # clean NULL (~04:4x, no roll effect at any dose: this slow creep
    # gait's trapezoidal profile always catches up within the gait's own
    # phase duration regardless of latency, so no static position error
    # is created). This candidate targets a DIFFERENT physical channel --
    # the FOOT-GROUND CONTACT itself, not the actuator chain: real rubber
    # feet exhibit classic Coulomb stick-slip (static friction while
    # planted/near-zero sliding speed EXCEEDS kinetic friction once
    # actively sliding), which MuJoCo's constant-coefficient contact
    # model does not express at all. A concentrated stick-slip
    # differential (e.g. one side's feet "stickier" than the other) is a
    # genuinely different persistent-moment-arm story than either prior
    # mechanism. (0.0, 0.0) = OFF, guarded (no rng consumed), bit-exact
    # -- see ``stickslip_friction_mult``.
    foot_stickslip_gain: tuple[float, float] = (0.0, 0.0)
    # Sliding speed (m/s) at which the extra stick boost has fully
    # decayed to the baseline (kinetic) coefficient -- a modeling
    # constant, not scaled by dr-scale (same convention as
    # joint_backlash_load_ref_nm / latency_load_ref_nm).
    foot_stickslip_vel_ref_mps: float = 0.02
    # "" (default) = every leg's gain drawn independently (bit-exact
    # no-op at gain 0, same guarded-last-draw convention as
    # latency_load_group); else a LEG-only group name (see
    # ``leg_group_mask`` -- no axis groups, friction has no joint axis).
    foot_stickslip_group: str = ""
    # Structured, concentrated PER-LEG MASS asymmetry (2026-09-14, speed
    # track). DESIGN.md's own mechanism inventory ("body/link mass, CoM
    # and inertia ... link length and per-leg asymmetric manufacturing
    # error") has only ever been exercised as SYMMETRIC, per-leg-
    # independent noise (``mass_scale``/``leg_mass_jitter_pct``/
    # ``com_offset_m`` above) -- a real build/assembly defect (battery
    # or wiring routed to one side, uneven print infill between the
    # left/right leg sets) is a genuinely different, PERSISTENT-BIAS
    # story, exactly the "uniform vs. concentrated" split that turned
    # joint backlash from a clean NULL into the best-to-date (~29-31%)
    # PS200 roll-signature match. (0.0, 0.0) = OFF, guarded (no rng
    # consumed, no earlier draw shifted), bit-exact -- draws a SINGLE
    # scalar magnitude (not independent per leg, unlike
    # ``leg_mass_jitter_pct``) applied as ``1 + magnitude`` to every
    # masked leg's mass+inertia, on top of (not instead of) the existing
    # per-leg jitter.
    leg_mass_bias_pct: tuple[float, float] = (0.0, 0.0)
    # "" (default) = every leg biased identically (degenerates to a
    # symmetric global mass bump, bit-exact no-op at magnitude 0); else
    # a LEG-only group name (see ``leg_group_mask`` -- mass has no
    # joint axis, same vocabulary as ``foot_stickslip_group``).
    leg_mass_bias_group: str = ""
    # Structured, concentrated PER-LEG LINK-LENGTH asymmetry (2026-09-17,
    # speed track). DESIGN.md separately names "link length and per-leg
    # asymmetric manufacturing error" alongside (not the same as) "body/
    # link mass, CoM and inertia" -- the mass/inertia half of that pair
    # was built+probed structured (leg_mass_bias_pct/-group, 09-14, clean
    # NULL) but link LENGTH itself has only ever been exercised as
    # SYMMETRIC per-leg-independent jitter (link_len_leg_pct above), never
    # as a concentrated persistent bias. A real assembly defect (one leg's
    # femur reprinted at the wrong scale, a servo horn seated one spline
    # off, a bent link from a fall) is a genuinely different story from
    # random per-leg noise, and unlike mass (a LOAD-domain perturbation
    # this policy's position-controlled actuators absorb without drifting,
    # per the mass-bias closure's own mechanistic finding) a length error
    # is a POSITION/KINEMATIC-domain defect -- the same domain that made
    # joint backlash the best-to-date (~29-31%) PS200 roll-signature
    # match, because the policy's IK still assumes NOMINAL length while
    # the true stance geometry is offset. (0.0, 0.0) = OFF, guarded (no
    # rng consumed, no earlier draw shifted), bit-exact -- draws a SINGLE
    # scalar magnitude (not independent per leg, unlike link_len_leg_pct)
    # applied as ``1 + magnitude`` to every masked leg's coxa+femur+tibia
    # length (and CoM shift, which moves with true link length), on top
    # of (not instead of) the existing global/per-leg jitter.
    link_len_bias_pct: tuple[float, float] = (0.0, 0.0)
    # "" (default) = every leg biased identically (degenerates to a
    # symmetric global length bump, bit-exact no-op at magnitude 0); else
    # a LEG-only group name (see ``leg_group_mask`` -- length has no
    # joint axis, same vocabulary as ``leg_mass_bias_group``).
    link_len_bias_group: str = ""
    # Structured, concentrated PER-LEG FOOT-CONTACT compliance
    # (2026-09-20, speed track). DESIGN.md's mechanism inventory names
    # "ground and per-foot friction/compliance" but every prior probe in
    # this saga only exercised FRICTION (foot_friction_scale) or a
    # GLOBAL, uniform solref timeconst applied to every geom alike
    # (contact_stiff_scale, ground and feet together). A soft rubber
    # pad, worn foot, or squashed-print foot geometry is a per-FOOT,
    # persistent story distinct from both -- the digital-twin replay
    # (HEXAPOD2_DIGITAL_TWIN_2026-09-12.md) separately tested and
    # REJECTED a chassis/leg-ROOT flex mechanism (closed: it moves
    # PS200 the wrong direction and invents roll in negative controls);
    # foot-level contact softening was never dosed by that study or this
    # saga. (0.0, 0.0) = OFF, guarded (no rng consumed, no earlier draw
    # shifted), bit-exact -- draws a SINGLE scalar magnitude (not
    # independent per leg) applied as a multiplicative INCREASE to the
    # foot geom's solref timeconst (softer contact, more give under
    # load), on top of (not instead of) the existing global
    # contact_stiff_scale.
    foot_contact_soft_pct: tuple[float, float] = (0.0, 0.0)
    # "" (default) = every foot softened identically; else a LEG-only
    # group name (see ``leg_group_mask`` -- contact softness has no
    # joint axis, same vocabulary as ``foot_stickslip_group``).
    foot_contact_soft_group: str = ""
    # Structured, concentrated PER-LEG FOOT TORSIONAL/ROLLING friction
    # reduction (2026-09-20, speed track). ``foot_friction_scale`` above
    # only ever touches ``geom_friction[:, 0]`` (SLIDING). MuJoCo's foot
    # pad geom is condim=6 (full torsional + rolling friction), never
    # randomized before now. A worn/rounded pad or a bearing that lets a
    # planted foot twist more freely under yaw reaction is a physically
    # distinct defect from sliding grip: it lets the SUPPORT TRIPOD pivot
    # under a swinging leg's reaction torque rather than holding still,
    # a candidate route from ordinary gait yaw reaction into extra BODY
    # roll that no prior probe in this saga (friction, contact-stiffness,
    # backlash, link-length, mass/CoM) has dosed. (0.0, 0.0) = OFF,
    # guarded (no rng consumed, no earlier draw shifted), bit-exact --
    # draws a SINGLE scalar magnitude applied as a multiplicative
    # DECREASE (``1 - magnitude``, floored at 0) to the foot geom's
    # torsional (index 1) and rolling (index 2) friction coefficients,
    # on top of (not instead of) the existing sliding-friction dose.
    foot_torsion_soft_pct: tuple[float, float] = (0.0, 0.0)
    # "" (default) = every foot softened identically; else a LEG-only
    # group name (see ``leg_group_mask``).
    foot_torsion_soft_group: str = ""
    # Transient PER-LEG foot-catch/stumble EVENT (2026-09-20, speed
    # track, STATUS.md 09-20 ~10:3x "Next" item 2). Every mechanism
    # dosed so far this saga (backlash, link-length, mass/CoM, contact
    # softness, torsional friction) is a CONTINUOUS per-episode model
    # parameter -- exactly what the digital-twin's own causal read of
    # the PS200 trace (HEXAPOD2_DIGITAL_TWIN_2026-09-12.md: "load-
    # dependent post-encoder deformation ... unloads one support foot,
    # followed by body pivot and SWING-FOOT CONTACT") says the real
    # event is NOT: it is a one-shot TRANSIENT per stride, not a
    # standing softness/gap. This axis models the LAST link of that
    # chain directly -- an unintended catch/snag on the swinging foot
    # -- rather than trying to cause it indirectly through a
    # compliance parameter (which the whole 09-14..09-20 probe series
    # showed the position-controlled actuator stack simply absorbs).
    # (0.0, 0.0) = OFF, guarded (no rng consumed, no earlier draw
    # shifted), bit-exact -- draws a SINGLE scalar magnitude (peak
    # yank force, Newtons) applied to every masked leg. sim_env fires
    # the event ONCE PER REAL LIFTOFF (foot touch sensor transitions
    # planted -> airborne, see sim_env._update_foot_catch_state), never
    # on a blind clock -- coupled to the policy's OWN gait phase, not a
    # guessed period, which is the "coupled to gait phase" requirement
    # named in STATUS.md. Applied as a brief (~0.12s) retrograde +
    # downward force on the caught foot's pad body via xfrc_applied
    # (sim_env._advance), then released.
    foot_catch_force_n: tuple[float, float] = (0.0, 0.0)
    # "" (default) = every leg catches identically; else a LEG-only
    # group name (see ``leg_group_mask`` -- a catch event has no joint
    # axis).
    foot_catch_force_group: str = ""
    # Adaptive/adversarial hard-case sampler (2026-09-14, speed track —
    # the DR-composition panel's next-named lever after CTRL/WIDE/
    # STRUCT/COMBO all missed the held-out >=30% roll-reduction floor,
    # STATUS.md 09-13 ~21:5x). False (default) = OFF: the struct overlay
    # draws its mode/group uniformly exactly as before (bit-exact, no
    # extra rng draws, no regret bookkeeping touched). True: the overlay
    # draws from DomainRandomizer.struct_story_weights() instead of a
    # flat 50/50 + uniform-group draw, biasing training toward whichever
    # STRUCT_STORIES region the running policy currently survives worst
    # (DomainRandomizer.record_struct_outcome, fed by each episode's own
    # peak roll — see walk_task._post_step). A bool, not a probability:
    # it changes HOW the overlay's own mode/group is chosen, not whether
    # it fires (struct_dr_prob still owns that). Not scaled by .scaled()
    # (a boolean mechanism switch, like zero_drift_cmd_frame below).
    struct_dr_adaptive: bool = False

    def scaled(self, s: float) -> "RandRanges":
        """Curriculum knob: shrink every range toward nominal by ``s``.

        s=1 is full randomization, s=0 is the calibrated nominal sim.
        Sensor NOISE floors (encoder, tilt, gyro noise) are kept at full
        strength even at s=0 — real sensors are always noisy; it's the
        structural/bias randomization that makes early learning hard.
        """
        s = max(0.0, min(1.0, float(s)))

        def pair(lo: float, hi: float) -> tuple[float, float]:
            return (1.0 + (lo - 1.0) * s, 1.0 + (hi - 1.0) * s)

        return RandRanges(
            mass_scale=pair(*self.mass_scale),
            com_offset_m=self.com_offset_m * s,
            leg_mass_jitter_pct=self.leg_mass_jitter_pct * s,
            link_len_scale_pct=self.link_len_scale_pct * s,
            link_len_leg_pct=self.link_len_leg_pct * s,
            friction_scale=pair(*self.friction_scale),
            contact_stiff_scale=pair(*self.contact_stiff_scale),
            ground_tilt_deg=self.ground_tilt_deg * s,
            kp_scale_pct=self.kp_scale_pct * s,
            kv_scale_pct=self.kv_scale_pct * s,
            torque_scale=pair(*self.torque_scale),
            latency_scale=pair(*self.latency_scale),
            deadband_scale=pair(*self.deadband_scale),
            vel_scale=pair(*self.vel_scale),
            cmd_drop_prob_max=self.cmd_drop_prob_max * s,
            placement_noise_deg=self.placement_noise_deg * s,
            bad_start_prob=self.bad_start_prob * s,
            bad_start_max_joints=self.bad_start_max_joints,
            bad_start_deg=(self.bad_start_deg[0] * s,
                           self.bad_start_deg[1] * s),
            joint_zero_bias_deg=self.joint_zero_bias_deg * s,
            zero_drift_cmd_frame=self.zero_drift_cmd_frame,
            encoder_noise_deg=self.encoder_noise_deg,
            imu_mount_deg=self.imu_mount_deg * s,
            imu_pos_xy_m=self.imu_pos_xy_m * s,
            imu_pos_z_m=(self.imu_pos_z_m[0] * s, self.imu_pos_z_m[1] * s),
            imu_bias_deg=self.imu_bias_deg * s,
            tilt_noise_deg=self.tilt_noise_deg,
            gyro_bias_deg_s=self.gyro_bias_deg_s * s,
            gyro_noise_deg_s=self.gyro_noise_deg_s,
            action_noise=self.action_noise * s,
            # Probability follows the curriculum; the DOSE does not
            # (like the sensor noise floors): a champion at dr 0.35
            # must still see real 6-18° leans, not homeopathic 2-6°
            # ones — a shrunken dose never visits the states the
            # hardware actually fails in.
            tipped_start_prob=self.tipped_start_prob * s,
            tipped_start_deg=self.tipped_start_deg,
            # Same convention as tipped: probability follows the
            # curriculum, the dose does not.
            rise_rock_prob=self.rise_rock_prob * s,
            rise_rock_deg=self.rise_rock_deg,
            walk_kick_prob=self.walk_kick_prob * s,
            walk_kick_deg=self.walk_kick_deg,
            walk_kick_s=self.walk_kick_s,
            walk_push_prob=self.walk_push_prob * s,
            walk_push_nm=self.walk_push_nm,
            walk_push_s=self.walk_push_s,
            walk_push_repeat_period_s=self.walk_push_repeat_period_s,
            walk_push_start_s=self.walk_push_start_s,
            # Same convention as tipped/rock/push: probability follows
            # the curriculum, the dose (strength menu / mix) does not —
            # a half-strength fault is a different, easier fault.
            fault_prob=self.fault_prob * s,
            fault_weak_scales=self.fault_weak_scales,
            fault_mix=self.fault_mix,
            # Same convention as walk_push/fault: probability follows
            # the curriculum, the dose (force/duration/timing menu)
            # does not -- a homeopathic shove never visits the states
            # the hardware push-recovery gate actually needs.
            ext_push_prob=self.ext_push_prob * s,
            ext_push_n=self.ext_push_n,
            ext_push_dur_s=self.ext_push_dur_s,
            ext_push_start_s=self.ext_push_start_s,
            ext_push_repeat_max=self.ext_push_repeat_max,
            ext_push_gap_s=self.ext_push_gap_s,
            ext_push_horizon_s=self.ext_push_horizon_s,
            # New-family ranges shrink toward nominal like every other
            # multiplicative range; the struct overlay follows the
            # probability-ramps/dose-does-not convention.
            foot_friction_scale=pair(*self.foot_friction_scale),
            leg_torque_scale=pair(*self.leg_torque_scale),
            struct_dr_prob=self.struct_dr_prob * s,
            struct_dr_adaptive=self.struct_dr_adaptive,
            # Magnitude ranges follow the curriculum like every other
            # per-joint scale (kp/kv/torque); the load-coupling reference
            # is a modeling constant, not scaled (like zero_drift_cmd_frame).
            joint_backlash_deg=(self.joint_backlash_deg[0] * s,
                                 self.joint_backlash_deg[1] * s),
            joint_backlash_load_gain=(self.joint_backlash_load_gain[0] * s,
                                       self.joint_backlash_load_gain[1] * s),
            joint_backlash_load_ref_nm=self.joint_backlash_load_ref_nm,
            # Categorical group selector, not a magnitude — same
            # convention as struct_dr_adaptive/zero_drift_cmd_frame:
            # WHICH joints get dosed does not shrink with the
            # curriculum, only the probability/dose menus do.
            joint_backlash_group=self.joint_backlash_group,
            # Same convention as joint_backlash_deg/-load_gain/-group
            # immediately above: magnitude ranges follow the curriculum,
            # the load-reference constant and categorical group name do
            # not.
            latency_load_gain=(self.latency_load_gain[0] * s,
                                self.latency_load_gain[1] * s),
            latency_load_ref_nm=self.latency_load_ref_nm,
            latency_load_group=self.latency_load_group,
            # Same convention: magnitude range follows the curriculum,
            # the velocity-reference constant and categorical group name
            # do not.
            foot_stickslip_gain=(self.foot_stickslip_gain[0] * s,
                                  self.foot_stickslip_gain[1] * s),
            foot_stickslip_vel_ref_mps=self.foot_stickslip_vel_ref_mps,
            foot_stickslip_group=self.foot_stickslip_group,
            # Same convention: magnitude range follows the curriculum,
            # the categorical group name does not.
            leg_mass_bias_pct=(self.leg_mass_bias_pct[0] * s,
                                self.leg_mass_bias_pct[1] * s),
            leg_mass_bias_group=self.leg_mass_bias_group,
            link_len_bias_pct=(self.link_len_bias_pct[0] * s,
                                self.link_len_bias_pct[1] * s),
            link_len_bias_group=self.link_len_bias_group,
            # Same convention: magnitude range follows the curriculum,
            # the categorical group name does not.
            foot_contact_soft_pct=(self.foot_contact_soft_pct[0] * s,
                                    self.foot_contact_soft_pct[1] * s),
            foot_contact_soft_group=self.foot_contact_soft_group,
            # Same convention: magnitude range follows the curriculum,
            # the categorical group name does not.
            foot_torsion_soft_pct=(self.foot_torsion_soft_pct[0] * s,
                                    self.foot_torsion_soft_pct[1] * s),
            foot_torsion_soft_group=self.foot_torsion_soft_group,
            # Same convention: magnitude range follows the curriculum,
            # the categorical group name does not.
            foot_catch_force_n=(self.foot_catch_force_n[0] * s,
                                 self.foot_catch_force_n[1] * s),
            foot_catch_force_group=self.foot_catch_force_group,
        )


@dataclass
class EpisodeRandomization:
    """One sampled episode's perturbations."""
    mass_scale: float
    com_offset_m: np.ndarray             # (3,)
    leg_mass_scale: np.ndarray           # (6, 3) coxa/femur/tibia bodies
    link_scale: np.ndarray               # (6, 3) coxa/femur/tibia lengths
    friction_scale: float
    contact_stiff_scale: float
    gravity_vec: np.ndarray              # (3,) tilted, |g| = 9.80665
    kp_scale: np.ndarray                 # (18,)
    kv_scale: np.ndarray                 # (18,)
    torque_scale: float
    latency_scale: float
    deadband_scale: float
    vel_scale: float
    cmd_drop_prob: float
    start_offset_rad: np.ndarray         # (18,) placement noise (+ bad start)
    bad_start_joints: list[int]          # joints that start way off
    joint_zero_bias_rad: np.ndarray      # (18,)
    zero_drift_cmd_frame: bool           # bias shifts cmd frame too
    encoder_noise_rad: float
    imu_mount_rot: np.ndarray            # (3, 3) chassis → IMU frame
    imu_pos_m: np.ndarray                # (3,) IMU offset from chassis origin
    imu_bias_rad: np.ndarray             # (2,) roll, pitch
    tilt_noise_rad: float
    gyro_bias_rad_s: np.ndarray          # (3,)
    gyro_noise_rad_s: float
    action_noise: float
    # Signed target body roll for a tipped start (0 = level episode).
    # + rolls the body toward its right side (legs 3-5), − toward the
    # left. sim_env maps this to an asymmetric leg-fold start offset at
    # plant/park starts and keeps the tilt reference LEVEL.
    tipped_roll_deg: float = 0.0
    # Signed target body roll for the rise-rock command bias (0 = no
    # rocking this episode; rise-mode episodes only, same sign
    # convention as tipped_roll_deg).
    rise_rock_roll_deg: float = 0.0
    # Signed PEAK target roll + pulse duration for the walk takeoff
    # kick (0 = no kick this episode; walk-mode episodes only, same
    # sign convention as tipped_roll_deg).
    walk_kick_roll_deg: float = 0.0
    walk_kick_dur_s: float = 0.0
    # Signed PEAK chassis roll torque (N·m) + pulse duration for the
    # walk takeoff push (0 = no push this episode; walk-mode episodes
    # only; + rolls the body toward its right side, same convention
    # as tipped_roll_deg).
    walk_push_peak_nm: float = 0.0
    walk_push_dur_s: float = 0.0
    # Optional recurrent timing. repeat_period_s <= 0 preserves the original
    # one-shot takeoff pulse. start_s is only sampled when repeat is enabled,
    # so the default adds no RNG draw to historical walk_push episodes.
    walk_push_repeat_period_s: float = 0.0
    walk_push_start_s: float = 0.0
    # Fault injection (dr.fault_*, see RandRanges). fault_mode "" =
    # healthy episode (all fault fields inert, apply_fault_to_model
    # is a no-op). "weak"/"frozen" carry ONE joint index in
    # fault_joints; "leg" carries that leg's 3 joint indices.
    # fault_scale is the strength multiplier for weak/leg (0.0 = dead
    # servo) and is ignored for frozen.
    fault_mode: str = ""
    fault_joints: tuple[int, ...] = ()
    fault_scale: float = 1.0
    # Mid-episode external push (dr.ext_push_*, see RandRanges): peak
    # |force| N + pulse duration + delay from episode start + world-
    # frame direction (0 = no push this episode; walk-mode episodes
    # only, see sim_env._ext_push_force_n).
    ext_push_peak_n: float = 0.0
    ext_push_dur_s: float = 0.0
    ext_push_start_s: float = 0.0
    ext_push_dir_rad: float = 0.0
    # REPEATED pushes (dr.ext_push_repeat_max, see RandRanges): extra
    # pulses beyond the first, each a (peak_n, dur_s, start_s, dir_rad)
    # tuple in the same units/convention as the four fields above.
    # Empty by default -- bit-exact no-op whenever repeat_max<=1 (the
    # default), since sample() only ever appends here when repeat_max>1.
    ext_push_extra: tuple[tuple[float, float, float, float], ...] = ()
    # Per-foot friction / per-leg torque asymmetry (dr.foot_friction_scale,
    # dr.leg_torque_scale, and the struct overlay below). All-ones = the
    # historical model, byte-exact (both apply paths are guarded no-ops).
    foot_friction_scale: np.ndarray = field(
        default_factory=lambda: np.ones(N_LEGS))
    leg_torque_scale: np.ndarray = field(
        default_factory=lambda: np.ones(N_LEGS))
    # "" = no structured overlay this episode; else "correlated" /
    # "asymmetric" (diagnostics only — the fields above already carry
    # the overlay's values).
    # Dynamic, load-coupled joint backlash (dr.joint_backlash_deg /
    # dr.joint_backlash_load_gain, see RandRanges). All-zero gap (the
    # default) = OFF, byte-exact (JointBacklash.apply is the identity
    # map at gap=0 — see its own docstring). Per-joint gap in RADIANS
    # (converted from the sampled degrees at draw time, matching every
    # other *_rad field's convention).
    joint_backlash_gap_rad: np.ndarray = field(
        default_factory=lambda: np.zeros(N_JOINTS))
    joint_backlash_load_gain: float = 0.0
    joint_backlash_load_ref_nm: float = 1.2
    # Dynamic, load-coupled COMMAND LATENCY (dr.latency_load_gain /
    # dr.latency_load_group, see RandRanges). All-zero gain (the
    # default) = OFF, byte-exact (ServoProfile treats an all-zero/None
    # gain array as a pure static latency, identical to every
    # pre-2026-09-14 profile).
    latency_load_gain: np.ndarray = field(
        default_factory=lambda: np.zeros(N_JOINTS))
    latency_load_ref_nm: float = 1.2
    # Per-foot Coulomb stick-slip (dr.foot_stickslip_gain / -group, see
    # RandRanges + domain_rand.stickslip_friction_mult). All-zero gain
    # (the default) = OFF, byte-exact (sim_env's per-tick friction hook
    # is a guarded no-op whenever every leg's gain is 0).
    foot_stickslip_gain: np.ndarray = field(
        default_factory=lambda: np.zeros(N_LEGS))
    foot_stickslip_vel_ref_mps: float = 0.02
    # Structured per-leg mass/inertia bias (dr.leg_mass_bias_pct /
    # -group, see RandRanges). All-ones (the default) = OFF, byte-exact
    # (multiplying by 1.0 in apply_to_model is a pure no-op).
    leg_mass_bias_scale: np.ndarray = field(
        default_factory=lambda: np.ones(N_LEGS))
    # Structured per-leg link-length bias (dr.link_len_bias_pct /
    # -group, see RandRanges). All-ones (the default) = OFF, byte-exact
    # (multiplying by 1.0 in apply_to_model is a pure no-op).
    link_len_bias_scale: np.ndarray = field(
        default_factory=lambda: np.ones(N_LEGS))
    # Structured per-leg foot-contact softening (dr.foot_contact_soft_pct
    # / -group, see RandRanges). All-ones (the default) = OFF, byte-exact
    # (multiplying by 1.0 in apply_to_model is a pure no-op).
    foot_contact_soft_scale: np.ndarray = field(
        default_factory=lambda: np.ones(N_LEGS))
    # Structured per-leg foot torsional/rolling-friction softening
    # (dr.foot_torsion_soft_pct / -group, see RandRanges). All-ones (the
    # default) = OFF, byte-exact (multiplying by 1.0 in apply_to_model
    # is a pure no-op).
    foot_torsion_soft_scale: np.ndarray = field(
        default_factory=lambda: np.ones(N_LEGS))
    # Transient per-leg foot-catch/stumble event peak force, Newtons
    # (dr.foot_catch_force_n / -group, see RandRanges). All-zero (the
    # default) = OFF, byte-exact -- sim_env's liftoff detector and
    # _advance's xfrc application are both guarded no-ops whenever
    # every entry is 0.0.
    foot_catch_force_n: np.ndarray = field(
        default_factory=lambda: np.zeros(N_LEGS))
    struct_dr_mode: str = ""
    # "" = no structured overlay this episode; else one of
    # domain_rand.STRUCT_STORIES — the granular key the adaptive
    # sampler (dr.struct_dr_adaptive) tracks and rewards/regrets
    # against. Set whenever the overlay fires, regardless of whether
    # adaptive selection is on, so walk_task._post_step always has a
    # story to report the episode's outcome against once the run turns
    # adaptivity on (diagnostics-only otherwise, mirrors struct_dr_mode).
    struct_dr_story: str = ""

    def fault_health(self) -> np.ndarray:
        """(18,) health vector per AMP brief §8.2: 1.0 healthy, 0.0
        disabled/frozen, intermediate = degraded strength. Deployable
        as actor obs once M4 wiring lands; also handy for eval
        reports."""
        h = np.ones(N_JOINTS, dtype=np.float32)
        if self.fault_mode:
            v = 0.0 if self.fault_mode == "frozen" else float(self.fault_scale)
            for j in self.fault_joints:
                h[j] = v
        return h

    def apply_fault_to_model(self, model) -> None:
        """Apply the episode's fault as pure MjModel field edits.

        Call AFTER ``servo_model.apply_params_to_model`` (which SETS
        actuator gain/bias/forcerange rows each reset — these edits
        multiply/override them). Touches only fields in
        ``mjx_backend.MODEL_DR_FIELDS`` (actuator_gainprm/biasprm/
        forcerange, dof_damping) so the per-world model-DR path uploads
        faults to the batched stacks unchanged. No-op when healthy.
        """
        if not self.fault_mode:
            return
        from .servo_model import _act_id, joint_names, joint_qvel_addrs

        names = joint_names()
        dadr = joint_qvel_addrs(model)
        for j in self.fault_joints:
            pa = _act_id(model, names[j])
            va = _act_id(model, names[j] + "_d")
            if self.fault_mode == "frozen":
                # Seized gearbox: servo can't move it, backdrive locked.
                model.actuator_forcerange[pa] = (0.0, 0.0)
                model.actuator_forcerange[va] = (0.0, 0.0)
                model.dof_damping[dadr[j]] = FROZEN_DOF_DAMPING
            else:
                s = float(self.fault_scale)
                model.actuator_gainprm[pa, 0] *= s
                model.actuator_biasprm[pa, 1] *= s
                model.actuator_forcerange[pa] *= s
                model.actuator_forcerange[va] *= s
                # scale 0.0 = dead servo: joint free-swings against its
                # existing kv damping + frictionloss (backdrive), which
                # stay untouched.

    def apply_asym_to_model(self, model) -> None:
        """Per-leg torque-saturation asymmetry (dr.leg_torque_scale /
        struct overlay) as pure MjModel field edits.

        Call AFTER ``apply_params_to_model`` (which SETS the actuator
        forcerange rows each reset) and after ``apply_fault_to_model``
        (composes multiplicatively with a weak/leg fault, like the joint
        panel's PanelEnv recipe). Touches only ``actuator_forcerange``
        (in ``mjx_backend.MODEL_DR_FIELDS`` — per-world upload carries
        it to the batched stacks). Guarded no-op at all-ones.
        """
        lts = np.asarray(self.leg_torque_scale, dtype=float)
        if not np.any(lts != 1.0):
            return
        from .servo_model import _act_id, joint_names

        names = joint_names()
        for leg in range(N_LEGS):
            s = float(lts[leg])
            if s == 1.0:
                continue
            for j in leg_joints(leg):
                pa = _act_id(model, names[j])
                va = _act_id(model, names[j] + "_d")
                model.actuator_forcerange[pa] *= s
                model.actuator_forcerange[va] *= s

    def apply_to_model(self, model, *, chassis_bid: int) -> None:
        """Mutate a (freshly restored) MjModel in place."""
        import mujoco

        def bid(name: str) -> int:
            return mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_BODY, name)

        def gid(name: str) -> int:
            return mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_GEOM, name)

        def sid(name: str) -> int:
            return mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_SITE, name)

        # Mass: global scale + chassis CoM shift + per-link jitter.
        model.body_mass[:] *= self.mass_scale
        model.body_inertia[:] *= self.mass_scale
        model.body_ipos[chassis_bid] += self.com_offset_m

        # Leg geometry + per-link mass. Link lengths in the MJCF are just
        # attachment offsets: coxa length = L{i}_femur body x, femur length
        # = L{i}_tibia body x, tibia length = pad-hinge body x.
        for i in range(N_LEGS):
            b_yaw = bid(f"L{i}_yaw")
            b_fem = bid(f"L{i}_femur")
            b_tib = bid(f"L{i}_tibia")
            b_pad = bid(f"L{i}_pad")
            # True post-encoder series flex reparents the original output
            # body below an encoder carrier. Its attachment offset therefore
            # lives on the carrier; named output bodies still own link mass,
            # inertia and CoM. Fall back to the rigid topology per joint so
            # selectors (for example only L4 pitch+knee) compose correctly.
            b_fem_attach = bid(f"L{i}_pitch_encoder_carrier")
            if b_fem_attach < 0:
                b_fem_attach = b_fem
            b_tib_attach = bid(f"L{i}_knee_encoder_carrier")
            if b_tib_attach < 0:
                b_tib_attach = b_tib
            s_coxa, s_femur, s_tibia = self.link_scale[i]
            # Structured per-leg bias (dr.link_len_bias_pct/-group): a
            # SECOND, persistent multiplier on top of the above global/
            # per-leg jitter -- 1.0 (default) is a bit-exact no-op.
            # Folded into s_coxa/s_femur/s_tibia so it scales BOTH the
            # attachment offset (below) and the CoM shift (below,
            # ipos *= s_coxa/s_femur/s_tibia) consistently, like a leg
            # that is genuinely longer/shorter, not just re-weighted.
            bias = self.link_len_bias_scale[i]
            s_coxa *= bias
            s_femur *= bias
            s_tibia *= bias

            model.body_pos[b_fem_attach, 0] *= s_coxa
            model.body_pos[b_tib_attach, 0] *= s_femur
            model.body_pos[b_pad, 0] *= s_tibia
            # CoM of each link moves with its length.
            model.body_ipos[b_yaw, 0] *= s_coxa
            model.body_ipos[b_fem, 0] *= s_femur
            model.body_ipos[b_tib, 0] *= s_tibia

            for k, b in enumerate((b_yaw, b_fem, b_tib)):
                model.body_mass[b] *= self.leg_mass_scale[i, k]
                model.body_inertia[b] *= self.leg_mass_scale[i, k]
                # Structured per-leg bias (dr.leg_mass_bias_pct/-group):
                # a SECOND, persistent multiplier on top of the above
                # per-part jitter -- 1.0 (default) is a bit-exact no-op.
                model.body_mass[b] *= self.leg_mass_bias_scale[i]
                model.body_inertia[b] *= self.leg_mass_bias_scale[i]

        # Ground: sliding friction, contact compliance, slope (via gravity).
        model.geom_friction[:, 0] *= self.friction_scale
        model.geom_solref[:, 0] *= self.contact_stiff_scale
        model.opt.gravity[:] = self.gravity_vec

        # Per-foot friction asymmetry (dr.foot_friction_scale / struct
        # overlay). Guarded no-op at all-ones. Same recipe as the joint
        # panel's PanelEnv: MuJoCo combines contact friction by
        # element-wise max, so a foot dosed BELOW the floor coefficient
        # must also cap the floor or the dose silently vanishes.
        ffs = np.asarray(self.foot_friction_scale, dtype=float)
        if np.any(ffs != 1.0):
            foot_gids = []
            for i in range(N_LEGS):
                g = gid(f"L{i}_foot")
                if g < 0:
                    raise ValueError(f"model has no L{i}_foot geom")
                foot_gids.append(g)
            ground_gids = [g for g in (gid("floor"), gid("terrain"))
                           if g >= 0]
            if not ground_gids:
                raise ValueError("model has no floor or terrain geom")
            dosed = model.geom_friction[foot_gids, 0] * ffs
            model.geom_friction[foot_gids, 0] = dosed
            cap = float(np.min(dosed))
            for g in ground_gids:
                model.geom_friction[g, 0] = min(
                    float(model.geom_friction[g, 0]), cap)

        # Per-foot contact softening (dr.foot_contact_soft_pct / struct
        # overlay). Guarded no-op at all-ones. Multiplies ONLY the named
        # foot geoms' solref timeconst (softer contact, more give under
        # load) on top of the global contact_stiff_scale above, which
        # touches every geom (feet AND ground) uniformly -- this is a
        # persistent, per-foot-concentrated defect (worn/soft pad,
        # squashed print), not a symmetric ground/foot-alike change.
        fcs = np.asarray(self.foot_contact_soft_scale, dtype=float)
        if np.any(fcs != 1.0):
            for i in range(N_LEGS):
                g = gid(f"L{i}_foot")
                if g < 0:
                    raise ValueError(f"model has no L{i}_foot geom")
                model.geom_solref[g, 0] *= float(fcs[i])

        # Per-foot torsional/rolling-friction softening (dr.
        # foot_torsion_soft_pct / struct overlay). Guarded no-op at
        # all-ones. Touches ONLY the named foot geoms' torsional (index
        # 1) and rolling (index 2) friction -- distinct from the
        # existing sliding-friction dose (index 0, foot_friction_scale)
        # above.
        fts = np.asarray(self.foot_torsion_soft_scale, dtype=float)
        if np.any(fts != 1.0):
            for i in range(N_LEGS):
                g = gid(f"L{i}_foot")
                if g < 0:
                    raise ValueError(f"model has no L{i}_foot geom")
                model.geom_friction[g, 1] *= float(fts[i])
                model.geom_friction[g, 2] *= float(fts[i])

    def summary(self) -> dict:
        tilt = math.degrees(math.acos(
            min(1.0, -float(self.gravity_vec[2]) / G0)))
        return {
            "mass_scale": round(self.mass_scale, 3),
            "com_offset_mm": [round(v * 1000, 1) for v in self.com_offset_m],
            "link_scale_range": [round(float(np.min(self.link_scale)), 3),
                                 round(float(np.max(self.link_scale)), 3)],
            "friction_scale": round(self.friction_scale, 3),
            "ground_tilt_deg": round(tilt, 2),
            "kp_scale_mean": round(float(np.mean(self.kp_scale)), 3),
            "torque_scale": round(self.torque_scale, 3),
            "latency_scale": round(self.latency_scale, 3),
            "deadband_scale": round(self.deadband_scale, 3),
            "cmd_drop_prob": round(self.cmd_drop_prob, 3),
            "imu_pos_mm": [round(v * 1000, 1) for v in self.imu_pos_m],
            "zero_bias_max_deg": round(
                float(np.max(np.abs(self.joint_zero_bias_rad))) / DEG2RAD, 2),
            "zero_drift_cmd_frame": bool(self.zero_drift_cmd_frame),
            "bad_start_joints": [int(j) for j in self.bad_start_joints],
            "start_offset_max_deg": round(
                float(np.max(np.abs(self.start_offset_rad))) / DEG2RAD, 1),
            "tipped_roll_deg": round(self.tipped_roll_deg, 1),
            "rise_rock_roll_deg": round(self.rise_rock_roll_deg, 1),
            "walk_kick_roll_deg": round(self.walk_kick_roll_deg, 1),
            "walk_kick_dur_s": round(self.walk_kick_dur_s, 2),
            "walk_push_peak_nm": round(self.walk_push_peak_nm, 2),
            "walk_push_dur_s": round(self.walk_push_dur_s, 2),
            "walk_push_repeat_period_s": round(
                self.walk_push_repeat_period_s, 3),
            "walk_push_start_s": round(self.walk_push_start_s, 3),
            "fault": ("none" if not self.fault_mode else
                      f"{self.fault_mode}:j{list(self.fault_joints)}"
                      f"@{round(self.fault_scale, 2)}"),
            "struct_dr": self.struct_dr_mode or "none",
            "struct_dr_story": self.struct_dr_story or "none",
            "foot_friction_min": round(
                float(np.min(self.foot_friction_scale)), 3),
            "leg_torque_min": round(
                float(np.min(self.leg_torque_scale)), 3),
            "joint_backlash_max_deg": round(
                float(np.max(self.joint_backlash_gap_rad)) / DEG2RAD, 2),
            "joint_backlash_load_gain": round(
                self.joint_backlash_load_gain, 2),
            "latency_load_gain_max": round(
                float(np.max(self.latency_load_gain)), 3),
            "foot_stickslip_gain_max": round(
                float(np.max(self.foot_stickslip_gain)), 3),
            "foot_contact_soft_max": round(
                float(np.max(self.foot_contact_soft_scale)), 3),
            "foot_torsion_soft_min": round(
                float(np.min(self.foot_torsion_soft_scale)), 3),
        }


class JointBacklash:
    """Per-joint classical mechanical backlash (play), optionally widened
    by recent joint load — the DYNAMIC, load-coupled uncertainty family
    DR_JOINT_PANEL_2026-09-13 named as its escalation after every bounded
    STATIC parameter family (independent/correlated/asymmetric, incl. the
    structured hard-region overlay) closed 0/5 against the PS200 16.78-deg
    hardware roll signature.

    Physical picture: a servo's OUTPUT (through gearbox/link play) does not
    instantly follow a direction reversal of its commanded setpoint — it
    must first take up a small "dead" gap before it re-engages, and that
    gap is understood to widen under load (worn/loaded gear teeth, cable
    stretch). This is intentionally distinct from ``deadband_scale``
    (RandRanges), an always-on symmetric dead-zone around ANY held
    position, already probed alone (probe_ps200_transfer.py "Deadband
    (backlash/post-encoder compliance) dose") and refuted as a scale
    match: that mechanism never engages/disengages with commanded
    DIRECTION, so it cannot express the "takes up slack on every reversal,
    especially under load" story this class does.

    ``apply`` is the textbook backlash (play) nonlinearity: the engaged
    (effective, foot-side) position only moves once the commanded target
    has crossed more than ``gap/2`` past the point of the last reversal.
    At ``gap=0`` (every joint, the historical default) ``apply`` is the
    exact identity map — ``move`` is true whenever ``target != engaged``
    and the update sets ``engaged = target`` unconditionally, so a
    disabled axis is bit-exact with pre-2026-09-14 behavior with zero
    extra branching cost avoided only by the caller never constructing
    this class when the episode's gap is all-zero (see sim_env.py).
    """

    def __init__(self, gap_rad: np.ndarray, *, load_gain: float = 0.0,
                 load_ref_nm: float = 1.2):
        self.gap_rad = np.asarray(gap_rad, dtype=float).reshape(N_JOINTS)
        self.load_gain = float(load_gain)
        self.load_ref_nm = max(float(load_ref_nm), 1e-9)
        self._engaged: np.ndarray | None = None

    def reset(self, q0_rad: np.ndarray) -> None:
        self._engaged = np.asarray(q0_rad, dtype=float).reshape(
            N_JOINTS).copy()

    def apply(self, target_rad: np.ndarray,
              load_nm: np.ndarray | None = None) -> np.ndarray:
        """Return this tick's backlash-lagged effective target.

        ``load_nm`` (optional, one tick lagged — the caller's most recent
        available actuator-force reading, never a look-ahead) is the
        per-joint load magnitude driving the load-coupled gap widening;
        ``None`` or ``load_gain=0`` keeps a pure static-gap backlash.
        """
        if self._engaged is None:
            self.reset(target_rad)
        gap = self.gap_rad
        if self.load_gain > 0.0 and load_nm is not None:
            load_frac = np.clip(
                np.abs(load_nm) / self.load_ref_nm, 0.0,
                JOINT_BACKLASH_LOAD_CAP)
            gap = gap * (1.0 + self.load_gain * load_frac)
        half = gap * 0.5
        target = np.asarray(target_rad, dtype=float).reshape(N_JOINTS)
        delta = target - self._engaged
        move = np.abs(delta) > half
        self._engaged = np.where(
            move, target - np.sign(delta) * half, self._engaged)
        return self._engaged


def _struct_gravity(rng: np.random.Generator) -> np.ndarray:
    """Tilted gravity for a struct episode (panel tilt bound)."""
    u = rng.uniform
    tilt = float(u(0.0, STRUCT_TILT_DEG)) * DEG2RAD
    az = float(u(0.0, 2.0 * math.pi))
    grade = np.array([math.tan(tilt) * math.cos(az),
                      math.tan(tilt) * math.sin(az), -1.0])
    return G0 * grade / np.linalg.norm(grade)


def _sample_struct_overlay(rng: np.random.Generator,
                           ep: EpisodeRandomization,
                           story: str | None = None) -> EpisodeRandomization:
    """Overlay one structured hard-region ensemble on a base episode.

    Port of the frozen joint panel's correlated/asymmetric samplers
    (`probe_dr_joint_panel._sample_{correlated,asymmetric}`, kept frozen
    there as a pre-registered artifact) with the panel's measured
    hard-region emphasis always on: per-joint kp/kv spread, FRAME-COUPLED
    zero bias (zero_drift_cmd_frame=True), chassis CoM offset, cmd drop,
    contact stiffness and ground tilt, plus per-foot friction / per-leg
    torque asymmetry. Doses come from the module STRUCT_* constants
    (PanelBounds provenance). Draws happen only when the overlay fires,
    after every base-sample draw — the OFF path never reaches here.

    ``story`` (one of ``STRUCT_STORIES``) forces the mode/group instead
    of drawing it — the adaptive sampler's hook (dr.struct_dr_adaptive).
    None (default, every pre-2026-09-14 caller) reproduces the original
    draw exactly: same rng calls in the same order, bit-exact.
    """
    u = rng.uniform
    if story is None:
        mode = "correlated" if rng.random() < 0.5 else "asymmetric"
    else:
        mode = "correlated" if story == "correlated" else "asymmetric"

    # Hard-region core (both modes): the panel's strongest roll drivers.
    kp = u(1.0 - STRUCT_KP_PCT, 1.0 + STRUCT_KP_PCT, N_JOINTS)
    kv = u(1.0 - STRUCT_KV_PCT, 1.0 + STRUCT_KV_PCT, N_JOINTS)
    zb = u(-STRUCT_ZERO_BIAS_DEG, STRUCT_ZERO_BIAS_DEG, N_JOINTS) * DEG2RAD
    com = np.array([u(-STRUCT_COM_XY_M, STRUCT_COM_XY_M),
                    u(-STRUCT_COM_XY_M, STRUCT_COM_XY_M), 0.0])
    cmd_drop = float(u(*STRUCT_CMD_DROP))
    stiff = float(u(*STRUCT_CONTACT_STIFF))
    gravity = _struct_gravity(rng)
    foot = np.ones(N_LEGS)
    leg_t = np.ones(N_LEGS)
    over: dict = {}

    if mode == "correlated":
        # Latent physical stories couple many knobs at once (panel doc).
        g = float(u(0.0, 1.0))            # battery sag under gait load
        over["torque_scale"] = float(
            STRUCT_TORQUE[1] - g * (STRUCT_TORQUE[1] - STRUCT_TORQUE[0]))
        over["vel_scale"] = float(
            STRUCT_VEL[1] - g * (STRUCT_VEL[1] - STRUCT_VEL[0]))
        over["latency_scale"] = float(
            1.0 + g * (STRUCT_LATENCY[1] - 1.0) * u(0.3, 1.0))
        w = int(rng.integers(0, N_LEGS))  # one worn leg
        wg = float(u(0.0, 1.0))
        for j in leg_joints(w):
            kp[j] *= 1.0 - wg * STRUCT_KP_PCT
            zb[j] = float(u(-1.0, 1.0)) * wg * STRUCT_ZERO_BIAS_DEG * DEG2RAD
        leg_t[w] = 1.0 - wg * (1.0 - STRUCT_LEG_TORQUE[0])
        foot[w] = 1.0 - wg * (1.0 - STRUCT_FOOT_FRICTION[0])
        over["deadband_scale"] = float(
            1.0 + wg * (STRUCT_DEADBAND[1] - 1.0) * u(0.0, 1.0))
        m = float(u(-1.0, 1.0))           # as-built mass error + CoM shift
        mid = 0.5 * (STRUCT_MASS[0] + STRUCT_MASS[1])
        half = 0.5 * (STRUCT_MASS[1] - STRUCT_MASS[0])
        over["mass_scale"] = float(mid + m * half)
        com = com * abs(m)
        f = float(u(0.0, 1.0))            # slick floor: dull + soft
        over["friction_scale"] = float(
            1.0 - f * (1.0 - STRUCT_FRICTION[0]))
        stiff = float(1.0 - f * (1.0 - STRUCT_CONTACT_STIFF[0]))
        story_out = "correlated"
    else:
        # Systematic per-side / per-leg-group manufacturing+wear asymmetry.
        if story is None:
            _group_opts = [_STRUCT_LEFT, _STRUCT_RIGHT, _STRUCT_FRONT,
                          _STRUCT_REAR, (int(rng.integers(0, N_LEGS)),)]
            _idx = int(rng.integers(0, 5))
            group = _group_opts[_idx]
            story_out = ("asym_left", "asym_right", "asym_front",
                        "asym_rear", "asym_single")[_idx]
        elif story == "asym_single":
            group = (int(rng.integers(0, N_LEGS)),)
            story_out = story
        else:
            group = {"asym_left": _STRUCT_LEFT, "asym_right": _STRUCT_RIGHT,
                     "asym_front": _STRUCT_FRONT,
                     "asym_rear": _STRUCT_REAR}[story]
            story_out = story
        g = float(u(0.4, 1.0))
        lms = np.asarray(ep.leg_mass_scale, dtype=float).copy()
        for leg in group:
            for j in leg_joints(leg):
                kp[j] = 1.0 - g * STRUCT_KP_PCT * u(0.5, 1.0)
                kv[j] = 1.0 + g * STRUCT_KV_PCT * u(-1.0, 1.0)
                zb[j] = g * STRUCT_ZERO_BIAS_DEG * u(-1.0, 1.0) * DEG2RAD
            leg_t[leg] = 1.0 - g * (1.0 - STRUCT_LEG_TORQUE[0]) * u(0.5, 1.0)
            foot[leg] = (1.0
                         - g * (1.0 - STRUCT_FOOT_FRICTION[0]) * u(0.5, 1.0))
            lms[leg] = 1.0 + g * STRUCT_LEG_MASS_PCT * u(-1.0, 1.0, 3)
        over["leg_mass_scale"] = lms
        # Mild global context so the asymmetry acts on a non-nominal robot.
        over["mass_scale"] = float(u(0.95, 1.15))
        over["friction_scale"] = float(u(0.7, 1.2))
        over["torque_scale"] = float(u(0.8, 1.05))
        over["latency_scale"] = float(u(0.9, 1.6))
        over["deadband_scale"] = float(u(0.8, 2.0))

    return replace(
        ep,
        kp_scale=kp, kv_scale=kv,
        joint_zero_bias_rad=zb, zero_drift_cmd_frame=True,
        com_offset_m=com, cmd_drop_prob=cmd_drop,
        contact_stiff_scale=stiff, gravity_vec=gravity,
        foot_friction_scale=foot, leg_torque_scale=leg_t,
        struct_dr_mode=mode, struct_dr_story=story_out, **over)


class DomainRandomizer:
    def __init__(self, ranges: RandRanges | None = None, *,
                 scale: float = 1.0):
        self.scale = float(scale)
        self.ranges = (ranges or RandRanges()).scaled(self.scale)
        # A measured, persistent floor grade is systematic rather than DR.
        # ``ground_tilt_deg`` above is residual uncertainty around this
        # baseline.  Azimuth names the downhill direction in world XY:
        # 0 degrees = +X, 90 degrees = +Y.
        self.ground_tilt_base_deg = 0.0
        self.ground_azimuth_base_deg = 0.0
        # Adaptive/adversarial struct-DR regret (dr.struct_dr_adaptive,
        # 2026-09-14). One EMA "badness" score per STRUCT_STORIES key,
        # updated only via record_struct_outcome (walk_task._post_step,
        # guarded by the same cfg flag) — a randomizer built with the
        # flag off never touches this dict, so it costs nothing when
        # inert. Seeded at 1.0 (neutral prior: every story equally
        # unproven-hard) rather than 0.0 so struct_story_weights() never
        # divides by an all-zero vector before the first outcome lands.
        self._struct_regret = {k: 1.0 for k in STRUCT_STORIES}

    def record_struct_outcome(self, story: str, badness: float,
                              decay: float = 0.9) -> None:
        """EMA-update one story's regret from an episode's own outcome.

        ``badness`` is any nonnegative scalar where BIGGER = the policy
        did WORSE under that story this episode (walk_task feeds peak
        roll magnitude in degrees) — struct_story_weights() then biases
        future draws toward whichever story currently has the highest
        EMA, i.e. the region the CURRENT policy survives worst, not a
        fixed offline hard region.
        """
        if story not in self._struct_regret:
            return
        d = float(np.clip(decay, 0.0, 0.999))
        prev = self._struct_regret[story]
        self._struct_regret[story] = d * prev + (1.0 - d) * max(
            0.0, float(badness))

    def struct_story_weights(self, explore_floor: float = 0.15) -> dict:
        """Sampling distribution over STRUCT_STORIES from tracked regret.

        A pure regret-proportional draw can starve a story to ~0 mass
        the moment it looks easy, which would stop the very re-checks
        that would notice it got hard again — so ``explore_floor`` mixes
        in a uniform floor (default 15%, same spirit as every other
        guarded-curriculum floor in this file) on top of the
        regret-weighted 85%.
        """
        keys = list(STRUCT_STORIES)
        reg = np.array([max(0.0, self._struct_regret.get(k, 1.0))
                        for k in keys], dtype=float)
        total = float(reg.sum())
        reg_w = (reg / total) if total > 0.0 else (
            np.ones(len(keys)) / len(keys))
        n = len(keys)
        floor = float(np.clip(explore_floor, 0.0, 1.0))
        w = floor / n + (1.0 - floor) * reg_w
        w = w / w.sum()
        return {k: float(v) for k, v in zip(keys, w)}

    def set_ground_slope(self, *, tilt_deg: float,
                         downhill_azimuth_deg: float) -> None:
        """Set the fixed floor grade composed with per-episode slope DR."""
        if not 0.0 <= float(tilt_deg) < 90.0:
            raise ValueError("ground tilt must be in [0, 90) degrees")
        self.ground_tilt_base_deg = float(tilt_deg)
        self.ground_azimuth_base_deg = float(downhill_azimuth_deg) % 360.0

    @classmethod
    def from_params(cls, params: SimServoParams, *,
                    scale: float = 1.0) -> "DomainRandomizer":
        """Widen ranges with the measured joint-to-joint spread, if fitted."""
        r = RandRanges()
        spreads = [params.spread.get(ax, {}) for ax in AXES]
        rise = [s.get("rise_ms_pct") for s in spreads if s.get("rise_ms_pct")]
        delay = [s.get("delay_ms_pct") for s in spreads
                 if s.get("delay_ms_pct")]
        if rise:
            # Rise-time spread across joints ≈ effective kp/kv spread.
            r.kp_scale_pct = max(r.kp_scale_pct, 1.5 * max(rise))
            r.kv_scale_pct = max(r.kv_scale_pct, 1.5 * max(rise))
        if delay:
            hi = 1.0 + 2.0 * max(delay)
            r.latency_scale = (max(0.3, min(r.latency_scale[0], 2.0 - hi)),
                               max(r.latency_scale[1], hi))
        return cls(r, scale=scale)

    def sample(self, rng: np.random.Generator) -> EpisodeRandomization:
        r = self.ranges
        u = rng.uniform

        # Leg lengths: one global scale (systematic print/CAD error) times
        # independent per-leg per-segment spread (assembly tolerance).
        global_len = u(1.0 - r.link_len_scale_pct, 1.0 + r.link_len_scale_pct)
        link_scale = global_len * u(
            1.0 - r.link_len_leg_pct, 1.0 + r.link_len_leg_pct, (N_LEGS, 3))

        # Ground slope: a persistent measured grade plus a smaller random
        # residual.  Compose the two as grade vectors (tan(theta)) so the
        # zero-baseline case remains identical in distribution and opposite
        # slopes can correctly cancel.
        tilt = u(0.0, r.ground_tilt_deg) * DEG2RAD
        az = u(0.0, 2.0 * math.pi)
        base_tilt = self.ground_tilt_base_deg * DEG2RAD
        base_az = self.ground_azimuth_base_deg * DEG2RAD
        grade_xy = np.array([
            math.tan(base_tilt) * math.cos(base_az)
            + math.tan(tilt) * math.cos(az),
            math.tan(base_tilt) * math.sin(base_az)
            + math.tan(tilt) * math.sin(az),
        ])
        gravity_dir = np.array([grade_xy[0], grade_xy[1], -1.0])
        gravity = G0 * gravity_dir / np.linalg.norm(gravity_dir)

        mnt = r.imu_mount_deg * DEG2RAD
        imu_mount_rot = _rot_rpy(u(-mnt, mnt), u(-mnt, mnt), u(-mnt, mnt))

        # Start pose: hand-placement slop on every joint, plus (sometimes)
        # a few joints that are WAY off — slipped zero / operator error,
        # the 2026-08-06 scenario. The env holds this pose at reset like
        # the hardware does; the policy must cope from a degraded stance.
        start_offset = u(-r.placement_noise_deg, r.placement_noise_deg,
                         N_JOINTS) * DEG2RAD
        bad_joints: list[int] = []
        if rng.random() < r.bad_start_prob:
            n_bad = int(rng.integers(1, r.bad_start_max_joints + 1))
            bad_joints = list(rng.choice(N_JOINTS, size=n_bad,
                                         replace=False))
            for j in bad_joints:
                mag = u(*r.bad_start_deg) * DEG2RAD
                start_offset[j] = mag * (1 if rng.random() < 0.5 else -1)

        # Tipped start: draws are GUARDED so configs with the axis off
        # (prob 0, incl. dr_scale=0) keep the legacy rng stream —
        # same convention as the walk park bank.
        tipped_roll = 0.0
        if r.tipped_start_prob > 0.0 and rng.random() < r.tipped_start_prob:
            tipped_roll = float(u(*r.tipped_start_deg))
            if rng.random() < 0.5:
                tipped_roll = -tipped_roll

        # Rise rock: same guarded-draw convention (axis off = legacy
        # rng stream, bit-exact).
        rise_rock = 0.0
        if r.rise_rock_prob > 0.0 and rng.random() < r.rise_rock_prob:
            rise_rock = float(u(*r.rise_rock_deg))
            if rng.random() < 0.5:
                rise_rock = -rise_rock

        # Walk takeoff kick: same guarded-draw convention.
        walk_kick, walk_kick_s = 0.0, 0.0
        if r.walk_kick_prob > 0.0 and rng.random() < r.walk_kick_prob:
            walk_kick = float(u(*r.walk_kick_deg))
            walk_kick_s = float(u(*r.walk_kick_s))
            if rng.random() < 0.5:
                walk_kick = -walk_kick

        # Walk takeoff push: same guarded-draw convention.
        walk_push, walk_push_s = 0.0, 0.0
        walk_push_repeat_period, walk_push_start = 0.0, 0.0
        if r.walk_push_prob > 0.0 and rng.random() < r.walk_push_prob:
            walk_push = float(u(*r.walk_push_nm))
            walk_push_s = float(u(*r.walk_push_s))
            if rng.random() < 0.5:
                walk_push = -walk_push
            # Guarded to preserve the historical RNG stream whenever the
            # recurrent extension is disabled (the default).
            if max(r.walk_push_repeat_period_s) > 0.0:
                walk_push_repeat_period = float(
                    u(*r.walk_push_repeat_period_s))
                walk_push_start = float(u(*r.walk_push_start_s))

        # Fault injection: same guarded-draw convention (fault_prob=0
        # keeps the legacy rng stream bit-exact).
        fault_mode, fault_joints, fault_scale = "", (), 1.0
        if r.fault_prob > 0.0 and rng.random() < r.fault_prob:
            mix = np.asarray(r.fault_mix, dtype=float)
            mix = mix / mix.sum()
            pick = rng.random()
            if pick < mix[0]:
                fault_mode = "weak"
                fault_joints = (int(rng.integers(N_JOINTS)),)
                fault_scale = float(
                    r.fault_weak_scales[
                        int(rng.integers(len(r.fault_weak_scales)))])
            elif pick < mix[0] + mix[1]:
                fault_mode = "frozen"
                fault_joints = (int(rng.integers(N_JOINTS)),)
            else:
                fault_mode = "leg"
                leg = int(rng.integers(N_LEGS))
                fault_joints = leg_joints(leg)
                fault_scale = 0.0

        # Mid-episode external push: same guarded-draw convention
        # (ext_push_prob=0 keeps the legacy rng stream bit-exact).
        ext_push, ext_push_dur, ext_push_start, ext_push_dir = (
            0.0, 0.0, 0.0, 0.0)
        ext_push_extra: tuple[tuple[float, float, float, float], ...] = ()
        if r.ext_push_prob > 0.0 and rng.random() < r.ext_push_prob:
            ext_push = float(u(*r.ext_push_n))
            ext_push_dur = float(u(*r.ext_push_dur_s))
            ext_push_start = float(u(*r.ext_push_start_s))
            ext_push_dir = float(u(0.0, 2.0 * math.pi))
            # Repeated pushes (dr.ext_push_repeat_max): only entered
            # when >1, so the default draws zero extra rng numbers and
            # stays bit-exact. See RandRanges.ext_push_repeat_max.
            if r.ext_push_repeat_max > 1:
                extras = []
                prev_end = ext_push_start + ext_push_dur
                # int(): --cfg-set dr.ext_push_repeat_max=3 arrives as
                # float 3.0 (_parse_cfg_set coerces every scalar to
                # float); range() rejects floats. Direct-constructor
                # callers pass ints and are unaffected.
                for _ in range(int(r.ext_push_repeat_max) - 1):
                    gap = float(u(*r.ext_push_gap_s))
                    start_i = prev_end + gap
                    dur_i = float(u(*r.ext_push_dur_s))
                    if start_i + dur_i > r.ext_push_horizon_s:
                        break
                    peak_i = float(u(*r.ext_push_n))
                    dir_i = float(u(0.0, 2.0 * math.pi))
                    extras.append((peak_i, dur_i, start_i, dir_i))
                    prev_end = start_i + dur_i
                ext_push_extra = tuple(extras)

        ep = EpisodeRandomization(
            mass_scale=u(*r.mass_scale),
            com_offset_m=np.array([
                u(-r.com_offset_m, r.com_offset_m),
                u(-r.com_offset_m, r.com_offset_m),
                0.0]),
            leg_mass_scale=u(1.0 - r.leg_mass_jitter_pct,
                             1.0 + r.leg_mass_jitter_pct, (N_LEGS, 3)),
            link_scale=link_scale,
            friction_scale=u(*r.friction_scale),
            contact_stiff_scale=u(*r.contact_stiff_scale),
            gravity_vec=gravity,
            kp_scale=u(1.0 - r.kp_scale_pct, 1.0 + r.kp_scale_pct, N_JOINTS),
            kv_scale=u(1.0 - r.kv_scale_pct, 1.0 + r.kv_scale_pct, N_JOINTS),
            torque_scale=u(*r.torque_scale),
            latency_scale=u(*r.latency_scale),
            deadband_scale=u(*r.deadband_scale),
            vel_scale=u(*r.vel_scale),
            cmd_drop_prob=u(0.0, r.cmd_drop_prob_max),
            start_offset_rad=start_offset,
            bad_start_joints=bad_joints,
            joint_zero_bias_rad=u(
                -r.joint_zero_bias_deg, r.joint_zero_bias_deg,
                N_JOINTS) * DEG2RAD,
            zero_drift_cmd_frame=bool(r.zero_drift_cmd_frame),
            encoder_noise_rad=r.encoder_noise_deg * DEG2RAD,
            imu_mount_rot=imu_mount_rot,
            imu_pos_m=np.array([
                u(-r.imu_pos_xy_m, r.imu_pos_xy_m),
                u(-r.imu_pos_xy_m, r.imu_pos_xy_m),
                u(*r.imu_pos_z_m)]),
            imu_bias_rad=u(-r.imu_bias_deg, r.imu_bias_deg, 2) * DEG2RAD,
            tilt_noise_rad=r.tilt_noise_deg * DEG2RAD,
            gyro_bias_rad_s=u(
                -r.gyro_bias_deg_s, r.gyro_bias_deg_s, 3) * DEG2RAD,
            gyro_noise_rad_s=r.gyro_noise_deg_s * DEG2RAD,
            action_noise=r.action_noise,
            tipped_roll_deg=tipped_roll,
            rise_rock_roll_deg=rise_rock,
            walk_kick_roll_deg=walk_kick,
            walk_kick_dur_s=walk_kick_s,
            walk_push_peak_nm=walk_push,
            walk_push_dur_s=walk_push_s,
            walk_push_repeat_period_s=walk_push_repeat_period,
            walk_push_start_s=walk_push_start,
            fault_mode=fault_mode,
            fault_joints=fault_joints,
            fault_scale=fault_scale,
            ext_push_peak_n=ext_push,
            ext_push_dur_s=ext_push_dur,
            ext_push_start_s=ext_push_start,
            ext_push_dir_rad=ext_push_dir,
            ext_push_extra=ext_push_extra,
        )
        # Per-foot friction / per-leg torque asymmetry + structured
        # hard-region overlay: ALL drawn after every base field (guarded),
        # so the defaults leave the historical stream untouched AND
        # enabling them never shifts the base draws for a given seed.
        if tuple(r.foot_friction_scale) != (1.0, 1.0):
            ep = replace(ep, foot_friction_scale=u(
                r.foot_friction_scale[0], r.foot_friction_scale[1], N_LEGS))
        if tuple(r.leg_torque_scale) != (1.0, 1.0):
            ep = replace(ep, leg_torque_scale=u(
                r.leg_torque_scale[0], r.leg_torque_scale[1], N_LEGS))
        if r.struct_dr_prob > 0.0 and rng.random() < r.struct_dr_prob:
            story = None
            if r.struct_dr_adaptive:
                # Adaptive hard-case draw (2026-09-14): pick the
                # overlay's story from the running regret distribution
                # instead of letting _sample_struct_overlay's own
                # internal flat 50/50 + uniform-group draw pick it.
                # Only reached when dr.struct_dr_adaptive is on, so the
                # default (off) path never takes this branch and stays
                # bit-exact with the pre-2026-09-14 stream.
                weights = self.struct_story_weights()
                keys = list(weights.keys())
                probs = np.asarray([weights[k] for k in keys], dtype=float)
                story = str(rng.choice(keys, p=probs))
            ep = _sample_struct_overlay(rng, ep, story=story)
        # Dynamic joint backlash: drawn LAST (guarded), same convention
        # as foot_friction_scale/leg_torque_scale/struct above -- the
        # default (0.0, 0.0) range never consumes rng and leaves every
        # earlier draw's stream byte-exact.
        if max(r.joint_backlash_deg) > 0.0:
            gap_deg = u(r.joint_backlash_deg[0], r.joint_backlash_deg[1],
                        N_JOINTS)
            # Group mask (2026-09-14): "" -> all-ones, so this multiply
            # is a bit-exact no-op for every pre-existing config; it
            # consumes no rng and runs AFTER the draw above so the
            # stream is identical whether or not a group is named.
            if r.joint_backlash_group:
                gap_deg = gap_deg * backlash_group_mask(
                    r.joint_backlash_group).astype(float)
            load_gain = (u(*r.joint_backlash_load_gain)
                         if max(r.joint_backlash_load_gain) > 0.0 else 0.0)
            ep = replace(
                ep,
                joint_backlash_gap_rad=gap_deg * DEG2RAD,
                joint_backlash_load_gain=float(load_gain),
                joint_backlash_load_ref_nm=float(r.joint_backlash_load_ref_nm))
        # Load-coupled latency: drawn LAST (guarded), same convention as
        # joint_backlash_deg immediately above -- default (0.0, 0.0)
        # never consumes rng and leaves every earlier draw byte-exact.
        if max(r.latency_load_gain) > 0.0:
            lg_vec = u(r.latency_load_gain[0], r.latency_load_gain[1],
                       N_JOINTS)
            if r.latency_load_group:
                lg_vec = lg_vec * dof_group_mask(
                    r.latency_load_group,
                    param_name="latency_load_group").astype(float)
            ep = replace(
                ep,
                latency_load_gain=lg_vec,
                latency_load_ref_nm=float(r.latency_load_ref_nm))
        # Per-foot stick-slip: drawn LAST (guarded), same convention as
        # latency_load_gain/joint_backlash_deg immediately above --
        # default (0.0, 0.0) never consumes rng and leaves every earlier
        # draw byte-exact.
        if max(r.foot_stickslip_gain) > 0.0:
            ss_gain = u(r.foot_stickslip_gain[0], r.foot_stickslip_gain[1],
                        N_LEGS)
            if r.foot_stickslip_group:
                ss_gain = ss_gain * leg_group_mask(
                    r.foot_stickslip_group,
                    param_name="foot_stickslip_group").astype(float)
            ep = replace(
                ep,
                foot_stickslip_gain=ss_gain,
                foot_stickslip_vel_ref_mps=float(r.foot_stickslip_vel_ref_mps))
        # Structured per-leg mass bias: drawn LAST (guarded), same
        # convention as foot_stickslip_gain immediately above -- default
        # (0.0, 0.0) never consumes rng and leaves every earlier draw
        # byte-exact. A SINGLE scalar magnitude (not independent per
        # leg, unlike leg_mass_jitter_pct) so a masked group gets one
        # consistent, persistent bias rather than more symmetric noise.
        if max(r.leg_mass_bias_pct) > 0.0:
            bias_mag = float(u(*r.leg_mass_bias_pct))
            bias_vec = np.full(N_LEGS, bias_mag)
            if r.leg_mass_bias_group:
                bias_vec = bias_vec * leg_group_mask(
                    r.leg_mass_bias_group,
                    param_name="leg_mass_bias_group").astype(float)
            ep = replace(ep, leg_mass_bias_scale=1.0 + bias_vec)
        # Structured per-leg link-length bias: drawn LAST (guarded), same
        # convention as leg_mass_bias_pct immediately above -- default
        # (0.0, 0.0) never consumes rng and leaves every earlier draw
        # byte-exact. A SINGLE scalar magnitude (not independent per
        # leg, unlike link_len_leg_pct) so a masked group gets one
        # consistent, persistent length bias rather than more symmetric
        # noise.
        if max(r.link_len_bias_pct) > 0.0:
            len_bias_mag = float(u(*r.link_len_bias_pct))
            len_bias_vec = np.full(N_LEGS, len_bias_mag)
            if r.link_len_bias_group:
                len_bias_vec = len_bias_vec * leg_group_mask(
                    r.link_len_bias_group,
                    param_name="link_len_bias_group").astype(float)
            ep = replace(ep, link_len_bias_scale=1.0 + len_bias_vec)
        # Structured per-leg foot-contact softening: drawn LAST
        # (guarded), same convention as link_len_bias_pct immediately
        # above -- default (0.0, 0.0) never consumes rng and leaves
        # every earlier draw byte-exact. A SINGLE scalar magnitude
        # (not independent per leg) so a masked group gets one
        # consistent, persistent softening rather than more symmetric
        # noise.
        if max(r.foot_contact_soft_pct) > 0.0:
            soft_mag = float(u(*r.foot_contact_soft_pct))
            soft_vec = np.full(N_LEGS, soft_mag)
            if r.foot_contact_soft_group:
                soft_vec = soft_vec * leg_group_mask(
                    r.foot_contact_soft_group,
                    param_name="foot_contact_soft_group").astype(float)
            ep = replace(ep, foot_contact_soft_scale=1.0 + soft_vec)
        # Structured per-leg foot torsional/rolling-friction softening:
        # drawn LAST (guarded), same convention as foot_contact_soft_pct
        # immediately above -- default (0.0, 0.0) never consumes rng and
        # leaves every earlier draw byte-exact. A SINGLE scalar
        # magnitude, applied as a multiplicative DECREASE (floored at 0)
        # rather than an increase like every prior "bias"/"soft" field,
        # because torsional grip only ever gets WORSE (worn/rounded),
        # never spontaneously stronger.
        if max(r.foot_torsion_soft_pct) > 0.0:
            tors_mag = float(u(*r.foot_torsion_soft_pct))
            tors_vec = np.full(N_LEGS, tors_mag)
            if r.foot_torsion_soft_group:
                tors_vec = tors_vec * leg_group_mask(
                    r.foot_torsion_soft_group,
                    param_name="foot_torsion_soft_group").astype(float)
            ep = replace(ep, foot_torsion_soft_scale=np.clip(
                1.0 - tors_vec, 0.0, 1.0))
        # Transient per-leg foot-catch/stumble event: drawn LAST
        # (guarded), same convention as foot_torsion_soft_pct
        # immediately above -- default (0.0, 0.0) never consumes rng
        # and leaves every earlier draw byte-exact. A SINGLE scalar
        # magnitude (peak yank force, Newtons), not independent per
        # leg, so a masked group gets one consistent event strength.
        if max(r.foot_catch_force_n) > 0.0:
            catch_mag = float(u(*r.foot_catch_force_n))
            catch_vec = np.full(N_LEGS, catch_mag)
            if r.foot_catch_force_group:
                catch_vec = catch_vec * leg_group_mask(
                    r.foot_catch_force_group,
                    param_name="foot_catch_force_group").astype(float)
            ep = replace(ep, foot_catch_force_n=catch_vec)
        return ep
