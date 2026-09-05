# cw-walkscratch-easy0905-sde-s3-c2

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: REFUSED

**created**: 2026-09-05T11:06:32+00:00

**pod**: hexapod-mjx-train-9

**steps**: 40000000

**parent**: cw-walkscratch-easy0905-base-s3

**hypothesis**: Own-checkpoint 40M continuation of sde-s3 (ACQ CONTINUE this cycle: ep_len_mean dipped from a 333 peak to 47-57 mid-run then genuinely recovered to 184-193 in the last two logged points, ep_rew_mean climbed monotonically -522->+28.3 ending positive, v_along_cmd held ~0.17 m/s throughout -- same still-learning fingerprint sde-s0/s1/s2 already earned continuations for. Respec'd from base-s3 (never carries --use-sde) with blank --activation-fn + --init-from only. Named -c2 because -c1 (same recipe) was killed 30s after launch when auto-placed on a pod contended with a CPU-heavy eval (fps=91) -- W&B names are append-only so it cannot be reused.

**gate**: Acquisition milestone at own easy physics: 20s held-out fixed-forward, >=0.03 m/s median net forward, 0 falls in 12 det episodes, six-leg lift/place on video, no belly drag; report sto. Per 08-21 ruling: FAIL only if v_along_cmd/reward_walk go flat or ep_len re-collapses without recovery; continue further if still climbing at cutoff.

**refused_reason**: hexapod-mjx-train-9 already runs cw-walkscratch-easy0905-sde-s3-c1b — GPU pods host exactly one run; pick a free GPU pod.

