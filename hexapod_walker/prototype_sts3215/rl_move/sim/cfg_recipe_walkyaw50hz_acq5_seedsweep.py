"""Canonical `acq5-seedsweep` stationary-heading-hold (task-space
TURN-OFFSET) cfg-set list, versioned in code -- same rationale as
``cfg_recipe_walk50hz_rlonly_v2.py`` (walkcurr, 2026-09-30): the
`eval_walk_turn_compose.py` role-composition tool needs this recipe's
exact contract (SAC, box_yaw=30, walk_yaw_offset_set/frac=1, both-leg
gate) to build the TURN env instance, and a hand-retyped ~90-flag cfg
list is exactly the mistake `probe_currentcap29_flatonly.py`'s
docstring warns about. Verbatim from the recorded launch command
(``ops.sh entry cw-walkyaw50hz-rlonly-scratch-sac-s5-easedterm-
tipmix05-yawbox30-bodyassist-ysema1-term400-gapincome-yawoffset-
bothleggate-acq5-seedsweep``), --cfg-set values only (training-only
flags -- --steps, --seed, --algo, --batch-size, --notes, etc. --
dropped; they don't affect an eval env's construction). DR fields ARE
included (unlike the walk_rlonly_v2 recipe's deliberate omission) --
verbatim fidelity was simpler here and they are inert no-ops whenever
the caller builds the env with ``randomize=False``/``dr_scale=0.0``
(every eval/composition convention in this repo).

This is a MECHANICS-ONLY module (a literal arg list + a thin builder)
-- it does not rank rollouts and carries no reward/behavior opinion.
"""
from __future__ import annotations

# Order matters for --cfg-set (later duplicate keys win). Verbatim
# order from the training command.
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
    "goal.joint_action_box_hip_deg=20.0",
    "goal.joint_action_box_knee_deg=25.0",
    "reward.k_walk_freeprog=2.0",
    "reward.walk_freeprog_cap_m_s=0.06",
    "reward.walk_kernel_vel_ema=1.0",
    "reward.walk_kernel_vel_tau_s=0.1",
    "reward.k_track=0.0",
    "reward.k_roll=0.0",
    "reward.k_pitch=0.0",
    "reward.k_height=0.0",
    "reward.k_gyro=0.0",
    "reward.k_action=0.0",
    "reward.k_action_delta=0.01",
    "reward.k_current=0.0",
    "reward.k_walk_heading=0.0",
    "reward.k_step_event=0.0",
    "reward.k_park_duty=0.0",
    "reward.k_walk_idle_charge=0.0",
    "reward.k_loadslip_excess=0.0",
    "bus.write_speed=4096",
    "bus.servo_vel_max_counts_s=write_speed",
    "bus.write_acc=1000",
    "safety.max_delta_q_deg=7.2",
    "safety.max_current_a=100",
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
    "dr.mass_scale=0.85,1.20",
    "dr.leg_mass_jitter_pct=0.10",
    "dr.link_len_scale_pct=0.02",
    "dr.link_len_leg_pct=0.012",
    "dr.com_offset_m=0.012",
    "dr.friction_scale=0.6,1.4",
    "dr.contact_stiff_scale=0.7,2.0",
    "dr.ground_tilt_deg=2.0",
    "dr.kp_scale_pct=0.20",
    "dr.kv_scale_pct=0.25",
    "dr.vel_scale=0.85,1.10",
    "dr.cmd_drop_prob_max=0.05",
    "dr.placement_noise_deg=2.0",
    "dr.bad_start_prob=0.25",
    "dr.bad_start_max_joints=3",
    "dr.bad_start_deg=8.0,35.0",
    "dr.joint_zero_bias_deg=1.0",
    "dr.gyro_bias_deg_s=0.5",
    "dr.imu_bias_deg=1.0",
    "dr.imu_mount_deg=10.0",
    "dr.imu_pos_xy_m=0.07",
    "dr.imu_pos_z_m=-0.02,0.10",
    "dr.action_noise=0.02",
    "dr.fault_prob=0.3",
    "dr.ext_push_prob=0.3",
    "dr.walk_kick_prob=0.0",
    "dr.walk_push_prob=0.3",
    "reward.walk_leg_duty_ratio_target=0.30",
    "reward.walk_leg_duty_ratio_grace_s=3.0",
    "reward.walk_leg_duty_ratio_tau_s=1.0",
    "reward.walk_leg_swing_gap_grace_s=3.0",
    "reward.walk_leg_swing_gap_cap_s=4.0",
    "reward.walk_turn_kernel_neutral=1.0",
    "safety.max_roll_deg=45",
    "safety.max_pitch_deg=45",
    "goal.joint_action_box_yaw_deg=30",
    "safety.body_pose_assist_start_gain_nm_per_rad=40.0",
    "safety.body_pose_assist_gain_nm_per_rad=0.0",
    "safety.body_pose_assist_max_nm=25.0",
    "safety.body_pose_assist_deadband_frac=0.6",
    "safety.body_pose_assist_ramp_steps=6000000",
    "reward.yaw_still_avg_s=1.0",
    "reward.term_penalty=400",
    "reward.safety_termination_penalty=400",
    "reward.walk_leg_swing_gap_charge=0.0",
    "reward.walk_leg_swing_gap_income=10.0",
    "reward.walk_leg_duty_ratio_charge=0.0",
    "reward.walk_leg_duty_ratio_income=10.0",
    "goal.walk_turn_in_place_frac=0.0",
    "goal.walk_yaw_cmd=0",
    "goal.walk_yaw_offset_frac=1.0",
    "goal.walk_yaw_offset_set=15,30,45,90,-15,-30,-45,-90",
    "reward.k_walk_yaw=0.0",
    "reward.k_walk_yaw_offset=1.0",
    "reward.k_walk_yaw_offset_hold=50.0",
    "reward.k_yaw_prog=0.0",
    "reward.k_yaw_still=0.0",
    "reward.walk_yaw_hold_prog_gate=0.0",
    "reward.walk_yaw_kernel_gate=0.0",
    "reward.walk_yaw_offset_hold_leg_gate=1.0",
    "reward.walk_yaw_offset_kernel_leg_gate=1.0",
]

CHECKPOINT = ("rl_move/sim/policies/"
              "ppo_goal_cw_walkyaw50hz_rlonly_scratch_sac_s5_easedterm_"
              "tipmix05_yawbox30_bodyassist_ysema1_term400_gapincome_"
              "yawoffset_bothleggate_acq5_seedsweep.zip")

# Discrete relative-heading offsets (radians) this checkpoint trained
# on -- goal.walk_yaw_offset_set above, degrees->radians. The
# composition tool draws turn segments from this exact set so it never
# asks the specialist to hold a target it never saw in training.
OFFSET_SET_DEG: list[float] = [15.0, 30.0, 45.0, 90.0,
                               -15.0, -30.0, -45.0, -90.0]


def build_cfg_args() -> list[str]:
    """Full ordered --cfg-set VALUE list for the acq5-seedsweep
    stationary-heading-hold turn role."""
    return list(CFG_ARGS)


def apply_to_cfg(cfg: dict) -> dict:
    """Apply every ``CFG_ARGS`` key=value onto ``cfg`` in place, via the
    SHARED ``cfg_set.parse_cfg_set`` parser. Returns ``cfg``."""
    from .cfg_set import parse_cfg_set
    for key, parsed in parse_cfg_set(CFG_ARGS).items():
        sect, name = key.split(".", 1)
        cfg.setdefault(sect, {})[name] = parsed
    return cfg
