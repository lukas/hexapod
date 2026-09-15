# Hexapod test-suite audit — 2026-09-14

The suite has excess experimental baggage and significant coverage gaps. The strongest opportunity is to move measured reward-ranking experiments out of regression gating, repair tests that do not exercise production behavior, and include the omitted firmware and system-identification checks. Reducing the headline case count is not a useful objective by itself.

## Scope and measurements

Audited commit `bda4e099ca4a0a28f2f5427b83f75f5ea00ae44f`, the migrated hardware-angle integration branch discussed with Lukas. This was a whole-suite static inventory and runtime profile, followed by manual review of the highest-cost and suspicious tests, two focused fault-injection checks, and investigation of omitted tests. It was not an assertion-by-assertion manual review or exhaustive mutation/coverage analysis of every test.

The earlier description of 3,865 tests as the “entire repository” was inaccurate. `make test-fast` selects only `rl_move/tests`, `linux_control`, and `robots`. Even `make test` omits `firmware/tests` and `sysid/tests`.

| Measure | Result |
| --- | --- |
| Default test source inventory | 326 files; 76,400 lines; 3,274 test-function definitions |
| Fresh-worktree default run | 3,865 passed; 23 skipped; one expected failure; 124.02 seconds |
| RL-directory cases | 3,402; includes policy/runtime, orchestrator, simulation and training tests |
| Linux-control cases | 479 |
| Robot-experiment cases | 4 |
| Collection skips | Four entire optional-backend modules; included in the reported skip count |
| Cases exceeding five seconds including setup | 15, measured under the configured parallel run |
| Files over the project's 1,000-line limit | Six |
| Additional omitted tests run | 25 firmware cases passed; 79 sysid cases passed; three sysid cases failed |

Parameterized inputs explain part of the difference between function count and case count. XML has 3,889 result records, including the four module-level collection skips. Timing sums below add individual setup/call/teardown elapsed times across parallel workers; they are neither CPU time nor a prediction of serial runtime or wall-clock savings. Fresh checkout/import/cache effects also make this 124-second run different from the preceding 68-second integration run.

## Findings and disposition

### 1. High priority: expensive reward-ranking banks remain in the fast regression suite

The binding research rules explicitly retire rollout-ranking assertions in favor of experiment reports and evaluation metrics. Nevertheless, these five files contain historical calibrated rollouts and measured reward thresholds:

| File | Selected cases | Summed case time | Action |
| --- | ---: | ---: | --- |
| `rl_move/tests/test_phasedir_semantics.py` | 24 | 85.62 s | Extract measured ranking banks; retain isolated mechanics |
| `rl_move/tests/test_walkscratch_easy_pilot.py` | 37 | 84.76 s | Extract pilot-specific recipes/rankings; retain command/ramp and gate mechanics |
| `rl_move/tests/test_course_disp_window_semantics.py` | 16 | 69.51 s | Retire the whole ranking test file from regression gating |
| `rl_move/tests/test_course_disp_semantics.py` | 10 | 23.97 s | Extract rankings and historical-checkpoint probe; retain default-off mechanism checks |
| `rl_move/tests/test_course_income_semantics.py` | 20 | 17.72 s | Extract calibrated income/teacher comparisons; retain synthetic mechanism checks |
| **Total** | **107** | **281.57 s** | **47.96% of 587.07 summed case seconds** |

The most clear-cut removal is `test_course_disp_window_semantics.py`: all four test functions compare simulated returns for old dose windows. Six parameterized cases are already marked slow, but 16 other cases still run. Its module fixture runs the same bank for those unmarked consumers. In the measured parallel run that fixture was instantiated on separate workers, costing 35.75 and 33.76 seconds for two cases.

The same marking problem occurs in `test_walkscratch_easy_pilot.py`: line 436 marks one `easy_returns` consumer slow, while consumers at lines 447, 464 and 473 remain selected. Skipping one test does not skip its shared fixture when other selected tests request it. Assertions such as `gait > park + 400` and a preset pilot recipe are experiment evidence, not stable software contracts.

