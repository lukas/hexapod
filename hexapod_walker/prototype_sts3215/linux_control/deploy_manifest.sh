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
  drive_controller.py cpg_controller_loader.py
  mcu_feetech_bus.py async_bus_guard.py bench_api.py web_drive.py xbox_drive.py
  motor_setup_api.py webui_config.py requirements-robot.txt
  joint_calibrate.py plant_calibrate.py geometry_plant.py imu_calibrate.py
  event_log.py telemetry_recorder.py async_bus_guard.py
  command_journal.py deploy_record.py
  status_display.py deploy_status_display.py servo_watch.py
  mpu_probe.py rl_policy.py safe_zero.py pinned_tip.py
  sysid_protocol.py sysid_runner.py
  bus_bench.py touchdown_zero.py rl_walk_start.py
  standup_modes.json
)

# Directories shipped wholesale into linux_control/.
# api/ = the BenchAPI route-group mixins (bench_api.py is the dispatcher).
LC_DIRS=(api webui vendor systemd)

# motor_setup files shipped to the board (canonical copies; includes the
# on-board run.sh wizard entrypoint).
MOTOR_FILES=(
  __init__.py feetech_bus.py urt2_bench.py inplace_demos.py
  motion_telemetry.py
  registry.py urt2_motor_setup.py run.sh README.md
)

# rl_move numpy-only core subset (imported by rl_policy.py).
RLMOVE_FILES=(
  __init__.py env.py robot_state.py attitude.py safety.py
  config.py config.yaml body_ik.py control_loop.py logger.py
  np_policy.py deployed_policy.py contact_predictor_model.json
)

# rl_move/sim numpy-only helpers (rot-60 canonicalizer + sagittal mirror).
RLMOVE_SIM_FILES=(__init__.py rot60.py mirror.py)

# stage_deploy_tree <stage_dir> <linux_control_src_dir>
# Builds the EXACT remote bundle layout under <stage_dir>.
write_deploy_record() {
  local stage="$1" src="$2" rev branch dirty deployer host now tree_hash
  rev="$(git -C "$src" rev-parse HEAD 2>/dev/null || echo unknown)"
  branch="$(git -C "$src" rev-parse --abbrev-ref HEAD 2>/dev/null || echo unknown)"
  if [ -n "$(git -C "$src" status --porcelain 2>/dev/null)" ]; then
    dirty=true
  else
    dirty=false
  fi
  deployer="${HEXAPOD_DEPLOYER:-${USER:-unknown}}"
  host="$(hostname -s 2>/dev/null || echo unknown)"
  now="$(date -u +%Y-%m-%dT%H:%M:%S.000Z)"
  # Hash of the staged tree itself: the deterministic identity of what ships,
  # independent of whether the source checkout was clean.
  tree_hash="$(cd "$stage" && find . -type f ! -name deploy_record.json -print0 \
    | LC_ALL=C sort -z | xargs -0 shasum -a 256 2>/dev/null \
    | shasum -a 256 | cut -d' ' -f1)"
  mkdir -p "$stage/linux_control"
  cat > "$stage/linux_control/deploy_record.json" <<EOF
{
  "schema_version": 1,
  "deploy_id": "${tree_hash:0:16}-$now",
  "deployed_at": "$now",
  "deployer": "$deployer",
  "deployed_from_host": "$host",
  "source_path": "$src",
  "git_revision": "$rev",
  "git_branch": "$branch",
  "source_dirty": $dirty,
  "staged_tree_sha256": "$tree_hash",
  "transport": "${HEXAPOD_DEPLOY_TRANSPORT:-unknown}"
}
EOF
}

stage_deploy_tree() {
  local stage="$1" src="$2" proto f
  proto="$(cd "$src/.." && pwd)"

  mkdir -p "$stage/linux_control/policies" "$stage/motor_setup" \
    "$stage/rl_move/sim"

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

  # Last, so the receipt hashes the tree that actually ships: after caches
  # and macOS junk are removed, and excluding the receipt itself.
  write_deploy_record "$stage" "$src"
}

# PYTHONPATH used when launching on-board tools from linux_control/
# (mirrors the systemd unit: vendor, motor_setup, cwd, bundle root).
REMOTE_PYTHONPATH_FROM_LC='vendor:../motor_setup:.:..'
