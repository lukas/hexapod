# Untouched control-chain measurement — VALID_OBSERVATION

The exact six prescribed baseline replays completed on 2026-09-08: **6,020 control ticks, 30,100 profile ticks and 30,100 physics steps**, in 37.117 seconds on the pinned CPU runtime. Every existing comparison passed. The result fills the missing synchronized policy/decoder/safety/profile/actuator/joint history; it is an observation of the unchanged policy. No new yaw efficacy result, controller, PPO continuation or physical trial follows from it. All earlier STOPs and original 5 mrad, retention and continuous-joystick criteria remain unchanged.

## Execution and parity

Preregistration, runner and meaningful static tests were published before responses in commit `ed675d09cb60b1a0e6527da76bc59830815e2cad`. Root independently reviewed the complete runner, frozen helper and safety/profile semantics, then authorized this exact execution. Sixty pure/static checks passed locally and on the controller before the simulation. No implementation recovery, partial failure, selective retry or extra rollout occurred.

The execution manifest confirms runner SHA256 `761c19669895a3ac57bf3aca835cc819cadb088a446d5ba44c94f963c2693bf9`. Execution started at `2026-09-08T10:39:28Z`; the process exited 0 with `VALID_OBSERVATION`. The immutable preregistration inside the manifest retains its historical pre-execution `NOT_STARTED`/awaiting-review fields; current outcome is in [full/summary.json](full/summary.json), not a retrospective edit of the preregistration.

| Comparison | Result |
| --- | --- |
| Six frozen cells, fixed lengths | 4 × 755 arc ticks + 2 × 1,500 straight ticks = 6,020 |
| Policy, decoder, safety and control records | Complete, one per control tick |
| Actual command writes | 6,020; exactly one per tick |
| Profile and physics calls | 30,100 each; exactly five 0.002-second steps per control tick |
| Prior saved body/current arrays | All 78 match shape, dtype and bytes exactly |
| Body trace including modes and current hashes | All six match |
| Prior complete-state boundaries | All 34 match saved state hashes and qpos |
| Safety holds / failed statuses / terminations | 0 / 0 / 0 |
| Decoder failures | 0 |

The 34 prior boundaries are eight saved arc states per cell (ticks 600, 619, 638, 657, 680, 699, 718 and 737) plus the two straight endpoints at 1,500. The four complete arc endpoints at 755 are **new captures**: the old references only saved all 755 body/current samples and earlier full states. No nonexistent old 755 full-state reference is claimed. Coverage counts begin after the unchanged reset and exclude its physics steps.

An independent audit loaded only JSON/NPZ data and NumPy, without importing the runner, helper or simulator. It confirmed the inventory, operation coverage, all 78 arrays, all 34 historical state boundaries and runner SHA. Eight descriptive fields were independently recomputed across both registered windows and all six cells, with maximum discrepancy exactly zero. See [INDEPENDENT_AUDIT.md](INDEPENDENT_AUDIT.md).

## Descriptive transfer facts

These summaries use the preregistered post-ramp window `[200,N)` and an unweighted mean over the six corresponding joints per axis, ordered **yaw / hip / knee**. Arc windows are 5.55 seconds and straight windows 13 seconds; these are six individual cells, not an aggregate effectiveness estimate. Per-joint results for both all-tick and post-ramp windows remain in each cell JSON.

`requested_slew_exceed_fraction` counts requested increments beyond the nominal/entry-ramped allowance. The name describes a request comparison, not recoverable yaw loss or a general safety-saturation diagnosis. Here the recorded statuses provide additional context: no holds or failed status, entry slew ramps inactive, and every returned safe target was exactly the previous safe target plus the requested delta clipped to the recorded rate cap (maximum residual 0 radians). The logical-to-MuJoCo command mapping also matched actual write arguments exactly. These checks establish the observed transformations on these replays; they do not isolate their contribution to body yaw.

| Cell | Control ticks | Requested slew exceedance %, yaw / hip / knee | Mean absolute decoded→safe gap °, yaw / hip / knee | Mean absolute profile goal→target gap °, yaw / hip / knee |
| --- | ---: | --- | --- | --- |
| w+0.00_ph0_straight_baseline | 1500 | 67.26 / 81.28 / 43.09 | 1.387 / 3.885 / 0.317 | 2.818 / 2.660 / 3.817 |
| w+0.00_ph1_straight_baseline | 1500 | 68.04 / 80.33 / 44.29 | 1.392 / 3.890 / 0.329 | 2.822 / 2.687 / 3.816 |
| w+0.15_ph0_baseline | 755 | 66.19 / 78.95 / 43.57 | 1.943 / 3.867 / 0.328 | 2.310 / 2.726 / 3.903 |
| w+0.15_ph1_baseline | 755 | 66.01 / 80.36 / 45.08 | 1.948 / 3.851 / 0.355 | 2.316 / 2.738 / 3.901 |
| w-0.15_ph0_baseline | 755 | 64.44 / 81.65 / 40.42 | 2.089 / 3.751 / 0.270 | 2.306 / 2.712 / 3.934 |
| w-0.15_ph1_baseline | 755 | 63.66 / 82.16 / 41.98 | 2.111 / 3.782 / 0.293 | 2.317 / 2.725 / 3.947 |

