# cw-walkscratch-easy0905-sde-s3

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: CONTINUE

**created**: 2026-09-05T09:50:46+00:00

**pod**: hexapod-mjx-train-2

**steps**: 40000000

**parent**: cw-walkscratch-easy0905-sde-s0

**wandb_id**: 2cz2qe5m

**hypothesis**: Plain English: independent seed 3 of the gSDE exploration family, completing n=4 fresh seeds to match base/halfgrav for the sde-vs-Gaussian family comparison (matched-seed directive 09-05). From-scratch 40M, identical to sde-s2 except --seed 3.

**gate**: Acquisition milestone at OWN physics: 20 s held-out fixed-forward, >=0.03 m/s median net forward, 0 falls in 12 det episodes, six-leg lift/place on video, no belly drag; report sto. Mechanism evidence inherited from the family 2M CANARY PASS; spot-check ~2M in W&B. Not met with signals rising = continue/realign per 08-21; FAIL only on flat v_along+reward at budget or park recapture.

**verdict**: ACQ CONTINUE — 4th sde-family seed, same still-learning fingerprint as sde-s0-c1/sde-s1/sde-s2 (not FAIL per 08-21). Evidence: logs/ckpt_eval/cw_walkscratch_easy0905_sde_s3_gate/report.json — walk/det TERM tilt_pitch 6/6 (fwd 0.10m, gait_valid true meaning it cycled all six legs before falling, not a sacrificed-leg drag), walk/sto 0/6 gait_valid sac[2] fwd 0.34m, startjitter mixed (3/6 and 0/6 gait_valid) — every scenario well below the 0.6m/20s bar. wandb_history.csv: rollout/ep_len_mean rose to a peak 333 by ~9M, DIPPED to 47-57 mid-run (~28-38M), then genuinely RECOVERED to 184-193 at the final two logged points (40M) — not a flat dead plateau. rollout/ep_rew_mean rose monotonically the whole run (-522->-117->-30->-9.7->+24->+28.3, ending POSITIVE). env/v_along_cmd_m_s rose to a 0.177 peak and holds ~0.167 at the end. Same dip-then-recover signature as sde-s0-c1/sde-s1/sde-s2 (contrast with sdehalfgrav's genuine flat-plateau FAIL fingerprint). Next: own-checkpoint 40M continuation (sde-s3-c1), matching sde-s0-c1(->c2)/sde-s1-c2/sde-s2-c2 — strip --activation-fn/--use-sde on the plain --init-from per the CURRENT_TRUTHS.md gotcha.

