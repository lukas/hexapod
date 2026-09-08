# Frozen-parent torque1x zero-shot evaluator recovery — 2026-09-08

This recovers the existing cycle20260908T080122 comparison. No PPO, new seed, physical action, reward change, or additional training budget was introduced.

The initial OFF baseline on train9 failed before simulation because its older evaluator rejected `--video-fps25`. Source review additionally showed that the completed ON baseline on train5 used pre-Cartesian `joint_task.py`: it had no Cartesian action decoder and therefore interpreted the ON actor through joint-space decode. That old ON report is **not comparable** with the trained-child gates. Its complete JSON and the failed OFF log are preserved here and their original remote output paths were not overwritten.

The controller matched the trained-child evaluator on train4; train8 matched every relevant evaluator, decoder, environment, reward, motor, model/config and shared dependency checked. Idle5/9 were synchronized using the existing `snapshot.sh --sync` helper, preserving policies, outputs and STL assets. Both now stamp `f99cb4d4d4ff414bb7e958748e3b75d950c86432`. Post-sync verification matched174 source dependency files to child4, the actual motor-model JSON, and all recorded Python package versions. Fifteen key source hashes are explicitly compared across controller, child4, child8, corrected5 and corrected9 in `recovery.json`. Train5’s pre/post semantic diff is preserved separately.

Each corrected arm uses its own retained40M checkpoint and own exact source cfg (51 ON cfg entries including its three Cartesian box keys;48 OFF entries with Cartesian decode disabled). The only source-cfg change is the preregistered torque scaling `3,3`→`1,1`. Checkpoint SHA256 values remain:

- ON: `569dfa7f5851307839559b53f636754d9c599432979707198a061597ceb78579`
- OFF: `f4b962c1a851b2b413625d631969b9d63e509633f2f64629733c2141982d014e`

Protocol: seed0;20s episodes;6 episodes in each nominal deterministic, nominal stochastic, start-jitter deterministic and start-jitter stochastic group; DR0; original100Hz control/motor configuration;25fps video. Start-jitter settings remain3degrees, bad probability0.25, at most1 bad joint,8–16degrees. Model remains the4.80573kg MJX mesh-family twin (0 meshes/91 geoms), not full-STL hardware qualification. No success claim is made before the complete24episode reports.

Corrected outputs use the common suffix `_torque1x_zeroshot_evalfix1`. Exact commands, cfg, checkpoint provenance, fresh source manifests, preserved failures, idle check and sync receipts are in the JSON and shell files here. Launches used foreground`cd` and detached stdin/stdout/stderr; live evaluator FDs confirm `/dev/null` plus only their own log.

Verified progression08:33:36→08:34:30UTC:

| Arm / pod | Actual Python PID | Completed clips | CPU ticks | Completed simulated time |
| --- | ---: | ---: | ---: | ---: |
| ON / train5 |1155623|1→3|25698→70881|60s|
| OFF / train9 |4143559|1→3|27840→76302|60s|

Each completed clip contains500frames/20seconds at25fps. Both evaluators are healthy and still running; final reports remain pending. Follow the exact paths in `recipes.json`; do not replay either arm while these processes are active.
