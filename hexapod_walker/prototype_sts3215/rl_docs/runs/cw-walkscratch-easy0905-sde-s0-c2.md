# cw-walkscratch-easy0905-sde-s0-c2

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: FAILED

**created**: 2026-09-05T10:54:05+00:00

**pod**: hexapod-mjx-train-8

**steps**: 40000000

**parent**: cw-walkscratch-easy0905-sde-s1

**hypothesis**: Own-checkpoint 40M continuation of sde-s0-c1 (ACQ CONTINUE this cycle: ep_len dipped then recovered to 239, reward ended positive +17.1, v_along holds ~0.15-0.17 m/s — same still-learning fingerprint as sde-s1/s2/s3). Plain English: give the sde-s0 lineage another 40M to see if survival duration keeps compounding like sde-s1-c2/sde-s2-c2 are already testing.

**gate**: Acquisition milestone at own easy physics: 20s held-out fixed-forward, >=0.03 m/s median net forward, 0 falls in 12 det episodes, six-leg lift/place on video, no belly drag; report sto. Per 08-21 ruling: FAIL only if v_along_cmd/reward_walk go flat or ep_len re-collapses without recovery.

**verdict**: Own-checkpoint continuation attempt died in <1s, 0 steps logged. This respec (built by a concurrent cycle) cloned cw-walkscratch-easy0905-sde-s1's vector (a gSDE-flagged sibling carrying a bare --use-sde --sde-sample-freq 20) and only blanked --activation-fn -- leaving --use-sde in place alongside a plain --init-from, tripping train_ppo_mjx.py's SystemExit guard (PPO.load already restores the checkpoint's own gSDE). Same bug class as sde-s1-c1/sde-s2-c1, this time via wrong respec SOURCE (must be a non-gSDE sibling like base-s0/base-s1, which never carry --use-sde at all) rather than a leftover flag value. Pod hexapod-mjx-train-8 confirmed idle, no lingering process. Relaunching correctly as sde-s0-c3 (respec from base-s0: blank --activation-fn, no --use-sde, --init-from only).

**failed_reason**: SystemExit in <1s: --use-sde only applies to from-scratch/transplant builds; a plain --init-from warm start keeps the checkpoints own exploration mode. This respec cloned cw-walkscratch-easy0905-sde-s1 (a gSDE-flagged sibling: --use-sde --sde-sample-freq 20 present) and only blanked --activation-fn, leaving the bare --use-sde flag in place alongside --init-from -- same bug class as sde-s1-c1/sde-s2-c1, this time via wrong respec source (a gSDE sibling) rather than wrong flag. 0 steps logged, pod hexapod-mjx-train-8 confirmed idle (no train_ppo process). Relaunching correctly as sde-s0-c3 (respec from base-s0, which never carries --use-sde, blank --activation-fn + --init-from only).

