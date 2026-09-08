# Opt-in evaluation video pacing: isolated rendering benchmark

Completed on the Linux controller on 2026-09-08. This measures a short rendering workload, not a canonical walking gate or a promised full-gate speedup.

The benchmark loaded the actual checkpoint from `cw-walkscratch-crutchoff-s1-widen8-legdutyratio-guardfix-acq10m` (MD5 `fb3faa76e582e7c065569384b5939f4d`) and compared legacy capture with 25 fps capture using the same configuration and random seeds. Both deterministic and stochastic comparisons preserved every scientific episode field and every recorded action/state/reward trace value exactly.

| Mode | Capture | Rollout/render wall seconds | Process CPU seconds | Frames | Encoded seconds |
|---|---|---:|---:|---:|---:|
| Deterministic | Legacy, every 100 Hz tick | 8.681 | 70.130 | 120 | 4.8 |
| Deterministic | 25 fps | 2.294 | 15.218 | 30 | 1.2 |
| Stochastic | Legacy, every 100 Hz tick | 8.468 | 64.070 | 120 | 4.8 |
| Stochastic | 25 fps | 2.429 | 17.162 | 30 | 1.2 |

Each rollout simulated 1.2 seconds at 100 Hz; four rollouts total 4.8 seconds. Timings exclude renderer warmup and video encoding; separate encoding times are retained in results.json. Process CPU time includes rendering threads. Video encoding was independently read back to verify frame counts, 25 fps and duration. Endpoint capture is preserved.

## Model selection and scope

The controller's default mesh XML (`47081bf1...`) contains a 3.494226 kg model. The initial benchmark stopped before rendering because this did not match the intended frozen plant. The corrected temporary script selects the existing frozen asset directory:

`/workspace/hexapod-turnphase-wt/hexapod_walker/prototype_sts3215/mesh_mujoco`

It asserts XML SHA256 `7efb8e8a0cb014c0b4bac27c41e7a85e683553168b87d85aac0d52d6a8e5a837`, 34 meshes and total mass 4.80573 kg. Exact XML/STL hashes, evaluator hash, checkpoint identity and configuration are in results.json. No production source, configuration, active evaluator, trainer or finalizer was changed.

This is a renderer benchmark with an actual trained policy. It deliberately selects the frozen full mesh and disables randomization in both arms; it is not the checkpoint's canonical held-out gate. Environment seed is 0, policy/global RNG seed is 19, and Torch uses two threads. Longer scenes, different CPU contention and encoding/copy-back costs can change full-gate speedup.

## Reproduction

The script imports the revised evaluator explicitly from `/tmp/hexapod_eval_checkpoint_pacing_f37ab4beb.py` while retaining normal shared imports. Stage the evaluator from core commit `f37ab4beb2f5c681180e3b8de67d7692d3cac85d` at that path, and this script at its recorded temporary path. On a compatible controller with the same frozen assets and retained checkpoint:

```sh
nice -n 19 uv run python /tmp/hexapod_video_pacing_benchmark_f37ab4beb_frozen.py
```

The script writes only its separate `/tmp/hexapod_video_pacing_benchmark_f37ab4beb_frozen/` output directory. It never launches training or publishes gate results. Videos are omitted from this repository receipt.
