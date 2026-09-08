# Fresh-canary claim review — 2026-09-08 02:01 UTC

Evidence audit supporting scoped corrections to SKILLS, walkcurr STATUS and CURRENT_TRUTHS. Existing health verdicts and qualification criteria are preserved.

The corrected additive duty-ratio reward is demonstrably active and its three cited fresh-lineage canaries meet their reported health thresholds. These results do **not** establish the claimed “first real gait recovery from a fresh/naive init.” Health, recovery relative to the actual initialization, and causal benefit of the charge are separate claims.

## Exact initialization and comparison

Run prefix below: `cw-walkscratch-easy0905-headset-crossgrav-medhead-dr-allaxis-nokick-crutchoff-`. Each corrected run is the listed suffix plus `-guardfix1`; each inert predecessor is the same suffix without that ending. Counts are `gait_valid` out of the exact 24-episode det/sto walk/start-jitter panel; every row below has **zero terminations**.

| Suffix | Actual `--init-from` suffix | Training RNG | Heading set | Actual init's own gate | Inert 2M predecessor | Corrected 2M |
|---|---|---:|---|---:|---:|---:|
| `s0-widen8-acq1-legdutyratiofresh` | `s0_acq1.zip` | 2 | 8-way | 21/24, **5-way** | 22/24 | 21/24 |
| `s1-widen8-acq1-legdutyratiofresh` | `s1_widen8.zip` | 3 | 8-way | 21/24, 8-way | 22/24 | 21/24 |
| `s0-widenbis180-legdutyratiofresh` | `s0_acq1.zip` | 2 | 6-way | 21/24, **5-way** | 18/24 | 18/24 |

The full checkpoint prefix for the init suffixes is `rl_move/sim/policies/ppo_goal_cw_walkscratch_easy0905_headset_crossgrav_medhead_dr_allaxis_nokick_crutchoff_`.

Native exact `get_run` ledger entries confirm the initialization, RNG, 2M requested budget, and identical goal/reward/motor/DR configuration strings between each original and corrected attempt. The originals were invalid as tests of an **active** charge because the activation guard was broken; their preserved behavioral reports remain useful contextual undosed comparisons. They are post-hoc comparisons across a code repair, not a substitute for the explicitly matched charge-off acquisition now running through evaluation. These small differences do not establish that the charge is harmful or that the mechanism class is closed.

`s0_acq1` is an already trained 40M checkpoint. Its own 5-way gate is not a matched baseline for either the 8-way or 6-way evaluation. `s1_widen8` had already trained and passed the 8-way canary. “Fresh/naive” can therefore describe selected lineage placement at most; it does not mean a random/untrained initialization or three independent seeds. The three arms use two RNGs, and both s0 arms share the same checkpoint.

## Specific corrections

- `STATUS.md` says corrected s0 fresh has sacrifice in **2/24** episodes. Its exact corrected report has **3/24**: `walk/det[0]` leg 5, `walk_startjitter/sto[2]` leg 5, and `walk_startjitter/sto[3]` leg 0. **2/24 belongs to its inert predecessor.**
- The s1 corrected policy has the same three failing episode/leg labels as its actual initialization and the same 21/24 aggregate. Their numerical behavior differs; matching flags do not imply bit-identical policies or rollouts.
- For the milder arm, leg 0 clears the peer-excluded duty ratio ≥0.22 in 21/24 episodes versus 20/24 in the inert predecessor. Both remain 18/24 gait-valid with six sacrifice episodes. This is a narrow threshold crossing, not broad recovery.
- Comparisons against much worse termination-reward arms or their longer acquisitions do not isolate the additive charge's effect. The “far above ... at 20x the budget” comparison is not a matched recovery baseline.
- Likewise, replace “BIT-IDENTICAL” claims based only on matching gait-valid/failing-leg patterns with a statement naming exactly those matching fields. No checkpoint or full numerical rollout equivalence is established here.

Suggested replacement for the fresh-canary headline/net read in SKILLS, STATUS and CURRENT_TRUTHS:

> Active additive duty-ratio reward: three corrected 2M canaries meet their mechanism-health thresholds (21/24, 21/24 and 18/24 gait-valid; zero terminations), across two training RNGs and two heading envelopes. This establishes activation and short-budget compatibility, not causal gait recovery. The actual initializations were already walking, and matching inert predecessors scored 22/24, 22/24 and 18/24. The matched charge-on/off acquisition comparison is the next causal read; retain current qualification criteria and avoid claims of mechanism efficacy before that comparison.

The +10M acquisition report/decision belongs to cycle `20260908T015550`; this review does not duplicate or replace that verdict. Its matched charge-off control must be evaluated before attributing duration-associated changes to the charge.

## Evidence locations and retrieval caveat

Exact reports are on the controller under `/workspace/hexapod/hexapod_walker/prototype_sts3215/logs/ckpt_eval/`, in `<run-name-with-hyphens-replaced-by-underscores>_gate/report.json`, for all six original/corrected runs in the table and exact sources `..._s0_acq1` and `..._s1_widen8`.

W&B identities, inert → corrected: s0 fresh `x6d04iaz` → `iwhaciad`; s1 fresh `xvrxw7t3` → `tdpmyt9z`; milder `tipif77i` → `w6y5uai5`. Source ledger identities: s0 `0r0p9nix`, s1 `3cfy682l`.

Claim locations at inspection: `rl_docs/SKILLS.md:1367`, `CURRENT_TRUTHS.md:944`, and the `~01:5x` refill update's “Net read” in `rl_docs/tracks/walkcurr/STATUS.md`. Lines can move during the active cycles.

The MCP `eval_report` lookup uses substring matching and returns only a few recent matches: querying `s1-widen8` returned later descendant reports rather than the exact source. This review used read-only direct reads of the exact canonical report paths to prevent that substitution. All eight exact gate reports have seed 0, policy std 0.135 and reported plant mass 4.80573 kg; heading configuration still differs as noted above.
