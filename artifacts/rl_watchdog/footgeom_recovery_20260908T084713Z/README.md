# Radius probe recovery, 2026-09-08

The old radius training arm completed naturally at 2,097,152 actual steps before the 09:10:26 UTC recovery check. No kill was issued. Its checkpoint, log and CPU finalizer were retained; the existing verdict helper recorded `INVALID_PHYSICS` with `CANARY FAIL - INFRASTRUCTURE` and mirrored the reason into W&B/RL_LOG. The old frozen-policy probe is retained as invalid-method evidence.

The corrected probe completed at 09:13:56 UTC. It used the exact original `/tmp/footgeom_probe_run.sh` argument list with only the output changed to `_compilefix1`. The original parent checkpoint SHA256 was verified as `e92377d6e133cb68051b71738845ce2c6419fc308fe19836df8466f338696ca0`; the invalid child was not loaded. Source was `9370228d0b888e28ea719fa707d8898d3d3084ab`, verified to contain deployed repair `d54506ef2ad2dfc19dfc52929fa3e90aa696771b`. Per-file source hashes and the full parsed cfg/argv are in `probe_provenance.json`.

The model is the **mesh_mjx twin**, 91 geoms, 0 meshes, 4.80573 kg, 500 Hz physics and 100 Hz control. All six radius/compiled bounds are 13.5 mm. Before launch, baseline and corrected body masses, inertias, inertial frames and friction arrays were exactly equal; 24 paired sequential reset randomization/RNG draws matched. The completed report's randomization dictionaries also match the original parent gate for all 24 corresponding episodes. Report model, motor, seed, DR and start-jitter metadata match. This is a simulation geometry sensitivity, not a hardware calibration or full-STL qualification.

The probe preserved seed 0, six episodes per group, deterministic/stochastic × nominal/start-jitter, 20 seconds, own cfg randomization, and no video. The evaluator ran in the canonical controller report directory, so native `eval_report` could read it directly; no ad hoc report copy-back was used. The exact native keys are the parent run stem plus `_gate`, `_footgeom0135_probe` (invalid) and `_footgeom0135_probe_compilefix1` (corrected); their full paths are in provenance and report files.

| Group | Parent median slip/m | Corrected | Change | Gait valid | Falls |
|---|---:|---:|---:|---:|---:|
| Nominal det | 4.9805 | 5.6690 | +13.8% | 6/6 | 0 |
| Nominal sto | 5.1725 | 6.0320 | +16.6% | 5/6 | 0 |
| Start-jitter det | 5.1030 | 5.5370 | +8.5% | 5/6 | 0 |
| Start-jitter sto | 5.4155 | 5.8595 | +8.2% | 6/6 | 0 |

The original finite decision required median slip improvement of at least 10% in at least three groups, at most one fall, and no new chronic sacrifice (the same leg flagged in at least four of six episodes within a group). **Zero groups improve; all four worsen.** Gait is unchanged at 22/24, with zero falls and identical sparse leg-2 flags. Therefore the corrected frozen probe does not support the original training premise, and **no replacement 2M PPO was launched**. This dose/checkpoint result does not establish universal geometry-class failure.

`recovery_state.json` records actual progress: the same Python PID advanced from six to eighteen completed episodes across a 38-second observation interval and then completed all 24. The active unrelated half-gravity runs were untouched. Root owns publication and downstream scientific decisions; no CPU completion wait or recovery launch remains pending.

Reproduce the table/decision locally with `uv run python compare.py`. Raw JSON files were obtained through native MCP. Their local SHA256s are in `receipt_hashes.json`.
