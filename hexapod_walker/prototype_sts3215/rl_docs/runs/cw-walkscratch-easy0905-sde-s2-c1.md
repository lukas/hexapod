# cw-walkscratch-easy0905-sde-s2-c1

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: FAILED

**created**: 2026-09-05T10:22:09+00:00

**pod**: hexapod-mjx-train-4

**steps**: 40000000

**parent**: cw-walkscratch-easy0905-sde-s2

**hypothesis**: Plain English: sde-s2 was ruled ACQ CONTINUE, not FAIL, at its 40M cutoff -- ep_len_mean rose 102->109->116->169->194->214 ticks (still climbing at the last logged point) and ep_rew_mean tracked it up an order of magnitude off its mid-training trough, with env/v_along_cmd_m_s holding ~0.15-0.17 m/s throughout; this is survival-duration still being learned, not sdehalfgrav-s0's genuine flat-everything plateau. Give it the same own-checkpoint 40M continuation budget sde-s0/sde-s1 got.

**gate**: Acquisition milestone at own easy physics: 20 s held-out fixed-forward, >=0.03 m/s median net forward, 0 falls in 12 det episodes, six-leg lift/place on video, no belly drag; report sto. Verify at first eval the loaded policy is still gSDE (use_sde=True). Not met with ep_len/reward still rising = continue further per 08-21; FAIL only if ep_len_mean and reward BOTH go flat this budget (sdehalfgrav-s0 fingerprint) or park recaptures.

**verdict**: Own-checkpoint continuation of sde-s2 died in ~2s, 0 steps logged. Same launch-mechanics bug as sde-s1-c1: this respec kept --use-sde/--sde-sample-freq/--activation-fn elu alongside a plain --init-from, tripping train_ppo_mjx.py's SystemExit guard (PPO.load already restores the checkpoint's own gSDE/ELU). Diagnosed+fixed same day (fb_20260905T080341_ef45b6): relaunched correctly as sde-s2-c2 (blank --activation-fn, no --use-sde, plain --init-from) on train-11, confirmed genuinely training past 15M steps. No behavioral evidence from this attempt; superseded by sde-s2-c2, not a lineage kill.

**failed_reason**: run never appeared as 'running' in W&B within 240s

**refused_reason**: launch-mechanics bug: --init-from-source cloned --use-sde+--sde-sample-freq+--activation-fn alongside a plain --init-from; train_ppo_mjx.py raises SystemExit for BOTH combos on a plain warm-start (checkpoint's own gSDE/activation must come from PPO.load, not CLI flags) -- process died in ~2s (wandb exit_code 0, runtime 0), matches concurrent cycle's sde-s1-c1 identical crash (also had --activation-fn+--init-from). Relaunching as sde-s2-c2 with those flags stripped.

