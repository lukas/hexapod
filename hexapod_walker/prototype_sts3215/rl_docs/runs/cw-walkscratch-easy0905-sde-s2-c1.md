# cw-walkscratch-easy0905-sde-s2-c1

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: INTENT

**created**: 2026-09-05T10:22:09+00:00

**pod**: hexapod-mjx-train-4

**steps**: 40000000

**parent**: cw-walkscratch-easy0905-sde-s2

**hypothesis**: Plain English: sde-s2 was ruled ACQ CONTINUE, not FAIL, at its 40M cutoff -- ep_len_mean rose 102->109->116->169->194->214 ticks (still climbing at the last logged point) and ep_rew_mean tracked it up an order of magnitude off its mid-training trough, with env/v_along_cmd_m_s holding ~0.15-0.17 m/s throughout; this is survival-duration still being learned, not sdehalfgrav-s0's genuine flat-everything plateau. Give it the same own-checkpoint 40M continuation budget sde-s0/sde-s1 got.

**gate**: Acquisition milestone at own easy physics: 20 s held-out fixed-forward, >=0.03 m/s median net forward, 0 falls in 12 det episodes, six-leg lift/place on video, no belly drag; report sto. Verify at first eval the loaded policy is still gSDE (use_sde=True). Not met with ep_len/reward still rising = continue further per 08-21; FAIL only if ep_len_mean and reward BOTH go flat this budget (sdehalfgrav-s0 fingerprint) or park recaptures.

