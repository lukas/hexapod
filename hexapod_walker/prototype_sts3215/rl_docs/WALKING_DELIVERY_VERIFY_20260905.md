# Walking delivery verification — 2026-09-05 (orchestrator, controller pod)

Executes operator feedback `fb_20260905T075426_969b3d` ("keep 100 Hz and
isolate filter lag") against the published `codex/smooth-walking-delivery`
branch (tip `c3f3ddb4`), in an isolated worktree. CPU only; zero PPO; no
physical robot access; the policy stays 100 Hz throughout. The Codex-owned
runtime/exporter files were not edited; main's campaign source is untouched.

## 1. Copied actor and model/motor hash verification

- **Actor bytes are NOT verifiable from this pod.** The frozen actor
  (`hardware-walk-noyaw-v2-canary`) lives in the operator checkout's
  untracked `artifacts/rl_policy_hardware/...`; it is not in the repo, the
  run ledger, or the W&B project. What IS verifiable: `actor_sha256`
  (`58a9bbf7…`) and `checkpoint_sha256` (`250643a4…`) are **bit-identical
  across all six replay reports and the checked-in Robot Lab timing canary
  plan** — internally consistent provenance, single frozen actor everywhere.
- **Motor model MATCHES:** `rl_move/sim/sim_model.json` sha256 `6968268e…`
  matches this repo bit-exactly in every report row.
- **Sim model MISMATCH (honest flag):** all replay rows ran on a
  **4.80573 kg full-mesh model** (`hexapod_mesh.xml` sha `7efb8e8a…`)
  generated in the operator's checkout. This repo cannot regenerate it:
  a fresh `build_mesh_model.py` build here gives **3.490 kg**
  (sha `dd6275c0…`; the campaign's audited as-built mass is 3.50 kg), with
  **19/34 referenced meshes byte-different** (coxa/femur/tibia links,
  servos, chassis, bearings). The published absolute progress/slip numbers
  are therefore tied to a model ~37 % heavier than the audited as-built
  robot; the branch doc itself flags this. Which CAD state produced 4.8 kg
  needs a Codex-side answer (their checkout at
  `/Users/lukas/Documents/ChatGPT/hexapod project`).
- Side observation: a fresh mesh build also rewrites the TRACKED
  `hexapod_mesh_mjx.xml` twin (current CAD, incl. the 09-04 leg-geometry/
  boot update, no longer reproduces the committed twin bit-exactly). Both
  checkouts were restored to the committed twin; no training default was
  changed. Worth a deliberate refresh decision later — separate question.

## 2. Faster-filter comparison — independent reproduction

Since the exact actor is unavailable here, the comparison was reproduced
with a DIFFERENT frozen 100 Hz actor under the identical harness: the
todaypolicy bundle walk role
(`cw-walk-allheading-mlp-singleframe-acq1-stdanneal`, obs 74 / hidden
128×128 / robot_abs_tibia_v2 / walk_obs_body_vel=2 / 0.08 m/s — same
contract family as the canary), exported via `export_policy_np` (parity
1.4e-07), on this repo's regenerated 3.490 kg full mesh. Same seed,
10 s, DR-0, forward + sideways. Artifacts:
`logs/ckpt_eval/deployed_transport_substitute_20260905*`.

| Policy 100 Hz, write/feedback | fwd prog (op / here) | side prog (op / here) |
|---|---|---|
| nominal | .433 / .426 | .379 / .360 |
| 50 / 10 (orig filters) | .294 / .269 | .297 / .230 |
| 50 / 50 (orig alphas) | .368 / .350 | .359 / .324 |
| 50 / 50, matched slow bandwidth | .296 / .335 | .280 / .236 |
| 50 / 10, faster filters | .366 / .340 | .327 / .266 |
| 100 / 100 | .414 / .422 | .369 / .361 |

Filter-alpha arithmetic verified exact: fast = 1−0.7⁵ / 0.98⁵; matched
slow bandwidth = 1−0.7^(1/5) / 0.98^(1/5).

**Reproduced on a different actor and different-mass model:** the deployed
transport costs real progress; faster filters at the existing 10 Hz
feedback recover ~88 % of the forward 50 Hz-sensing gain (op: ~100 %);
sideways recovers only ~38 % (op: ~48 %) — sideways genuinely wants
cadence, matching the branch doc. **One honest divergence:** the
matched-slow-bandwidth control removes essentially all of the sideways
gain here (as published) but only ~19 % of the forward gain (op: ~all) —
for this actor a real fraction of the forward 50 Hz gain is cadence, not
filter lag. The "filter lag is a major, separable component" conclusion
stands; its forward-share is actor-dependent.

## 3. Matched noise-sensitivity screen (new, opt-in tooling)

`eval_deployed_transport.py` gained `--sensor-noise-json`
(`NoisySensorTransport`): seeded fixed-block noise injected on the RAW
frame at the transport acquisition hook (encoder/gyro/accel-tilt, before
the hardware filters), bit-identical draws across filter arms, identity at
zero scales; 3 new unit tests (19/19 file green; envelope bank 13/13).
Deployed-only cells (the nominal path has no acquisition hook). Scales =
campaign DR floors: encoder 0.09°, gyro 0.5°/s, tilt 0.3°.

| arm (w50) | clean fwd/side | 1× floor | 2× floor |
|---|---|---|---|
| s10 orig filters | .269 / .230 | .292 / .236 | .294 / .292 |
| s10 **fast filters** | .340 / .266 | .324 / .249 | .280 / .256 |
| s50 orig alphas | .350 / .324 | .333 / .263 | — |

At 1× DR-floor noise the fast-filter candidate keeps most of its clean-sim
forward advantage (.324 vs .292, slip 3.82 vs 4.23). At 2× floor the
advantage is gone forward (.280 vs .294, slip 4.59 vs 4.07). Single
deterministic 10 s cells — a screen, not a gate; treat ±0.03 as noise.
**Consequence:** the faster filters are usable-looking at nominal noise but
their margin dies within 2× — the branch's "first inspect estimator
response against recorded encoder/IMU data" order is the right gate before
any deployment decision. No deployment recommendation is made here.

## 4. Stop/restart slip measurement — corrected and re-run

The worktree's corrected evaluator
(`slip_metric_version=commanded_intervals_v2_stop_history_advanced`)
was re-run on the **exact published model** (08-30 mesh, verified by
bit-identical progress vs `command_envelope_v1_09-05/summary.json`),
scenario `stop_restart`, seed 0 (published seed 0/1 rows were identical):
`logs/ckpt_eval/command_envelope_stoprestart_slipv2_09-05/`.

| arm | published slip/ach-m (v1, biased) | corrected (v2) |
|---|---|---|
| baseline | 1.384 | **1.314** |
| env_shared / env_yawpri | 1.559 | **1.365** |

The old metric charged paused-interval foot drift to the restart: the
envelope's apparent +12.6 % stop/restart slip penalty vs baseline is
mostly artifact; the real penalty is **+3.9 %** (ramp cost, direction
unchanged). Progress/yaw conclusions were never affected. Other published
scenarios have no mid-episode zero-command segment, so their slip values
are unaffected; the timeslice table on main (combo scenarios) is likewise
unaffected by this specific bug.

## 5. Regression check on the branch's default path

With the transport disabled and the same model files, branch code
reproduces main's published rollout **bit-exactly**
(prog 0.41362140257794966) — no default-behavior regression found in
`sim_env.py`/`safety.py`/`robot_state.py` for this path. An initial
4e-4 progress drift was traced to the fresh mesh regen (CAD moved on
09-04), not to code.

## Assumptions and limits

- Substitute-actor reproduction tests the TRANSPORT mechanism, not the
  canary actor's exact numbers; per-cell values differ from the published
  ones and should not be merged into one table without these labels.
- One seed, two headings, 10 s, DR-0 throughout: diagnostic screens.
- Noise scales are sim DR floors, not measured hardware noise; the
  injector cannot noise the nominal path.
- Simulated current remains an uncalibrated proxy; no freshness-stop/
  readiness replay (branch limitation list still applies).

## Next measurable step

Codex-owned, per the branch doc order: fit the estimator/filter response
against RECORDED hardware encoder/IMU traces (they exist under
`rl_move/hardware_traces/`), extract the real sensor-noise floor, then
re-run this matched screen at the MEASURED noise level — that single
number decides whether the fast-filter candidate survives. On this side,
nothing further is runnable until that measured floor exists; the
`env_yawpri` and time-slice rulings on main are unchanged.
