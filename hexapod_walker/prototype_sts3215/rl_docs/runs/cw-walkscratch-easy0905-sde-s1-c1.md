# cw-walkscratch-easy0905-sde-s1-c1

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: FAILED

**created**: 2026-09-05T10:18:30+00:00

**pod**: hexapod-mjx-train-0

**steps**: 2000000

**parent**: cw-walkscratch-easy0905-sde-s1

**hypothesis**: Plain English: sde-s1 was still climbing (ep_len 111->231 ticks, reward 2.8->38.7) with no plateau at the 40M budget cutoff, unlike sdehalfgrav-s0's genuine flat fingerprint that justified a FAIL -- give it the same own-checkpoint continuation budget sde-s0 got. Own-checkpoint 40M continuation of sde-s1 (08-21 ruling: rising reward/eval at budget end = continue, not fail). Built by respec from the base-s1 vector (not sde-s1) because plain --init-from rejects retained --use-sde/--activation-fn; PPO.load restores the checkpoint's own gSDE (sde_sample_freq=20) and ELU activation, so the arg vector is otherwise identical to sde-s1's.

**gate**: Acquisition milestone at own easy physics: 20 s held-out fixed-forward, >=0.03 m/s median net forward, 0 falls in 12 det episodes, six-leg lift/place on video, no belly drag; report sto. Verify at first eval the loaded policy is still gSDE (use_sde=True, sde_sample_freq=20). Not met with ep_len/reward still rising = continue further per 08-21; FAIL only if ep_len_mean and reward BOTH go flat this budget (sdehalfgrav-s0 fingerprint) or park recaptures.

**verdict**: Own-checkpoint continuation of sde-s1 died in ~2s, 0 steps logged (wandb exit_code 0/runtime 0 looked clean). Root cause: this respec's arg vector kept --activation-fn elu on top of a plain --init-from, which trips train_ppo_mjx.py's own SystemExit guard (PPO.load already restores the checkpoint's saved ELU/gSDE; the guard exists because reasserting those flags on a warm-start is unsupported). Diagnosed+fixed same day (fb_20260905T080341_ef45b6, CURRENT_TRUTHS Known Tooling Gotchas): relaunched correctly as sde-s1-c2 (blank --activation-fn, no --use-sde, plain --init-from) on train-4, confirmed genuinely training past 12M steps. No behavioral evidence from this attempt; superseded by sde-s1-c2, not a lineage kill.

**failed_reason**: run never appeared as 'running' in W&B within 240s

**refused_reason**: launch-mechanics bug: --activation-fn elu passed alongside a plain --init-from -- train_ppo_mjx.py:3250 raises SystemExit('--activation-fn only applies to from-scratch/transplant builds...') on ANY plain warm-start when activation-fn is truthy (PPO.load already restores the checkpoint's own activation). Died in ~2s (wandb exit_code 0, runtime 0). Same root cause independently diagnosed + fixed this cycle for sde-s2-c1/c2 (see that entry); relaunching as sde-s1-c2 with --activation-fn= (blank) to match the working base-s0-c1/base-s1-c1/halfgrav-s0-c1 pattern.

