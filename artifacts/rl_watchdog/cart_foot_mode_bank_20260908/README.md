# Exact-recipe Cartesian MODE comparator preflight — executed; partial comparator coverage

24 episodes: existing heading-bank six comparators × seeds 0/1 × legacy OFF/Cartesian ON. Each is bounded at 2,000 control ticks (20 s at 100 Hz), so the entire panel is at most 48,000 control ticks. Source recipe is the champion's exact 78 cfg overrides; ON adds only 0.06/0.035/0.04 m Cartesian half-widths. Source training seed remains metadata (2); these are existing evaluation seeds, not new training lineages.

Script records full resolved cfg and source hashes, generated command traces, reset pairing, actual model/motor identity, per-tick clipping and target reconstruction errors, scalar reward/component observations, returns, displacement, and termination. The original heading MED numerical assertions remain preregistered. Clipped poses remain explicitly projected observations. Clipping alone does not reject a comparator: its realized body-frame progress, stationary speed, action/joint movement or actual termination must support its label before an ordering can pass. Stationary uses the existing configured idle-speed threshold; original MED ranking margins are retained. Existing 30° limits are retained; no substitute 20° death test. A surviving topple leaves death-ordering evidence unavailable.

A probe-only inverse expresses the same desired logical joint poses in each action space. Cartesian inverse uses the actual decoder's nominal leg-root FK, center, and box, with an independent MuJoCo FK check before reset. This matches the decoder's nominal-geometry convention under DR. Actual env.step and all downstream safety, servo and reward code remain in use. k_action_delta=.01 is retained; its normalized coordinates differ, so no false ON/OFF total reward equality is required.

Scope: a behavior-comparator MODE preflight, not policy qualification, exhaustive exploit coverage, or a function-preserving actor initialization. No policy/checkpoint, PPO, W&B or training action. No production modifications. Root executed this artifact on the controller against the committed b24c2ffa source. See the result below.

From the reviewed controller prototype root after staging this directory:

```sh
OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 timeout --signal=TERM --kill-after=30s 1200s uv run python /tmp/cart_foot_mode_bank_20260908/bank.py --recipe /tmp/cart_foot_mode_bank_20260908/source_recipe.json --expected-hashes /tmp/cart_foot_mode_bank_20260908/expected_hashes.json --out /tmp/cart_foot_mode_bank_20260908/result.json > /tmp/cart_foot_mode_bank_20260908/console.log 2>&1
```

Result JSON is checkpointed after each episode, and result.log has unbuffered per-episode progress. The external timeout is a wall-clock bound, not a claim about expected runtime. Review source-hash mismatches before execution; do not silently rebaseline them.

## Root result

Completed all 24 episodes (48,000 control ticks) in 88.54 seconds. All reset,
model and command pairs match. Both ON and OFF pass the tested tracking-over-
fixed-heading, tracking-over-park, displacement, heading-wiring and survival
checks. Tracking earns roughly 2,752–2,987; fixed heading, wrong heading,
park and stall all earn negative returns.

The preregistered overall result is NOT_PASS because coverage is incomplete,
with no failed available ranking: the seed-0 stall moves above the predefined
stationary-speed threshold, and the clipped topple targets never terminate
under the unchanged 30-degree envelope. The same gaps occur in both arms.
This is not a demonstrated Cartesian reward-ranking regression and is not
full MODE preflight certification. Do not relabel it PASS or reduce the
physical envelope to force the death comparator.

No additional training was launched by this probe. The separately owned
matched canary had already begun; this artifact is supplementary evidence,
not a retroactive passing prelaunch record. Normalized action-delta pricing
and action-noise geometry differ between the action parameterizations even
with unchanged scalar config. No claim of total-reward parity is made.

Full ticks/commands are losslessly retained in result.json.gz; summary.json
contains all other result fields and the original JSON SHA-256.
