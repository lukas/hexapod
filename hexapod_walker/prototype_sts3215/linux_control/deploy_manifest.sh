# deploy_manifest.sh — THE single source of truth for what ships to the
# robot. Sourced by deploy_ssh.sh and deploy_adb.sh; both build the
# identical staged tree via stage_deploy_tree() and differ only in
# transport (tar|ssh vs adb push).
#
# Remote layout under /home/arduino/hexapod_sts (the "bundle root"):
#   linux_control/   robot server + control modules + webui/policies/vendor/systemd
#   hexapod_core/    shared robot/sim contract package (ships WHOLESALE)
#   motor_setup/     bench bring-up tools (canonical copies; on-board ./run.sh)
#   rl_move/         numpy-only RL core subset for rl_policy.py
#
# The old urt2_setup/ bundle (a stale-prone duplicate of motor_setup) was
# retired 2026-08-29; stage_deploy_tree knows nothing about it and the
# deploy scripts remove leftovers from the board.

# Individual files shipped into linux_control/.
LC_FILES=(
  tripod_gait.py drive_controller.py cpg_controller_loader.py
  mcu_feetech_bus.py bench_api.py web_drive.py xbox_drive.py
  joint_calibrate.py plant_calibrate.py geometry_plant.py imu_calibrate.py
  event_log.py status_display.py deploy_status_display.py servo_watch.py
  mpu_probe.py rl_policy.py safe_zero.py pinned_tip.py
  noslip_gait.py se2_foot_gait.py sysid_protocol.py sysid_runner.py
  bus_bench.py touchdown_zero.py walk_ready_transition.py rl_walk_start.py
  rl_policy_weights.json rl_walk_weights.json standup_modes.json
)

# Directories shipped wholesale into linux_control/.
# api/ = the BenchAPI route-group mixins (bench_api.py is the dispatcher).
LC_DIRS=(api webui policies vendor systemd)

# motor_setup files shipped to the board (canonical copies; includes the
# on-board run.sh wizard entrypoint and the dance/quad legacy stubs).
MOTOR_FILES=(
  __init__.py feetech_bus.py urt2_bench.py inplace_demos.py
  quad_walk.py dance_script.py motion_telemetry.py
  motor_setup_registry.json urt2_motor_setup.py run.sh README.md
)

# rl_move numpy-only core subset (imported by rl_policy.py).
RLMOVE_FILES=(
  __init__.py env.py robot_state.py attitude.py safety.py
  config.py config.yaml body_ik.py control_loop.py logger.py
  np_policy.py joint_frame.py
)

# rl_move/sim numpy-only helpers (rot-60 canonicalizer + sagittal mirror).
RLMOVE_SIM_FILES=(__init__.py rot60.py mirror.py)

# stage_deploy_tree <stage_dir> <linux_control_src_dir>
# Builds the EXACT remote bundle layout under <stage_dir>.
stage_deploy_tree() {
  local stage="$1" src="$2" proto f
  proto="$(cd "$src/.." && pwd)"

  mkdir -p "$stage/linux_control" "$stage/motor_setup" "$stage/rl_move/sim"

  for f in "${LC_FILES[@]}"; do
    cp "$src/$f" "$stage/linux_control/"
  done
  for f in "${LC_DIRS[@]}"; do
    cp -R "$src/$f" "$stage/linux_control/"
  done

  for f in "${MOTOR_FILES[@]}"; do
    cp "$proto/motor_setup/$f" "$stage/motor_setup/"
  done

  # hexapod_core ships wholesale — no curated list to forget to update.
  cp -R "$proto/hexapod_core" "$stage/hexapod_core"

  for f in "${RLMOVE_FILES[@]}"; do
    cp "$proto/rl_move/$f" "$stage/rl_move/"
  done
  for f in "${RLMOVE_SIM_FILES[@]}"; do
    cp "$proto/rl_move/sim/$f" "$stage/rl_move/sim/"
  done

  touch "$stage/linux_control/__init__.py"

  # Never ship caches or macOS junk.
  find "$stage" -name '__pycache__' -type d -exec rm -rf {} + 2>/dev/null || true
  find "$stage" -name '.DS_Store' -delete 2>/dev/null || true
}

# PYTHONPATH used when launching on-board tools from linux_control/
# (mirrors the systemd unit: vendor, motor_setup, cwd, bundle root).
REMOTE_PYTHONPATH_FROM_LC='vendor:../motor_setup:.:..'
