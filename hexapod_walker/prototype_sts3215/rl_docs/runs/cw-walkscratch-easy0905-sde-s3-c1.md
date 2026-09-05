# cw-walkscratch-easy0905-sde-s3-c1

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: REFUSED

**created**: 2026-09-05T11:03:41+00:00

**pod**: hexapod-mjx-train-9

**steps**: 40000000

**parent**: cw-walkscratch-easy0905-base-s3

**hypothesis**: Own-checkpoint 40M continuation of sde-s3 (ACQ CONTINUE this cycle: ep_len_mean dipped from a 333 peak to 47-57 mid-run then genuinely recovered to 184-193 in the last two logged points, ep_rew_mean climbed monotonically -522->+28.3 ending positive, v_along_cmd held ~0.17 m/s throughout -- same still-learning fingerprint sde-s0/s1/s2 already earned continuations for. Respec'd from base-s3 (never carries --use-sde) with blank --activation-fn + --init-from only. RELAUNCH: first attempt auto-placed on train-5 (contended with a CPU-heavy eval already there, fps=91, killed) -- pinned to an explicitly idle pod this time.

**gate**: Acquisition milestone at own easy physics: 20s held-out fixed-forward, >=0.03 m/s median net forward, 0 falls in 12 det episodes, six-leg lift/place on video, no belly drag; report sto. Per 08-21 ruling: FAIL only if v_along_cmd/reward_walk go flat or ep_len re-collapses without recovery; continue further if still climbing at cutoff.

**refused_reason**: W&B already has a run named cw-walkscratch-easy0905-sde-s3-c1 (names are append-only; pick a new one)

