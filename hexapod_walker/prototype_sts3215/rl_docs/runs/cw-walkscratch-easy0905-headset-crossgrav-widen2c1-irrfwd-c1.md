# cw-walkscratch-easy0905-headset-crossgrav-widen2c1-irrfwd-c1

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: PASS

**created**: 2026-09-06T02:59:38+00:00

**pod**: hexapod-mjx-train-8

**steps**: 2000000

**parent**: cw-walkscratch-easy0905-headset-crossgrav-widen2c1-abrupt-c1-acq1

**wandb_id**: nodmsa82

**hypothesis**: Plain English: the medhead lineage already showed that once a champion is cross-gravity-transferred to full 1g, MORE curriculum (heading widening, or timing-irregularity) can be composed natively at 1g without another 0.5g detour (widenfwd-c1/irrfwd-c1 both running/landing). This just-PASSED widen2c1-abrupt-c1-acq1 champion (ACQ PASS this cycle, gait_valid 20/24 at full 40M/1g) already HAS the full 8-way heading set, so the one composable axis left is command-timing irregularity (the irr jitter). Does 'compose-after-transfer' generalize to a 2nd base champion (not just medhead), and specifically to one that already carries the harder full 8-way heading (incl. reversals)?

**gate**: PASS/INFORMATIVE-POSITIVE if gait_valid stays majority (>=4/6) in walk/det with no chronic (<0.10-duty every episode) single-leg sacrifice -- shows compose-after-transfer generalizes beyond the medhead base champion to a 2nd, harder (full-heading) one. FAIL/INFORMATIVE-NEGATIVE if it collapses to the leg[1,4] chronic-sacrifice fingerprint or a new chronic pattern -- would mean compose-after-transfer is medhead-specific, not a general property of the 1g-transferred state. Either outcome is informative; do not require a mature 40M-grade gait at 2M.

**verdict**: CANARY PASS - INFORMATIVE-POSITIVE (per this run's own explicit gate): aggregate gait_valid 21/24 -- walk/det 5/6 (majority holds; one transient sac=[5], leg-5 duty 0.02 that episode vs 0.17-0.47 across the other 5 -- not chronic), walk/sto 6/6 clean, walk_startjitter/det 5/6 (transient sac=[1], leg-1 duty 0.05 that episode vs 0.24-0.37 elsewhere), walk_startjitter/sto 5/6 (sac=[5] + 1 genuine TERM tilt_roll). No leg is chronically flagged across multiple episodes -- each dip is isolated to a single episode in a single mode, unlike the leg[1,4] chronic-park fingerprint this gate was explicitly watching for. CONFIRMS compose-after-transfer (composing MORE curriculum natively at full 1g on a champion that's already been cross-gravity-transferred) generalizes beyond the medhead base to a 2nd, harder base champion (widen2c1, which already carries the full 8-way heading set incl. reversals) -- matches medhead-irrfwd-c1/medhead-widenfwd-c1's own CANARY PASS reads this cycle. Caveats: (1) 1 genuine fall (TERM tilt_roll, walk_startjitter/sto episode 0) -- the first fall logged across this whole forward-extension-canary family (medhead-{widenfwd,irrfwd}, medhead-ramp-{widenfwd,irrfwd} all logged 0/24 falls); (2) markedly slower/noisier than those siblings -- forward dist 0.10-1.32m/20s (vs siblings' 2.2-3.3m) and slip_per_m 4.7-10.4 (vs siblings' 3-6) -- consistent with widen2c1's own baseline champion already being the harder/slower full-8-way-heading recipe, not a new pathology introduced by irr-timing composition specifically. Reward quarters small and noisy (18.9,-22.7,24.0,-3.7) over only 2M steps -- consistent with sibling canaries at this budget, not diagnostic either way.

