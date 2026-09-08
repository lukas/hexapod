set -eu
cd /workspace/hexapod-turnphase-wt/hexapod_walker/prototype_sts3215
OUT=logs/ckpt_eval/root_fullcone_20260908
uv run python -m rl_move.sim.probe_turn_traction --policy scripted --engine audit --cfg-json cfg_frozen_audit.json --cells 0.08:0.15,0.08:-0.15,0.08:0 --phase-offsets 0.0,3.14159265 --plant fullmesh --seed 0 --episode-seconds 15 --label root_fullcone_scripted_fm --out "$OUT/scripted_audit_fm.json" > "$OUT/scripted_audit_fm.log" 2>&1
uv run python -m rl_move.sim.probe_turn_traction --policy checkpoint --checkpoint rl_move/sim/policies/ppo_goal_cw_robotwalk_turns_20260907_yawref_cont8m.zip --engine audit --cfg-json cfg_frozen_audit.json --cells 0.08:0.15,0.08:-0.15,0.08:0 --phase-offsets 0.0,3.14159265 --plant fullmesh --seed 0 --episode-seconds 15 --label root_fullcone_checkpoint_fm --out "$OUT/ckpt_audit_fm.json" > "$OUT/ckpt_audit_fm.log" 2>&1
echo ALL_DONE
