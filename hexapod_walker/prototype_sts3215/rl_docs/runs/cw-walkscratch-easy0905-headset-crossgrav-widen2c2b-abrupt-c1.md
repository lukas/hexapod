# cw-walkscratch-easy0905-headset-crossgrav-widen2c2b-abrupt-c1

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: FAIL - INFORMATIVE (negative control CONFIRMS, with nuance)

**created**: 2026-09-06T00:56:24+00:00

**pod**: hexapod-mjx-train-1

**steps**: 2000000

**parent**: cw-walkscratch-easy0905-headset-halfgrav-fullhead-widen2-c2b-acq1

**wandb_id**: j010yu74

**hypothesis**: Plain English: a NEGATIVE CONTROL for this cycle's cross-gravity-transfer finding. All 3 PASSing crossgrav discovery arms this cycle warm-started from LEG-HEALTHY halfgrav champions. This one instead warm-starts from widen2-c2b-acq1, a halfgrav champion that is ALREADY chronically leg-1-parked at its own native 0.5g (ACQ FAIL, gait_valid 14/24, leg-1 duty 0.01-0.21 in every episode) -- i.e. NOT leg-healthy at the source. If cross-gravity-transfer's benefit truly requires a leg-healthy starting point (the causal story this cycle's PASSes support), this arm should show the SAME or WORSE leg-1 entrenchment at 1g, not a repair -- confirming 'leg-healthy at source' is a necessary condition, not just correlated. If it instead becomes six-leg-healthy at 1g despite being unhealthy at 0.5g, that would be a surprising and important complication of the whole finding.

**gate**: This is a controlled-to-FAIL arm (expected FAIL, informative either way): EXPECTED/CONFIRMS if gait_valid stays majority-FAILING in walk/det with the same or worse leg-1 chronic sacrifice as the 0.5g source (duty <0.10 chronically) -- confirms leg-health-at-source is necessary for the transfer to work, strengthening (not just correlating) the cross-gravity-transfer causal story. SURPRISING/COMPLICATES if it instead clears majority (>=4/6) walk/det with no chronic sacrifice -- would mean 1g transfer can REPAIR an already-unhealthy halfgrav champion, a much stronger and more useful claim needing its own follow-up. Either outcome is informative; do not require a mature 40M-grade gait at 2M.

**verdict**: Negative control resolves CONFIRMS: warm-starting the abrupt-1g crossgrav recipe from the leg-1-entrenched widen2-c2b-acq1 champion does NOT produce a leg-healthy 1g policy — the leg-1-parked attractor survives; 2M at 1g only masks its nominal-start basin. Evidence (24-ep gate, report.json + per-leg duty/swing dig-in): leg-1 SACRIFICE in 10/24 episodes (walk/det 2/6, startjitter/det 5/6 with duty 0.01-0.09 and swing counts 7-36 vs 100+ other legs, startjitter/sto 3/6); aggregate gait_valid 14/24 = IDENTICAL to the parent's own 14/24 at native 0.5g (redistribution, not net repair). Matched controls: ALL FOUR healthy-source crossgrav siblings at the same 2M budget (medhead/widen2c1/irracq1/widenirrc1) show leg-1 sac 0/24 with duty >=0.10 everywhere; this arm's 'repaired' walk/det is also far below sibling quality (prog med 0.86, slip med 7.76 vs siblings 1.58-1.98 at band-level slip). The literal walk/det gate branch (4/6 gv, no chronic sac) reads SURPRISING but is superficial: the same checkpoint reverts to the chronic leg-1 fingerprint the moment start pose is perturbed. Conclusion: leg-health-at-source is NECESSARY for robust cross-gravity transfer at canary budget; walk/det alone is an insufficient entrenchment discriminator — use startjitter panels + per-leg sacrifice counts. Declining ep_rew_mean (-52->-439) is a widen2-lineage reward-scale trait (PASS sibling widen2c1 shows the same shape, -124->-229), not a per-run anomaly. Next: one pre-registered follow-up at acquisition scale (40M, same template as medhead-abrupt-c1-acq1) to answer the remaining fork the gate text demands: can BUDGET substitute for source health, i.e. does 40M at 1g fully repair the attractor (would reopen unhealthy champions as crossgrav seeds) or does entrenchment persist at all budgets.

