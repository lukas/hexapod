# cw-standwalk-stage2-dualbc6-turncap-mirroraug-klroll-acq1

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: KILLED

**created**: 2026-09-01T01:07:13+00:00

**pod**: hexapod-mjx-train-2

**steps**: 38000000

**parent**: cw-standwalk-stage2-dualbc6-turncap-mirroraug-valuewarmup-acq1

**wandb_id**: 7937l8rl

**hypothesis**: Plain English: control arm separating the campaign's two candidate erosion mechanisms -- is a bounded actor update size ALONE enough to defend turn authority, without any critic warmup? Same recipe/init as the twice-FAILED turnpay-acq1 base (turnpay-canary checkpoint, 1x pricing, 38M) with --actor-freeze-steps=0 (no warmup phase) and the single new mechanism --kl-rollback=0.05 (transactional PPO update: rollback + actor-LR halving whenever realized approx_kl > 0.05). Dig-in measured every run in this family training at realized approx_kl 0.08-0.15 / clip_fraction ~0.28 steady-state despite default --target-kl 0.02 (SB3 early-stop cannot undo an applied minibatch) -- oversized updates are the prime suspect for both grinding away the thin yaw behavior AND re-blinding the critic via nonstationarity (valuewarmup's credit fix decayed to 4/4 BLIND by 16M once co-training resumed). Read jointly with the sibling valuewarmup-klroll-acq1: if BOTH hold authority, bounded KL is the real lever and warmup is optional; if only the warmup sibling holds, both mechanisms are needed; if BOTH erode to floor with KL provably bounded, the oversized-update hypothesis is refuted and the next lever is the reward-decomposed multi-head critic.

**gate**: Read against turnpay-acq1's own measured final (+0.032/+0.055,-0.045/-0.046) and the valuewarmup 12-pt curve. MECHANISM: train/kl_rollback_count > 0 and realized approx_kl bounded <=~0.05 from step 0 (vs 0.08-0.15 baseline) -- if the guard never fires or KL is unchanged, fix wiring before reading anything else. FINAL (38M): PASS if probe_turn_authority (own TURNCAP_CFG_SET, wz_cmd=+-0.25) wz_med >=0.10 both signs AND det walk gait_valid >=5/6 zero falls AND purewalk det progress_ratio in/above 0.40-0.48. FAIL if the 2M-snapshot erosion curve matches turnpay-acq1/valuewarmup within noise (pos at/under ~0.05 floor by 15-20M) -- bounded KL changed nothing, oversized-update driver refuted for the no-warmup case. PARTIAL otherwise: quantify the erosion time-constant vs both parents' curves, do not force a binary call. Joint read with valuewarmup-klroll-acq1 per its own gate text.

**verdict**: KILLED - DUPLICATE (no scientific read). A concurrent cycle launched cw-standwalk-stage2-dualbc6-turncap-mirroraug-klrollctrl-acq1 (train-1, created 01:00:28, 7 min before this one) with the IDENTICAL config and seed: same turnpay-canary init, --actor-lr=0.0003, --actor-freeze-steps=0, --kl-rollback=0.05, seed 0, 38M -- both cycles independently derived the same no-freeze kl-rollback control off the same valuewarmup dig-in verdict (recorded 00:56). Same-seed same-config twins carry near-zero extra information; killed the later-created copy at ~1M steps to free train-2. The control read now belongs to klrollctrl-acq1 (its gate is equivalent: PASS >=0.10 both signs / PARTIAL >0.05 / FAIL at the <=0.05 floor, joint with valuewarmup-klroll-acq1). If a seed twin is wanted after the joint read, launch it as a respec of klrollctrl-acq1 with --seed 1, not a revival of this entry.

