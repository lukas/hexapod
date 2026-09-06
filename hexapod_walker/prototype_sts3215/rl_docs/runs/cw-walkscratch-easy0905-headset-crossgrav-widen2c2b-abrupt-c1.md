# cw-walkscratch-easy0905-headset-crossgrav-widen2c2b-abrupt-c1

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: RUNNING

**created**: 2026-09-06T00:56:24+00:00

**pod**: hexapod-mjx-train-1

**steps**: 2000000

**parent**: cw-walkscratch-easy0905-headset-halfgrav-fullhead-widen2-c2b-acq1

**wandb_id**: j010yu74

**hypothesis**: Plain English: a NEGATIVE CONTROL for this cycle's cross-gravity-transfer finding. All 3 PASSing crossgrav discovery arms this cycle warm-started from LEG-HEALTHY halfgrav champions. This one instead warm-starts from widen2-c2b-acq1, a halfgrav champion that is ALREADY chronically leg-1-parked at its own native 0.5g (ACQ FAIL, gait_valid 14/24, leg-1 duty 0.01-0.21 in every episode) -- i.e. NOT leg-healthy at the source. If cross-gravity-transfer's benefit truly requires a leg-healthy starting point (the causal story this cycle's PASSes support), this arm should show the SAME or WORSE leg-1 entrenchment at 1g, not a repair -- confirming 'leg-healthy at source' is a necessary condition, not just correlated. If it instead becomes six-leg-healthy at 1g despite being unhealthy at 0.5g, that would be a surprising and important complication of the whole finding.

**gate**: This is a controlled-to-FAIL arm (expected FAIL, informative either way): EXPECTED/CONFIRMS if gait_valid stays majority-FAILING in walk/det with the same or worse leg-1 chronic sacrifice as the 0.5g source (duty <0.10 chronically) -- confirms leg-health-at-source is necessary for the transfer to work, strengthening (not just correlating) the cross-gravity-transfer causal story. SURPRISING/COMPLICATES if it instead clears majority (>=4/6) walk/det with no chronic sacrifice -- would mean 1g transfer can REPAIR an already-unhealthy halfgrav champion, a much stronger and more useful claim needing its own follow-up. Either outcome is informative; do not require a mature 40M-grade gait at 2M.

