# Environment-only Cartesian Warp bank — PASS

Reuse `MjxShardedVecEnv` directly: four environments, two host workers,
`impl="warp"`, one pooled reset per environment, existing RNG 2, 100 Hz.
`source_recipe.json` contains the exact 78 cfg overrides from the original
scratch champion and only the three proposed Cartesian box overrides
(0.06/0.035/0.04 m). The shortened 1.2-second horizon is an integration-test
setting, not a behavioral gate; no policy or checkpoint is loaded.

Coverage: assert actual GPU/Warp backend and worker FakeData, exercise the
real worker `_act_to_q` path against CPU targets before/after model DR,
finite runtime steps, two rejected-action resets that consume/refill a
one-entry pool, a second complete reset and subsequent stepping. Natural
truncations are counted separately. CPU-vs-Warp physics trajectories are not
compared; PASS means runtime/decode integration only. No PPO/optimizer or
W&B run is constructed.

The existing `test_mjx_vec_env.py` is CPU-MJX pinned and defaults to impl=None;
`bench_mjx.py` bypasses the task decoder. Running either unchanged would not
exercise this feature's GPU integration. This runner reuses their existing
VecEnv API/reset strategy without rerunning unrelated tests.

## Ownership and sync prerequisites

Root selects train-11 only after fresh process/GPU/memory checks and announces
this bounded bank to active owner 042639. There is no general per-pod lease API
in the inspected helpers; do not invent a lease file. `capacity.py` reports
trainers, so its FREE label alone does not exclude evaluation/probe processes.
The full source tree must be synced from the corrected controller source,
including `cart_foot_decode.py`, `joint_task.py`, and supporting host/backend
code. `snapshot.sh --sync` records a `-dirty` code marker when appropriate;
keep it and record exact source hashes instead of pretending this is committed.
This is a test sync, not a training launch.

The commands below describe the bank sequence. Controller default service-account
RBAC did not permit the pod file-copy calls; root executed those calls from the
local client with its existing --kubeconfig=/Users/lukas/.kube/coreweave.yaml.
Do not retry the denied default service-account path.

Prepare this artifact directory at `/tmp/cart_foot_gpu_bank_20260908` on the
controller. Run these commands from the controller's prototype root **only
after root's fresh checks/ownership announcement**:

```sh
POD=hexapod-mjx-train-11
bash rl_move/orchestrator/snapshot.sh --sync "$POD"
uv run python - <<'CODE'
import json, runpy
from pathlib import Path
folder = Path('/tmp/cart_foot_gpu_bank_20260908')
bank = runpy.run_path(str(folder / 'bank.py'))
hashes = {name: bank['file_hash'](name) for name in bank['SOURCE_FILES']}
(folder / 'expected_hashes.json').write_text(json.dumps(hashes, indent=2))
CODE
kubectl exec "$POD" -- mkdir -p /tmp/cart_foot_gpu_bank_20260908
for name in bank.py source_recipe.json expected_hashes.json; do
  kubectl cp "/tmp/cart_foot_gpu_bank_20260908/$name" "$POD:/tmp/cart_foot_gpu_bank_20260908/$name"
done
kubectl exec "$POD" -- bash -lc 'cd /workspace/prototype_sts3215 && JAX_PLATFORMS=cuda HEXAPOD_MODEL_SOURCE=mesh_mjx HEXAPOD_CONTROL_HZ=100 OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 XLA_PYTHON_CLIENT_PREALLOCATE=false timeout --signal=TERM --kill-after=30s 600s uv run python /tmp/cart_foot_gpu_bank_20260908/bank.py --recipe /tmp/cart_foot_gpu_bank_20260908/source_recipe.json --expected-hashes /tmp/cart_foot_gpu_bank_20260908/expected_hashes.json --ticks 130 --out /tmp/cart_foot_gpu_bank_20260908/result.json > /tmp/cart_foot_gpu_bank_20260908/bank.log 2>&1'
```

Use a short tool yield when running the final command; the process can remain
active while root reads its isolated log. Do not register it as `evalpending`:
that is an eval ownership/trigger mechanism, not a general GPU lease, and this
bank is already attached to active 042639. Copy back log/result/source hashes
when done. A timeout or incomplete construction is not a passing bank.

The file must remain a real `.py` file with its main guard: multiprocessing
uses spawn, so piping the runner into Python stdin would fail. Normal errors
and SIGTERM run `try/finally` cleanup; the outer timeout caps a stuck worker
shutdown. Default upper work bound is 131 vector ticks (524 environment ticks)
plus bounded reset choreography; CLI rejects more than 260 loop ticks.

Preparation validation was an AST syntax check. The subsequent root execution
and GPU integration result are recorded below.


## Root execution result

Executed on train-11's H200 with synchronized dirty-source marker
36a0f709b7c2db2776b021e1a870f0c9b7058a7d-dirty. The 13 recorded source hashes
match the controller manifest before and after execution. PASS: 131 vector
ticks, two forced pool pops/refill, four natural truncations and a second
full reset; actual FakeData worker decode matches CPU targets to 1e-12 rad.
Per-world geometry randomization was exercised. This is runtime/decode
integration evidence, not CPU/Warp physics-trajectory parity or a behavioral
gate. No optimizer, checkpoint or W&B run was created.
Root verified exit 0 and NVIDIA 0%/0 MiB after cleanup. See result.json and
bank.log for full evidence. The root client used its existing authorized
kubeconfig for file copies after the controller's default service-account
copy attempt lacked RBAC permission; no role or security setting changed.
