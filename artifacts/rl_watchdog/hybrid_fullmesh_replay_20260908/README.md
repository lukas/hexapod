# Full-mesh assisted composition comparison

The newer yawref-cigate8m walking checkpoint passes the listed demo bars in
a matched full-mesh trial against the incumbent stdanneal policy.

| Metric | Candidate | Incumbent |
| --- | ---: | ---: |
| Walking progress ratio | 0.413 | 0.359 |
| 1-second course median / p90 | 3.29 / 14.84 degrees | 13.26 / 25.26 degrees |
| Current p95 | 1.676 A | 1.974 A |
| Terminations / phase errors | 0 / 0 | 0 / 0 |
| Valid walking gait | true | true |

This is a composed controller: scripted tuck stand/lower plus learned walking.
It is one deterministic seed-0, DR-0 trial per arm: 28 seconds of commanded
walking within a 50.02-second stand/walk/stop/restart/lower sequence. Every
actual yaw command is zero. It does not establish continuous-yaw, tip recovery,
hardware readiness, randomized robustness, or a single policy for the whole
sequence. The candidate retains its separate FAIL-QUALIFICATION lineage result.

The first cloud A/B used the simplified mesh_mjx twin. Root preserved that
result, then replayed both arms with the requested frozen full mesh: 34 meshes,
159 geoms, 4.80573 kg, XML SHA 7efb8e8a0cb014c0b4bac27c41e7a85e683553168b87d85aac0d52d6a8e5a837.
Both full-mesh exits were 0. Checkpoints, config lists, base configuration,
tuck definitions and harness hashes were pinned to the original A/B. The
400/20/0.375/350/100Hz motor contract, resets, phase marks, and all timestamped
commands match across arms. Reintegrating recorded command ramps and actual
velocity reproduces the progress scores; stop labels contain ramp-down demand.

The original twin report mixed incumbent 2-second course values with candidate
1-second values in its displayed table. This comparison consistently uses
1-second fields; all underlying 1- and 2-second fields are retained.

No new PPO arm or physical robot action was performed by this replay. There is
no measured candidate transition deficit here to justify that conditional arm.
Continuous yaw remains the separate unmet steering problem.

Evidence: comparison.json, replay_manifest.json, exact argv/effective configs,
per-arm summary/transfer/composition files and compressed ticks. Full videos
and contact sheets are preserved on the controller at:
hexapod_walker/prototype_sts3215/logs/ckpt_eval/hybridab_yawref_fullmesh_20260908/
The isolated replay worktree also remains at /workspace/hexapod_hybrid_fullmesh_20260908.
