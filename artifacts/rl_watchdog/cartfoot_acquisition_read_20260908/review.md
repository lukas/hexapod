# Independent Cartesian acquisition decision review — 2026-09-08

Recommendation: **one bounded, matched +10M continuation is justified by the existing intermediate clause**, subject to the normal video/exploit and non-log-std weight-movement checks. This is a decision review, not a replacement formal verdict or launch authorization.

The registered `cartfoot-c1-cont10m` gate uses **group mean slip**, not medians: promising requires ≤1.5× matched OFF in ≥3/4 groups, gait-valid ≥18/24, zero falls. Retrofit closure requires >3× in ≥3/4 groups or gait-valid <18/24. The observed ratios below exceed3× in only2/4 groups; 19/24 gait-valid and zero terminations persist. The numerical closure condition is therefore unmet; the result occupies its explicitly registered intermediate band.

| Group | ON mean slip at 2M | ON mean slip at 12M | 12M ON/OFF mean ratio |
|---|---:|---:|---:|
| walk/det | 19.064 | 13.326 | 2.418× |
| walk/sto | 24.962 | 17.485 | 3.084× |
| walk_startjitter/det | 68.401 | 16.378 | 2.522× |
| walk_startjitter/sto | 32.823 | 18.625 | 3.097× |

Held-out improvement is real but insufficient for success: all four ON groups reduce mean slip and increase mean progress ratio (.505→.710, .370→.535, .308→.636, .322→.505), with the same 19/24 gait-valid and zero falls. Current overall progress remains only .5965 versus OFF1.5925; this is neither qualification nor evidence Cartesian is superior.

`optimization_curve.json` currently contains **13 synchronized available rows**, 4,194,304–10,485,760 steps, not a complete whole-run history. Actual sampled-transition `optimization/reward_per_tick` improves −.319507→−.171629 (EMA −.409032→−.274301) while rolling episode length rises980.26→1961.67. `train_ppo_mjx.py:4223–4241` computes this from reward sum/transition count; it is not an ad hoc division of two separately averaged episode metrics. Raw episode-return quarters alone cannot establish stalled optimization while duration changes. This is consistent with CURRENT_TRUTHS.md's normalized-reward methodology and the 08-21/08-22 rule allowing continuation when optimization **and** held-out task metrics improve. It does not prove the entire curve was monotonic or explain every duration change.

## Bounded decision and falsification

Continue both current RNG2 checkpoints by exactly+10M, preserving each arm's actual inherited initialization, optimizer/schedule semantics, all physics/reward/noise/motor settings and the three-key ON/OFF difference. No seed3 extension, new seeds, new doses, or actor reinterpretation. Compare the same four groups×six held-out episodes at equal next depth; use arithmetic means for the registered ratios. Verify non-log-std weight movement and that existing videos show immature walking rather than a stable exploit before invoking the continuation clause.

At that single final read, retain the original **≤1.5× in≥3/4, gait-valid≥18/24, zero-fall** promising bar. **>3× in≥3/4 or gait-valid<18/24** falsifies the registered retrofit target; any new fall/protected-behavior loss also prevents promotion and further automatic continuation. If still intermediate, stop automatic budget extensions: the clause's one-extra-read allowance is exhausted. Record an unresolved retrofit outcome, not universal Cartesian class failure. If normalized reward rises but held-out slip/progress stalls or worsens, use the existing MISALIGNED audit branch instead of further same-recipe training. No success criterion or physical limit is relaxed.

Sources: this directory's `paired_summary.json`, four exact gate JSONs and `optimization_curve.json`; native MCP exact original `...cont40m-cartfoot-c1_gate/report.json` read2026-09-08 for the2M values; the exact `cartfoot-c1-cont10m` ledger gate; prototype `RESEARCH_RULES.md:33–57`, `RUN_INTERPRETATION_RULES.md` sections1/2/7, and `CURRENT_TRUTHS.md:1059–1064`. Prior MODE-comparator coverage remains partial and must not be relabeled fully passing.