**Concrete first cut:** remove this 107-line window-ranking file from pytest, preserving any useful research recipe in an explicitly invoked evaluation/probe and its results in experiment evidence. That removes 16 default cases and six excluded slow cases. Do not delete the other four files wholesale: they mix experiment assertions with useful code-path checks. Marking every rollout consumer slow would be a temporary containment measure, not completion of the requested pruning.

Evidence: `test_course_disp_window_semantics.py:56–107`; `test_walkscratch_easy_pilot.py:413–503`; `test_course_income_semantics.py:272–325`; `test_phasedir_semantics.py:388` onward; `RESEARCH_RULES.md:83–126`.

### 2. High priority: some tests can stay green while the production behavior is broken

`test_eval_cmd_suite_cfg_parse.py:42` calls itself an end-to-end check, but reconstructs the config-assignment loop inside the test. It never calls `eval_cmd_suite.main()`. The companion check at line 35 only looks for `_parse_cfg_set` in source text.

**Demonstrated failure to detect a bug:** in the isolated checkout, changed the production loop in `eval_cmd_suite.py:180` from `_parse_cfg_set(args.cfg_set)` to `_parse_cfg_set([])`, making it discard every supplied override. All four tests still passed. The mutation was then restored.

Replace the copied loop and substring check with a test that supplies CLI overrides to the real application entry point, intercepts environment construction, and asserts the actual config received. Keep the two shared-parser value tests, ideally in the parser's own test module. That protects the original list-parsing failure rather than the spelling of an import.

Other rewrite candidates:

- `test_motor_contract.py:165–200`: three tests inspect source fragments instead of observing resolved parameters or emitted contract metadata. Keep the genuine parameter-resolution tests earlier in that file; replace these source checks with captured constructor/log/report inputs. GPU construction can remain stubbed at the expensive boundary.
- `test_bulk_session_eval.py:257`: checks CLI declaration strings and `ep == args.strip_ep`, so a dead/commented code path could satisfy it. Assert parser defaults and selected episode behavior.
- `test_walkscratch_easy_pilot.py:608`: checks arithmetic on constants defined in the test file. It can pass regardless of production termination pricing. Move it to the pilot's experiment rationale and keep a synthetic test that calls the real pricing helper.

Static/AST checks are not inherently bad. A test whose explicit purpose is enforcing forbidden dependencies or a repository indexing rule is testing a structural contract. A source substring is inadequate when the claimed contract is runtime behavior.

### 3. High priority: normal test commands omit relevant firmware and calibration coverage

Both Makefile targets at lines 38–42 omit `firmware/tests` and `sysid/tests`. The robot unit helper does not add these directories either.

The omitted firmware tests compile actual firmware functions/loop code with fake I/O. All **25 passed**. They cover snapshot-cache behavior, full-health starvation during streaming, IMU failure debounce, and a negative control that reproduces the previous scheduler bug. These are directly relevant to the timer failures and worth keeping in an explicit hardware regression target.

The **82 sysid cases** completed with **79 passes and three failures**. The combined omitted run took only **4.34 seconds**. Failing cases are all in `sysid/tests/test_qualify_repeat_runner.py`, at lines 42, 132 and 174.

**Diagnosis:** `sysid/qualify_repeat_runner.py:291` requires the source comment `Always limp at the end` and a `_limp_all(bus, live_ids)` call. The controller at `linux_control/sysid_runner.py:774–805` deliberately retains support after an ordinary completion, falling back to limp if holding fails. The old proposal and qualification test still assume unconditional limp. This is stale qualification logic against a changed end-state contract, not proof the controller should drop support again.

Reconcile the saved protocol/qualification contract with the current supported completion behavior, and test execution outcomes using fake buses. Do not restore unconditional limp or weaken the existing fail-closed qualification just to make the tests pass. The audit did not change this admission behavior.

### 4. Medium priority: old experiments remain executable feature baggage

