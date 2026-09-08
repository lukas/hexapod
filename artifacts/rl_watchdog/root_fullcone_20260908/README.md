# Corrected full-cone steering rerun

All 12 original-plant audit cells reproduce the original behavior and pre-existing audit/planar metrics **bit for bit**. Full-cone and momentum checks pass in every cell; no falls occurred.

The full condim6 **elliptic** cone is near its boundary (usage>0.9) in **48.01–58.54%** of slipping-foot samples, versus **4.05–8.38%** for the old planar projection. Arc-only full-cone fractions are 48.01–52.40%. This overturns the previous claim that saturation was absent. Full usage also remains below 0.5 in 26.18–43.23% of samples: the result is mixed, not universal saturation or a unique cause of the yaw deficit.

Fractions pool over feet, weighted by slipping-foot-substep counts. Loading means any active compressive contact, without a 2 N threshold. Material-point XY slip speed is conditioned per foot; utilization is the maximum over that foot's contacts. These are not independent trials or a same-contact dissipation measurement.

The matched recipe uses scripted TripodGait 6 cells plus the retained yaw-cont8m checkpoint 6 cells: vx 0.08 m/s, wz +0.15/-0.15/0 rad/s, starts 0/3.14159265, seed 0, 15-second episodes, audit engine only. The original 34-mesh, 4.80573 kg plant and 100 Hz motor contract remain: write_speed 400, acc 20, resolved ceiling 350 counts/s, slew 0.375 deg/tick. Only authority-audit and traction-runner source files were copied to the frozen worktree. Its sim_env.py hash and original XML/config/checkpoint/34 asset hashes were verified before staging; the concurrent scratch owner's friction helper was not copied. No changed-friction cells, training, robot work or process interventions were performed.

Source repository HEAD at staging was 67ebc1524e84d554867424656f2717d09a5965a0; launch_manifest.json records exact hashes of the two copied modules despite concurrent main advancement. Momentum relative RMS residuals are 0.000655–0.001493.

Raw corrected reports are scripted_audit_fm.json and ckpt_audit_fm.json. The original_* reports retain the exact baselines. launch_manifest.json/run_root_fullcone.sh record input/source hashes and the recipe. comparison.json contains per-cell parity, cone statistics/components, force/couple impulses and raw-file hashes. Reproduce its checks from the repository root with:

    uv run python artifacts/rl_watchdog/root_fullcone_20260908/compare.py

No behavior qualification or hardware calibration claim follows from these measurements.
