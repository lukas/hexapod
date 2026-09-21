"""Canonical `cw-walk50hz-slew-smooth-s0` cfg-set list, versioned in
code -- same rationale/precedent as `cfg_recipe_walk50hz_rlonly_v2.py`
(walkcurr, 2026-09-17): this checkpoint was PROMOTED to the walkcurr
50Hz hardware-transfer reference (walkcurr/STATUS.md 2026-09-21
~03:3x, superseding `bundle_rlonly_v2`'s `crutchoff-s0-warmadapt-acq1`
walk role), so every packaging artifact that hardcodes the OLD
checkpoint's cfg-set (`rot60_fullcircle`, the lifecycle-handoff
composition) needs a matching versioned recipe for the NEW one before
it can be re-pointed -- a hand-retyped ~50-flag cfg-set list is exactly
the mistake that module's own docstring (and this project's 09-18
`rot60_fullcircle` speed-check incident) already warns against.
Verbatim from the recorded launch command (``ops.sh entry
cw-walk50hz-slew-smooth-s0``), --cfg-set values only (training-only
flags -- --steps, --init-from, --seed, --notes, --defer-final-artifacts,
etc. -- dropped; they don't affect an eval env's construction). Same
DR-field exclusion convention as the sibling module: the handful of
dr.* keys that are ALWAYS-ON identity/noise values (not scaled by
--dr-scale) are kept; every dr.* key that IS scaled by --dr-scale
(mass/friction/contact/backlash/etc.) is excluded since eval always
runs at dr-scale 0.0.

This is a MECHANICS-ONLY module (a literal arg list + a thin builder)
-- it does not rank rollouts and carries no reward/behavior opinion.
"""
from __future__ import annotations

# Order matters for --cfg-set (later duplicate keys win). Verbatim
# order from the training command (ops.sh entry cw-walk50hz-slew-
# smooth-s0), minus the excluded dr-scaled fields noted above.
CFG_ARGS: list[str] = [
    "env.model_source=mesh_mjx",
    "control.hz=50",
    "goal.walk_pure=1",
    "goal.walk_speed_min_m_s=0.06",
    "goal.walk_speed_max_m_s=0.06",
    "goal.walk_heading_max_rad=0.0",
    "goal.walk_cmd_resample_s=6.0",
    "goal.walk_cmd_metrics=1",
    "goal.walk_cmd_hold_s=0.0",
    "goal.walk_cmd_ramp_s=0.0",
    "goal.joint_action_bias_hip_deg=40.0",
    "goal.joint_action_bias_knee_deg=35.0",
    "goal.joint_action_box_yaw_deg=15.0",
    "goal.joint_action_box_hip_deg=20.0",
    "goal.joint_action_box_knee_deg=25.0",
    "reward.k_walk_freeprog=2.0",
    "reward.walk_freeprog_cap_m_s=0.06",
    "reward.walk_kernel_vel_ema=1.0",
    "reward.walk_kernel_vel_tau_s=0.1",
    "reward.term_penalty=24",
    "reward.safety_termination_penalty=24",
    "reward.k_track=0.0",
    "reward.k_roll=0.0",
    "reward.k_pitch=0.0",
    "reward.k_height=0.0",
    "reward.k_gyro=0.15",
    "reward.k_action=0.0",
    "reward.k_action_delta=0.03",
    "reward.k_current=0.02",
    "reward.k_walk_heading=0.0",
    "reward.k_step_event=0.0",
    "reward.k_park_duty=0.0",
    "reward.k_walk_idle_charge=0.0",
    "reward.k_loadslip_excess=0.0",
    "bus.write_speed=4096",
    "bus.servo_vel_max_counts_s=write_speed",
    "bus.write_acc=1000",
    "safety.max_delta_q_deg=3.5",
    "safety.max_current_a=100",
    "safety.max_roll_deg=30",
    "safety.max_pitch_deg=30",
    "struct_comp.enabled=0",
    "dr.latency_scale=1,1",
    "dr.deadband_scale=1,1",
    "dr.torque_scale=1.0,1.0",
    "dr.encoder_noise_deg=0.09",
    "dr.tilt_noise_deg=0.3",
    "dr.gyro_noise_deg_s=0.5",
    "ease.gravity_scale=1.0",
    "goal.walk_heading_set=[0.0,0.7853981633974483,-0.7853981633974483,"
    "1.5707963267948966,-1.5707963267948966,2.356194490192345,"
    "-2.356194490192345,3.141592653589793]",
    "goal.walk_stop_frac=0.0",
    "reward.walk_leg_duty_ratio_charge=10.0",
    "reward.walk_leg_duty_ratio_target=0.30",
    "reward.walk_leg_duty_ratio_grace_s=3.0",
    "reward.walk_leg_duty_ratio_tau_s=1.0",
    "reward.walk_leg_swing_gap_charge=10.0",
    "reward.walk_leg_swing_gap_grace_s=3.0",
    "reward.walk_leg_swing_gap_cap_s=4.0",
    "reward.k_action_accel=0.02",
    "bus.current_model=power",
]

# DR fields from the training command (mass_scale, leg_mass_jitter_pct,
# link_len_scale_pct, link_len_leg_pct, com_offset_m, friction_scale,
# contact_stiff_scale, ground_tilt_deg, kp_scale_pct, kv_scale_pct,
# vel_scale, cmd_drop_prob_max, placement_noise_deg, bad_start_*,
# joint_zero_bias_deg, gyro_bias_deg_s, imu_*, action_noise, fault_prob,
# ext_push_prob, walk_kick_prob, walk_push_prob) are intentionally
# EXCLUDED here, same rationale as the sibling module: eval/composition
# always runs with randomize=False (dr_scale=0), so these would be
# inert but listing them invites a future edit to flip dr_scale on
# without also restoring them.

CHECKPOINT = "rl_move/sim/policies/ppo_goal_cw_walk50hz_slew_smooth_s0.zip"


def build_cfg_args() -> list[str]:
    """Full ordered --cfg-set VALUE list for the promoted
    `slew-smooth-s0` walk role."""
    return list(CFG_ARGS)


def apply_to_cfg(cfg: dict) -> dict:
    """Apply every ``CFG_ARGS`` key=value onto ``cfg`` in place, via the
    SHARED ``cfg_set.parse_cfg_set`` parser (not a local float-or-string
    reimplementation). Returns ``cfg``."""
    from .cfg_set import parse_cfg_set
    for key, parsed in parse_cfg_set(CFG_ARGS).items():
        sect, name = key.split(".", 1)
        cfg.setdefault(sect, {})[name] = parsed
    return cfg