`test_tripod_gait_yaw_amplify_scale.py:11–20` explicitly says the option was refuted on September 4 and must not be used for BC training. Five mechanics tests remain, as does `test_probe_turn_authority.py:377`, which runs a simulation to insist the option still makes turning worse. The same family includes the uniform yaw-arm scaling candidate.

This is an appropriate **feature-plus-tests retirement candidate**, not a reason to remove protection from a still-supported API without changing the API. Local references show the refuted option in core gait code and diagnostic probes; the audit did not inspect every historical checkpoint, external caller or live run configuration. Confirm current consumers, preserve the negative result in research evidence, remove/refuse the obsolete knob, and replace its dose/rollout bank with an explicit unsupported-option test if compatibility requires one.

`test_probe_turn_authority.py` also contains useful contact-force, momentum and sign checks at lines 45–159 and 485 onward. Those must survive. Likewise, BC tests serve the active `any_means` goal; their age or use of demonstrations does not make them obsolete.

### 5. Medium priority: duplication is mostly scaffolding and fragmentation, not proven duplicate behavior

AST comparison found three exact test-body pairs. Manual inspection found that each pair calls a different helper/configuration: walk sequencing versus stance sequencing, or selective omega boost versus yaw scaling. Deleting one member would lose coverage. There were no shadowed/redefined test functions in the inventoried module/class scopes. This does not rule out semantic redundancy elsewhere.

Useful consolidation targets:

- Four `test_tripod_gait_*` files: 581 lines, 23 functions. Share setup and table-driven default/combined/pure-command cases while retaining distinct supported options and leg invariants.
- Five `test_mode_seq*` files: 1,035 lines, 36 functions. Share setup and sequence checks across the two environment types; retain their different transition grammars.
- Fourteen `test_launch_run*` files: 1,803 lines, 106 functions. Consolidate related CLI/default/continuation cases by behavior, with reusable launcher fixtures. Do not parameterize away boundary assertions or introduce a single giant test module.

Consolidation should reduce maintenance and duplicated setup; it may intentionally leave the executed case count unchanged.

Files exceeding the project's stated 1,000-line limit:

| File | Lines | Test functions |
| --- | ---: | ---: |
| `test_bc_anchor.py` | 3,601 | 141 |
| `test_rl_policy_timing.py` | 2,562 | 85 |
| `test_sim_env.py` | 1,878 | 58 |
| `test_gru_policy.py` | 1,655 | 38 |
| `test_walkscratch_easy_pilot.py` | 1,499 | 43 |
| `test_walk_curriculum.py` | 1,185 | 56 |

Prune experimental assertions first, then separate responsibilities and shared fixtures where warranted. Splitting large files by arbitrary line count would just distribute the same maintenance problem.

### 6. Medium priority: legacy model defaults and missing artifacts obscure what was exercised

`rl_move/tests/conftest.py:41` globally sets the model family to `primitive`. Many simulation tests inherit that setting instead of explicitly selecting their intended model. Some bank helpers override it, so it would be wrong to claim every simulation test uses the legacy family. Still, a large pass count cannot be read as coverage of the as-built robot model.

Replace the global model override with scoped, explicitly named fixtures/parameters for supported families. Retain legitimate primitive compatibility checks and require hardware-relevant tests to choose the intended model. `test_walkscratch_easy_pilot.py:135–146` also writes the environment directly; it restores it in `finally`, so this is a cleanup candidate rather than a demonstrated environment leak.

Five `test_cpg_controller_loader.py` cases skip because a named generated controller artifact is absent. A recover-loader case and one historical course-displacement checkpoint probe skip for the same reason. Build minimal valid/invalid artifacts in temporary fixtures for loader behavior; move real champion/checkpoint acceptance to an explicit artifact validation lane. Do not conflate these with optional JAX/CUDA/platform skips, which need a separate environment to execute.

The tracked `rise_ref_belly2plant.npz` is present in the fresh checkout; it was not falsely counted as an absent generated dependency.

