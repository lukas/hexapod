# Capped magnitude allocation: completed STOP

The exact preregistered assay completed on **2026-09-08 at 09:56 UTC**. **STOP: 0/8 candidate states and 0/4 fixed phase groups meet the original burst-authority gate.** Maximum candidate gain was **1.778 mrad**, below the unchanged **5 mrad** threshold. This closes this frozen allocation/mapping proposal. It does not authorize another dose, phase selection, weight fit, recurring controller, PPO, or physical trial. Prior single-axis, sign-box, support-yaw and time-slicing STOPs remain unchanged.

Root and `fresh_cartesian_frontier` owned this independent CPU diagnostic. Exactly **50 rollouts** ran: four continuous baselines, eight zero controls, 32 signed branches, and six straight controls. All eight specified states were available; none was replaced. The corrected execution exited successfully in 37.319 seconds. No training or robot action occurred.

## Frozen question and outcome

The candidate allocates the original mean-secant magnitudes under a .05 coordinate cap at the same requested L2 norm as the .025 sign-box comparator: **sqrt(18) × .025 = .10606601718**. All four template arrays, command-sign lookup, and phase centers were frozen before new responses. Each selected state received zero, +candidate, −candidate, +box and −box branches, with exactly five pulse ticks followed by 75 unchanged policy ticks. Branch sign reverses the vector while retaining the commanded yaw sign.

The held-out states use the original unexecuted quarter-phase selection rule: seed 0, DR 0, starts 0/pi, vx .08, wz ±.15, nearest pre-action phase in the fixed [P+10,P+25] window, P 600/638. They are held out from template fitting and prior pulse execution, not independent training seeds or reset draws. Fixed groups retain their original two members even when the unchanged nearest-phase lookup selects a different template.

All angles in the table are **mrad** and use the preregistered last-solve world-yaw measure. G+ and G− subtract the matched zero response and multiply by command sign. Odd = (G+ − G−)/2; advantage = G+(candidate) − G+(box). State names retain the **original group**; “lookup” records the template actually selected.

| Original group / start | Tick | Lookup phase | Candidate G+ | Candidate G− | Candidate odd | Box G+ | Advantage |
|---|---:|---:|---:|---:|---:|---:|---:|
| negative phase 0 / 0 | 657 | 1 | −1.618 | +0.503 | −1.060 | −0.859 | −0.759 |
| negative phase 0 / pi | 619 | 0 | +0.895 | −1.323 | +1.109 | −0.503 | +1.399 |
| negative phase 1 / 0 | 619 | 0 | −0.237 | +0.007 | −0.122 | +0.052 | −0.289 |
| negative phase 1 / pi | 657 | 0 | −0.221 | +0.007 | −0.114 | −0.518 | +0.297 |
| positive phase 0 / 0 | 657 | 1 | −3.026 | +0.119 | −1.572 | −2.355 | −0.670 |
| positive phase 0 / pi | 619 | 0 | −1.015 | +1.038 | −1.027 | −2.372 | +1.356 |
| positive phase 1 / 0 | 619 | 0 | −2.031 | −0.211 | −0.910 | −0.832 | −1.198 |
| positive phase 1 / pi | 657 | 0 | +1.778 | +0.513 | +0.632 | −1.167 | +2.945 |

Candidate gain mean/median was **−.684/−.626 mrad**; only 2/8 gains and 2/8 odd responses were positive. Comparator authority was also **0/8**. Comparative advantage mean/median was **+.385/+.00434 mrad**, with 4/8 positive. Every start-0 advantage was negative and every start-pi advantage positive: **no original pair had repeatable advantage**, even before applying the absolute authority gate. No fixed group passed for either yaw sign. These eight deterministic cells do not supply a population significance claim.

Every signed branch passed the unchanged retention requirements: **32/32**, including both directions of both allocations. Each completed the full 80-tick scoring window with all scored ticks walking and zero termination. Forward ratios to the matched zero ranged **.9685–1.0450**, loaded material-slip ratios **.9600–1.0517**, added peak roll **−.133 to +.133°**, and added peak pitch **−.093 to +.152°**. All remain inside .9 forward / 1.25 slip / baseline+3° gates. All eight +box comparators completed the same finite horizon. Per-leg loaded material displacement and loaded duration are preserved in the raw rows and audit; no new chronic-leg gate was introduced.

## Exactness, current and implementation evidence

