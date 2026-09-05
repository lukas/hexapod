# cw-walkscratch-easy0905-sde-s0-c3

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: REFUSED

**created**: 2026-09-05T10:57:24+00:00

**pod**: hexapod-mjx-train-8

**steps**: 2000000

**parent**: cw-walkscratch-easy0905-base-s0

**hypothesis**: Own-checkpoint 40M continuation of sde-s0-c1 (ACQ CONTINUE this cycle: ep_len_mean recovered from a mid-training trough of ~50 ticks to climb 159->203->239 in the last three logged points with no plateau, ep_rew_mean climbed -1.3->18.5->17.1 over the same window, v_along_cmd held steady ~0.15-0.17 m/s throughout -- same still-learning fingerprint sde-s1/sde-s2 already earned a continuation for. CORRECTED relaunch of the sde-s0-c2 attempt, which died in <1s because it was wrongly respec'd from cw-walkscratch-easy0905-sde-s1 (a gSDE sibling still carrying a bare --use-sde) and only blanked --activation-fn; this respec is from base-s0 (never carries --use-sde) with blank --activation-fn + --init-from only, mirroring the working sde-s1-c2/sde-s2-c2 pattern.

**gate**: Acquisition milestone at own easy physics: 20s held-out fixed-forward, >=0.03 m/s median net forward, 0 falls in 12 det episodes, six-leg lift/place on video, no belly drag; report sto. Per 08-21 ruling: FAIL only if v_along_cmd/reward_walk go flat or ep_len re-collapses without recovery; continue further if still climbing at cutoff.

**refused_reason**: acquisition runs require --evidence: name the healthy canary and a comparable full-budget learning precedent.