### 7. Medium priority: one broad xfail hides a stale default-pose assertion

`test_joint_frame.py:61–80` marks a multi-assertion test `xfail(strict=False)` with a message suggesting a policy-frame error. Running it with `--runxfail` shows the action-map roundtrip and absolute/relative conversion assertions pass. It fails only because it expects the default plant knee to be 80°, while `_default_plant_deg()` deliberately returns 100° absolute for the legacy geometry.

Split the unconditional conversion checks into ordinary failing tests. Test default stance separately, with deterministic configuration and an explicit intended geometric pose. Then remove the blanket xfail and its misleading diagnosis. This result is not evidence of a newly reproduced hardware angle-conversion bug.

### 8. Keep and prioritize tests that catch consequential boundary errors

As a positive control, temporarily removed the hip subtraction from `robot_pose_to_raw_degrees`. All four selected writer-path cases in `test_robot_frame_boundary.py:66` failed: direct bus, MCU, drive controller and demo. The files were restored afterward. These checks observe the actual outgoing servo commands and distinguish public absolute tibia coordinates from relative hinge coordinates.

Preserve and prioritize the raw/absolute boundary, whole-sample feedback handling, arm-before-write ordering, torque/support cleanup, deadline recovery and stale-feedback handling. The firmware negative controls and synthetic reward-helper tests in `test_walk_task.py` are also good patterns. Fake buses are valuable when they capture real commands or faults at the boundary, rather than supplying the very answer the test claims to derive.

The Linux-control tests consumed just 8.13 of 587.07 summed case seconds (1.4%). There is no timing justification here for indiscriminately shrinking this protection.

## Recommended implementation order

1. Reconcile the three stale qualification failures and include firmware/sysid in an explicit hardware regression target. Keep failure visible until the intended end-state contract is resolved.
2. Replace the demonstrated ineffective CLI test and the source-text runtime guards; split the broad angle xfail.
3. Remove the pure window-ranking bank from regression gating, then extract rollout/ranking sections from the other four costly files. Keep synthetic mechanism coverage. Record research evidence outside pytest.
4. Retire the refuted yaw options together with their dependent tests after consumer verification.
5. Consolidate repeated fixtures/CLI tables and reduce the six oversized files by responsibility.
6. Make model families and optional artifact/backend checks explicit, then define a short hardware loop and a broader integration loop. Measure again after those changes rather than setting an arbitrary target such as “under 500 tests.”

This audit did not delete tests, change runtime behavior, merge to main, deploy software, or move a robot. Temporary fault injections were restored. The report deliberately distinguishes confirmed defects and clear retirement candidates from consolidation opportunities that need further consumer review.

## Evidence

Companion artifacts are in `artifacts/test-suite-audit-20260914/` in the primary workspace:

- `module-inventory.csv`: all 326 default-scope files, source size, test-function counts and measured case time.
- `inventory.json`: AST inventory and duplicate-body candidates; heuristics are leads, not deletion verdicts.
- `results.xml`, `runtime-summary.json`, `test-profile.log`: default run and timings.
- `mutations.json`, `mutation-ignored_cli_overrides.log`, `mutation-missing_knee_hip_subtraction.log`: ineffective-test example and positive control.
- `omitted-results.xml`, `omitted-tests.log`: firmware/sysid results, including the three real failures.
- `xfail-diagnosis.log`: the exact default-pose assertion hidden by the broad expected failure.

Reproduction from `hexapod_walker/prototype_sts3215/`, with the locked worktree environment:

```sh
uv run pytest -q -n auto -m 'not slow' --durations=0 --durations-min=0.05 \
  --junitxml=/tmp/hexapod-audit-results.xml rl_move/tests linux_control robots
uv run pytest -q firmware/tests sysid/tests
uv run pytest -q --runxfail \
  rl_move/tests/test_joint_frame.py::test_joint_policy_surface_is_robot_abs_while_mujoco_stays_private
```

The last two commands intentionally reproduce the diagnosed failures at the audited commit; they are not claimed green.