- All eight original source P600/638 checks passed prefix, endpoint and scoring-window parity against the reviewed bank.
- All eight zero controls passed complete-state prefix/endpoint and scoring-window parity before nonzero execution. Offline NPZ review additionally confirmed every saved trace array, including current, equals the corresponding continuous baseline prefix.
- All 32 signed branches passed complete-state prefix and frozen mapping/vector parity. Offline NPZ review confirmed every array through the pre-pulse prefix exactly matches its zero.
- All four straight zero-off comparisons matched full 1500-tick traces, current arrays and complete endpoint states. Both untouched straight baselines were healthy, and every candidate/comparator control passed original retention on [2,15] seconds: 1300 walking ticks, positive body-forward displacement, zero termination. Zero-off lookup was checked on all 1500 ticks per arm.
- Zero falls and zero terminations occurred across all 50 rollouts. Exactly 160 dose records cover the 32 × five pulses; no action-bound clipping occurred. Requested L2 norms agree within float64 rounding. Float32 action conversion creates at most **2.81e-8** coordinate difference between recorded requested and applied increments; this is recorded, not a new rescaling. Matching requested L2 does not match plant motion, contact loading, work or energy.
- Current was available on **all 40,740 control ticks × 18 joints**. All 50 current-array hashes were independently verified. The maximum across the full runs was **2.640 A**, also present in the untouched straight baseline. These are **uncalibrated simulated estimates**, observed after existing `env.step`, not hardware measurements or a calibrated safety certification.

The plant remained the pinned full-mesh model: **34 meshes, 159 geoms, 4.80573 kg**. Motor contract: **400 write speed / 20 acceleration / .375° per tick / 350 counts/s resolved velocity / 100 Hz**. The 350 value is velocity, not current. Original current/safety configuration was unchanged. The runtime was isolated at `/workspace/hexapod_hybrid_fullmesh_20260908/hexapod_walker/prototype_sts3215`; no current simulator-source override was inherited. The helper’s recording start was changed only for straight material measurements, as preregistered and independently reviewed; physics and controller timing were unchanged.

One initial attempt failed in pure vector-reconstruction validation **before helper import or any simulator response**. Linux reconstruction differed from the exact frozen JSON by at most **2.082e-17 / 3 ULP**. Root reviewed and authorized changing that sanity assertion to the existing static-test contract, absolute tolerance **2e-16**, relative tolerance zero. The original frozen vector bytes and their application were unchanged. The failure, both platforms, coordinate hex values and repair are preserved. No baseline or response from the failed attempt existed to replace. The corrected 50-rollout protocol ran once after **92/92 controller static tests passed**; tests cover the actual frozen-vector consumer, rejection beyond tolerance, selection, gates, vector freezing, pulse timing and zero controls without importing the simulation helper.

## Provenance and files

Preregistration was published in **`c705980192a48a3aab07db031faf7f55271a16a9`** before new response generation. Root independently reviewed implementation **`d7399a203ed9d33bc99bd96ec93bfb9cf5c7c921`**, with pulse tests in `09924d2dd`. Numeric repair/evidence was published in **`c6b6b9fac`** and **`11a4c5d1d`** before the successful execution. The exact design copy retains its historical “DESIGN ONLY” wording; `PREREGISTRATION.json` records the subsequent freeze. Likewise, that immutable preregistration’s `NOT_STARTED` field is historical; actual completion is in `full_recovered/summary.json`.

| Pinned item | SHA256 |
|---|---|
| Executed runner | `9c24627698c3bdd6e871a54c87097219912161050b835f1fef88055c1a973e4f` |
| Exact protocol | `283a63bb3b2512d42fe14b6c85cfdcb34fbfc781d64d3c7222ef7b05866178b7` |
| Frozen vectors | `a16f9ccbb60f00164deee12649a061c84ad8729a61765b1cea423d2648acd23f` |
| Checkpoint | `61f9c20f0f72d89217a22b47037e33c8dad2f50bfaca0a3d5517f714dd0eeb10` |
| Full XML | `7efb8e8a0cb014c0b4bac27c41e7a85e683553168b87d85aac0d52d6a8e5a837` |
| Original 64-key cfg | `aabf4cc25f78ebf3b28ff7b4a46fba85c109f4061becaf4212e8842b5c550e40` |
| Reviewed helper | `436b0eee695094f94d68346548e12efed147f087b1447ea2349b0f4feb67cd54` |

Checkpoint name: `ppo_goal_cw_robotwalk_turns_20260907_yawref_cigate8m.zip`. Source and all asset hashes are in [pins.json](pins.json). The execution manifest records the actual controller runtime and source identity.

- [Summary](full_recovered/summary.json), [all eight state results](full_recovered/state_results.json), [frozen selections](full_recovered/selected_states_frozen.json), [straight controls](full_recovered/straight_zero_off.json).
- [Post-execution array/current/retention audit](postexecution_audit.json); all 50 per-run JSON records and compressed traces remain under `full_recovered/rows/` and `full_recovered/traces/`.
- [Original failure](initial_attempt/failure.json), [repair receipt](numeric_reconstruction_receipt.json), [controller numerical/platform evidence](numeric_platform_receipt.json), [local platform](numeric_local_platform_receipt.json).
- [Immutable preregistration](PREREGISTRATION.json), [frozen vectors](frozen_vectors.json), [runner](probe_magnitude.py), [static tests](test_magnitude.py), [execution manifest](full_recovered/execution_manifest.json).

The held-out outcomes remain immutable. They do not justify fitting another template to these eight states. This result rejects the exact frozen allocation/mapping’s proposed held-out authority and advantage; it does not prove that all possible steering mechanisms lack authority or isolate which physical mechanism caused the response.