The mean absolute delivered safe increments were 0.290–0.339° per tick at yaw, 0.325–0.336° at hip and 0.258–0.264° at knee across these cells. These are actual output histories, distinct from the much larger requested increments and configured caps. At the later profile/plant stages, mean absolute effective-actuator-target minus profile-target displacement was 0.375–0.386° yaw, 0.323–0.331° hip and 0.435–0.447° knee. Profile-target to actual post-step joint differences were 0.665–0.776°, 0.543–0.569° and 0.968–1.067°, respectively. These gaps include the applicable delayed profile, downstream actuator dead-zone and physical response; they are not uniquely attributed to servo dynamics or contact.

Actual writes requested speed 400 counts/s (35.15625°/s) and acceleration register 20. The recorded resolved profile velocity cap was 350 counts/s (30.76171875°/s). Post-ramp acceleration caps were all 175.78125°/s². Full-history arrays also preserve the initial default acceleration of 131.8359375°/s² (register 15) before delayed register-20 writes matured; the initial delay queue was empty and later queue lengths ranged 1–3. Thus configured write requests, initial defaults, matured caps and realized profile velocities are recorded separately. **350 is a velocity cap, not a current limit.**

Configured per-axis latency was 29.7 / 25.6125 / 8.5875 ms, and profile deadbands 0.432 / 0.353 / 0.494°. These are source configuration values, not a fitted empirical command-to-body delay. Raw command maturation and substep histories are available, but no delay, gain, template or control law was fitted. Preregistered zero-ignoring reversal counts are retained; arbitrarily small nonzero sign changes count, so the counts alone do not establish harmful policy cancellation.

Decoder, safety, latched command and sensed joint positions use robot-absolute radians. Profile, effective actuator targets and native joint physics use MuJoCo-relative radians; knee-relative equals knee-absolute minus hip-absolute. Comparisons stay in their stated frame. Existing sensed-versus-native differences include the frozen observation path and are not evidence of an encoder fault or a new calibration problem. Simulated current is completely recorded and byte-identical to the reference, but remains an uncalibrated simulation estimate.

## Provenance and artifacts

The pinned checkpoint is `ppo_goal_cw_robotwalk_turns_20260907_yawref_cigate8m.zip`, SHA256 `61f9c20f0f72d89217a22b47037e33c8dad2f50bfaca0a3d5517f714dd0eeb10`. Full XML SHA256 is `7efb8e8a0cb014c0b4bac27c41e7a85e683553168b87d85aac0d52d6a8e5a837`; original cfg SHA256 is `aabf4cc25f78ebf3b28ff7b4a46fba85c109f4061becaf4212e8842b5c550e40`. The source remains full mesh, 34 meshes / 159 geoms / 4.80573 kg, with 400 write speed / 20 acceleration / 0.375° control-tick slew / 350 counts/s resolved velocity / 100 Hz. Safety/current and physics configuration were unchanged.

Runtime: `/workspace/hexapod_hybrid_fullmesh_20260908/hexapod_walker/prototype_sts3215`; output: `/workspace/hexapod_control_chain_20260908/full`. Current main simulation files were not substituted for the frozen runtime. Every checkpoint, helper, source, cfg and reference hash was verified before helper import; exact hashes are in [PREREGISTRATION.json](PREREGISTRATION.json) and the linked magnitude [pins.json](../turn_magnitude_execution_20260908/pins.json). References came from magnitude result commit `be4e8a42381f128ead7bc86486f295de68940d89`.

- [DESIGN.md](DESIGN.md), [capture_control_chain.py](capture_control_chain.py) and [test_capture_control_chain.py](test_capture_control_chain.py): immutable reviewed protocol, implementation and static checks.
- [full/execution_manifest.json](full/execution_manifest.json) and [full/summary.json](full/summary.json): execution identity and actual outcome.
- `full/*_chain.npz`: complete synchronized control, command, profile and physics arrays; `full/*_body.npz`: all original body/current arrays; corresponding per-cell JSON: metadata, parity, full-state records and preregistered per-joint aggregates.
- [transfer_read.json](transfer_read.json): descriptive axis summaries and status/frame/output arithmetic checks, with no response fitting.
- [EVIDENCE_SHA256.json](EVIDENCE_SHA256.json): hashes and byte lengths of this evidence bundle, excluding the hash manifest itself.

The measurement supports analysis of the observed control-chain transfers. It does not establish a useful yaw mechanism, prove that a proposed correction will improve walking, identify a controller-independent authority bound, or overturn completed failures. Any actual new law remains future work requiring a distinct finite preregistered comparator and the original gates; none is launched or nominated by this artifact.
