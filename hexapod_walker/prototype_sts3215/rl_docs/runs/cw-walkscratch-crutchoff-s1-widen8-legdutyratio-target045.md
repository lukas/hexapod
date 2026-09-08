# cw-walkscratch-crutchoff-s1-widen8-legdutyratio-target045

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: FINISHED

**created**: 2026-09-08T09:52:41+00:00

**pod**: hexapod-mjx-train-5

**steps**: 2000000

**parent**: cw-walkscratch-easy0905-headset-crossgrav-medhead-dr-allaxis-nokick-crutchoff-s1-widen8-acq1-legdutyratiofresh-guardfix1

**wandb_id**: 86d56f57

**hypothesis**: Plain English: 2nd-seed replicate of the target=0.30->0.45 dose question (see the s0 sibling's own hypothesis text): same fresh-init widen8 recipe, same charge=150, only the balance target raised toward the passing population's median (0.537) instead of its p10 (0.30), testing whether a bolder target suppresses the chronic front-pair sacrifice more decisively than 0.30 did, without the slip/progress regression seen from merely continuing the 0.30 dose longer (09-08 ~03:3x).

**gate**: MECHANISM-HEALTH CANARY ONLY: do not judge skill acquisition, close a behavior/reward class, or require mature gait at this checkpoint. MECHANISM-HEALTH CANARY ONLY, 2M, identical bar to the s0-target045 sibling: PASS requires gait_valid equal-or-better AND slip_per_m/progress_ratio equal-or-better in >=3/4 groups vs this seed's own matched 0.30-dose guardfix1 sibling. Two seeds agreeing is sufficient for a canary-level mechanism verdict on this dose, per this lineage's own established convention. FAIL if chronic sacrifice persists/worsens or slip/progress regress in a majority of groups. No further dose step or continuation off a FAIL.

