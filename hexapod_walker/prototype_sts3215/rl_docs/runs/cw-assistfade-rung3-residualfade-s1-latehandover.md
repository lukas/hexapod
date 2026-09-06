# cw-assistfade-rung3-residualfade-s1-latehandover

<!-- GENERATED from experiments.json by launch_run.py — do not edit -->

**status**: INTENT

**created**: 2026-09-06T19:38:45+00:00

**pod**: hexapod-mjx-train-2

**steps**: 2000000

**parent**: cw-assistfade-rung3-residualfade-s1

**hypothesis**: Same as -s0-latehandover (see its own hypothesis): rung 3's schedule-collision FAIL reproduced worse on the std-anneal-frac lever (both -s0-stdslow and -s1-stdslow read <0.35 progress with over_current in every eval mode); per the pre-registered fallback, this arm changes ONLY sched.t1_steps (1.4M->1.7M, gentler/later blend handover within the 2M canary-phase cap) and reverts log-std-anneal-frac to the original 1.0. Seed 1, paired with -s0-latehandover for the same 2/2-seed read this track has used at every rung.

**gate**: MECHANISM-HEALTH CANARY ONLY: do not judge skill acquisition, close a behavior/reward class, or require mature gait at this checkpoint. Identical ignition text to every rung-3 canary: sustained forward translation the full episode, repeated alternating support transitions, all six legs participating (no permanently planted/unloaded leg), zero falls/safety terminations, progress_ratio>=0.35 on all modes (det+sto, walk + walk_startjitter, DR-0, held-out). MUST override goal.walk_residual_gate=0 (drop sched.*/walk_residual_* from the eval cfg-set). FAIL if progress stays <0.35, any leg is chronically parked/unloaded, or over_current terminations reappear in the startjitter panel -- check wandb_history.csv's env/sched_value vs reward_walk/height_err_mm/terminations trend across the anneal before concluding schedule-shape-vs-mechanism.

